#!/usr/bin/env python3
"""Run a prompt template over arXiv source papers with in-process vLLM.

This script loads the Hugging Face dataset as a normal Dataset, groups file rows
by arxiv_id, replaces {PAPER_TEXT} in prompt.txt, and sends batches directly to
vLLM's Python LLM API. It does not start or call a localhost server.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_DATASET = "Mithilss/neurips-2025-arxiv-latex-sources"
DEFAULT_MODEL = "MiniMaxAI/MiniMax-M2.7"
DEFAULT_OUTPUT = Path("outputs/neurips_2025_minimax_m27.jsonl")
DEFAULT_PLACEHOLDER = "{PAPER_TEXT}"
DEFAULT_COMPILATION_CONFIG = '{"mode":3,"pass_config":{"fuse_minimax_qk_norm":true}}'
REQUIRED_COLUMNS = {
    "arxiv_id",
    "title",
    "source_url",
    "paper_index",
    "paper_status",
    "paper_files_written",
    "relative_path",
    "extension",
    "is_text",
    "text",
}


@dataclass
class PaperAccumulator:
    arxiv_id: str
    title: str = ""
    source_url: str = ""
    paper_index: int | None = None
    paper_status: str = ""
    paper_files_written: int | None = None
    text_parts: dict[str, str] = field(default_factory=dict)

    def add_row(self, row: dict[str, Any], extensions: set[str]) -> None:
        if not self.title:
            self.title = row.get("title") or ""
        if not self.source_url:
            self.source_url = row.get("source_url") or ""
        if self.paper_index is None:
            self.paper_index = row.get("paper_index")
        if not self.paper_status:
            self.paper_status = row.get("paper_status") or ""
        if self.paper_files_written is None:
            self.paper_files_written = row.get("paper_files_written")

        if not row.get("is_text"):
            return
        extension = (row.get("extension") or "").casefold()
        text = row.get("text")
        relative_path = row.get("relative_path")
        if extension in extensions and text and relative_path:
            self.text_parts[str(relative_path)] = str(text)

    def build_paper_text(self, include_metadata_header: bool) -> str:
        sections = [
            f"### {path}\n{text}"
            for path, text in sorted(self.text_parts.items())
        ]
        body = "\n\n".join(sections)
        if not include_metadata_header:
            return body

        header_lines = [
            f"arxiv_id: {self.arxiv_id}",
            f"title: {self.title}",
        ]
        if self.source_url:
            header_lines.append(f"source_url: {self.source_url}")
        return "\n".join(header_lines) + "\n\n" + body


@dataclass
class PromptItem:
    arxiv_id: str
    title: str
    source_url: str
    prompt: str
    selected_files: int
    prompt_tokens: int | None
    original_prompt_tokens: int | None
    truncated: bool


def main() -> int:
    args = parse_args()
    if args.overwrite and args.output.exists():
        args.output.unlink()

    completed_ids = load_completed_ids(args.output) if args.resume else set()
    if completed_ids:
        print(f"Resuming: found {len(completed_ids)} completed arxiv_id values.", file=sys.stderr)

    prompt_template = args.prompt_file.read_text(encoding="utf-8")
    if args.placeholder not in prompt_template:
        raise SystemExit(
            f"{args.prompt_file} does not contain placeholder {args.placeholder!r}."
        )

    extensions = parse_extensions(args.extensions)
    papers = load_papers(args, extensions)
    if args.only_arxiv_id:
        wanted = set(args.only_arxiv_id)
        papers = [paper for paper in papers if paper.arxiv_id in wanted]
    if args.limit_papers is not None:
        papers = papers[: args.limit_papers]

    tokenizer = None
    max_input_tokens = args.max_input_tokens
    if max_input_tokens is None and args.max_model_len:
        max_input_tokens = max(args.max_model_len - args.max_tokens - args.token_safety_margin, 1)
    if max_input_tokens and max_input_tokens > 0:
        tokenizer = load_tokenizer(args)

    output_count = 0
    pending: list[PromptItem] = []

    args.output.parent.mkdir(parents=True, exist_ok=True)

    if not args.dry_run:
        llm = load_llm(args)
        sampling_params = build_sampling_params(args)
    else:
        llm = None
        sampling_params = None

    for paper in papers:
        if paper.arxiv_id in completed_ids:
            continue

        paper_text = paper.build_paper_text(args.include_metadata_header)
        if not paper.text_parts:
            append_record(
                args.output,
                {
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "source_url": paper.source_url,
                    "status": "skipped_no_text",
                    "selected_files": 0,
                },
            )
            output_count += 1
            continue

        item = make_prompt_item(
            paper=paper,
            paper_text=paper_text,
            prompt_template=prompt_template,
            placeholder=args.placeholder,
            tokenizer=tokenizer,
            max_input_tokens=max_input_tokens,
            on_too_long=args.on_too_long,
        )
        if item is None:
            append_record(
                args.output,
                {
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "source_url": paper.source_url,
                    "status": "skipped_too_long",
                    "selected_files": len(paper.text_parts),
                },
            )
            output_count += 1
            continue

        if args.dry_run:
            append_record(
                args.output,
                {
                    "arxiv_id": item.arxiv_id,
                    "title": item.title,
                    "source_url": item.source_url,
                    "status": "dry_run",
                    "selected_files": item.selected_files,
                    "prompt_tokens": item.prompt_tokens,
                    "original_prompt_tokens": item.original_prompt_tokens,
                    "truncated": item.truncated,
                },
            )
            output_count += 1
            continue

        pending.append(item)
        if len(pending) >= args.batch_size:
            assert llm is not None and sampling_params is not None
            output_count += run_batch(args.output, llm, sampling_params, pending)
            pending = []

    if pending:
        assert llm is not None and sampling_params is not None
        output_count += run_batch(args.output, llm, sampling_params, pending)

    print(f"Wrote {output_count} records to {args.output}", file=sys.stderr)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch NeurIPS arXiv source papers through an in-process vLLM model."
    )
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--split", default="train")
    parser.add_argument(
        "--data-files",
        help="Optional data_files argument for load_dataset, e.g. local Parquet shards.",
    )
    parser.add_argument("--cache-dir")
    parser.add_argument("--prompt-file", type=Path, default=Path("prompt.txt"))
    parser.add_argument("--placeholder", default=DEFAULT_PLACEHOLDER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--extensions", default=".tex")
    parser.add_argument("--limit-papers", type=int)
    parser.add_argument("--only-arxiv-id", action="append", default=[])
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume", dest="resume", action="store_true", default=True)
    parser.add_argument("--no-resume", dest="resume", action="store_false")
    parser.add_argument(
        "--include-metadata-header",
        dest="include_metadata_header",
        action="store_true",
        default=True,
    )
    parser.add_argument(
        "--no-metadata-header",
        dest="include_metadata_header",
        action="store_false",
    )

    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--tokenizer", help="Tokenizer name/path. Defaults to --model.")
    parser.add_argument("--tensor-parallel-size", type=int, default=4)
    parser.add_argument("--max-model-len", type=int, default=196608)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.9)
    parser.add_argument("--dtype", default="auto")
    parser.add_argument("--quantization")
    parser.add_argument(
        "--compilation-config-json",
        default=DEFAULT_COMPILATION_CONFIG,
        help="JSON passed to vLLM LLM(compilation_config=...). Use '' or none to disable.",
    )
    parser.add_argument("--trust-remote-code", dest="trust_remote_code", action="store_true", default=True)
    parser.add_argument("--no-trust-remote-code", dest="trust_remote_code", action="store_false")

    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--stop", action="append", default=[])

    parser.add_argument(
        "--max-input-tokens",
        type=int,
        help=(
            "Prompt-token budget before generation. Defaults to "
            "--max-model-len - --max-tokens - --token-safety-margin. "
            "Set to 0 to disable token counting/truncation."
        ),
    )
    parser.add_argument("--token-safety-margin", type=int, default=512)
    parser.add_argument(
        "--on-too-long",
        choices=("truncate", "skip", "error"),
        default="truncate",
    )
    return parser.parse_args()


def parse_extensions(raw: str) -> set[str]:
    extensions = set()
    for value in raw.split(","):
        value = value.strip().casefold()
        if not value:
            continue
        extensions.add(value if value.startswith(".") else f".{value}")
    if not extensions:
        raise SystemExit("--extensions must include at least one file extension.")
    return extensions


def load_papers(args: argparse.Namespace, extensions: set[str]) -> list[PaperAccumulator]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise SystemExit("Install datasets before running this script.") from exc

    load_kwargs: dict[str, Any] = {"split": args.split}
    if args.data_files:
        load_kwargs["data_files"] = args.data_files
    if args.cache_dir:
        load_kwargs["cache_dir"] = args.cache_dir

    dataset = load_dataset(args.dataset, **load_kwargs)
    missing = REQUIRED_COLUMNS.difference(dataset.column_names)
    if missing:
        raise SystemExit(f"Dataset is missing required columns: {sorted(missing)}")

    removable = [column for column in dataset.column_names if column not in REQUIRED_COLUMNS]
    if removable:
        dataset = dataset.remove_columns(removable)

    papers_by_id: dict[str, PaperAccumulator] = {}
    paper_order: list[str] = []
    for row in dataset:
        arxiv_id = row.get("arxiv_id")
        if not arxiv_id:
            continue
        arxiv_id = str(arxiv_id)
        paper = papers_by_id.get(arxiv_id)
        if paper is None:
            paper = PaperAccumulator(arxiv_id=arxiv_id)
            papers_by_id[arxiv_id] = paper
            paper_order.append(arxiv_id)
        paper.add_row(row, extensions)

    print(
        f"Loaded {len(paper_order)} papers from {args.dataset} "
        f"using extensions {sorted(extensions)}.",
        file=sys.stderr,
    )
    return [papers_by_id[arxiv_id] for arxiv_id in paper_order]


def load_tokenizer(args: argparse.Namespace) -> Any:
    try:
        from transformers import AutoTokenizer
    except ImportError as exc:
        raise SystemExit("Install transformers for prompt token counting/truncation.") from exc
    tokenizer_name = args.tokenizer or args.model
    return AutoTokenizer.from_pretrained(
        tokenizer_name,
        trust_remote_code=args.trust_remote_code,
    )


def load_llm(args: argparse.Namespace) -> Any:
    try:
        from vllm import LLM
    except ImportError as exc:
        raise SystemExit("Install vllm before running model inference.") from exc

    llm_kwargs: dict[str, Any] = {
        "model": args.model,
        "tensor_parallel_size": args.tensor_parallel_size,
        "trust_remote_code": args.trust_remote_code,
        "gpu_memory_utilization": args.gpu_memory_utilization,
        "dtype": args.dtype,
    }
    if args.max_model_len:
        llm_kwargs["max_model_len"] = args.max_model_len
    if args.quantization:
        llm_kwargs["quantization"] = args.quantization
    compilation_config = parse_compilation_config(args.compilation_config_json)
    if compilation_config is not None:
        llm_kwargs["compilation_config"] = compilation_config

    return LLM(**llm_kwargs)


def parse_compilation_config(raw: str | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    if raw.strip().casefold() in {"", "none", "null"}:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid --compilation-config-json: {exc}") from exc


def build_sampling_params(args: argparse.Namespace) -> Any:
    try:
        from vllm import SamplingParams
    except ImportError as exc:
        raise SystemExit("Install vllm before running model inference.") from exc

    kwargs: dict[str, Any] = {
        "temperature": args.temperature,
        "top_p": args.top_p,
        "max_tokens": args.max_tokens,
        "seed": args.seed,
    }
    if args.stop:
        kwargs["stop"] = args.stop
    return SamplingParams(**kwargs)


def make_prompt_item(
    paper: PaperAccumulator,
    paper_text: str,
    prompt_template: str,
    placeholder: str,
    tokenizer: Any | None,
    max_input_tokens: int | None,
    on_too_long: str,
) -> PromptItem | None:
    prompt = prompt_template.replace(placeholder, paper_text)
    prompt_tokens = count_tokens(tokenizer, prompt)
    original_prompt_tokens = prompt_tokens
    truncated = False

    if max_input_tokens and prompt_tokens and prompt_tokens > max_input_tokens:
        if on_too_long == "error":
            raise SystemExit(
                f"{paper.arxiv_id} prompt has {prompt_tokens} tokens, "
                f"above max_input_tokens={max_input_tokens}."
            )
        if on_too_long == "skip":
            return None
        assert tokenizer is not None
        paper_text = truncate_paper_text(
            tokenizer=tokenizer,
            prompt_template=prompt_template,
            placeholder=placeholder,
            paper_text=paper_text,
            max_input_tokens=max_input_tokens,
        )
        prompt = prompt_template.replace(placeholder, paper_text)
        prompt_tokens = count_tokens(tokenizer, prompt)
        truncated = True

    return PromptItem(
        arxiv_id=paper.arxiv_id,
        title=paper.title,
        source_url=paper.source_url,
        prompt=prompt,
        selected_files=len(paper.text_parts),
        prompt_tokens=prompt_tokens,
        original_prompt_tokens=original_prompt_tokens,
        truncated=truncated,
    )


def count_tokens(tokenizer: Any | None, text: str) -> int | None:
    if tokenizer is None:
        return None
    encoded = tokenizer(text, add_special_tokens=False)
    return len(encoded["input_ids"])


def truncate_paper_text(
    tokenizer: Any,
    prompt_template: str,
    placeholder: str,
    paper_text: str,
    max_input_tokens: int,
) -> str:
    empty_prompt = prompt_template.replace(placeholder, "")
    static_tokens = count_tokens(tokenizer, empty_prompt) or 0
    paper_budget = max(max_input_tokens - static_tokens - 32, 1)
    token_ids = tokenizer(paper_text, add_special_tokens=False)["input_ids"]
    if len(token_ids) <= paper_budget:
        return paper_text

    while paper_budget > 0:
        candidate = tokenizer.decode(token_ids[:paper_budget], skip_special_tokens=False)
        candidate_prompt = prompt_template.replace(placeholder, candidate)
        candidate_tokens = count_tokens(tokenizer, candidate_prompt) or 0
        if candidate_tokens <= max_input_tokens:
            return candidate
        paper_budget -= max(candidate_tokens - max_input_tokens + 32, 1)

    return ""


def run_batch(
    output_path: Path,
    llm: Any,
    sampling_params: Any,
    batch: list[PromptItem],
) -> int:
    print(
        "Generating batch: "
        + ", ".join(f"{item.arxiv_id}({item.prompt_tokens or '?'} tok)" for item in batch),
        file=sys.stderr,
    )
    outputs = llm.generate([item.prompt for item in batch], sampling_params)
    for item, request_output in zip(batch, outputs, strict=True):
        completion = request_output.outputs[0] if request_output.outputs else None
        generated_text = completion.text if completion is not None else ""
        parsed_response = parse_json_response(generated_text)
        append_record(
            output_path,
            {
                "arxiv_id": item.arxiv_id,
                "title": item.title,
                "source_url": item.source_url,
                "status": "generated",
                "selected_files": item.selected_files,
                "prompt_tokens": item.prompt_tokens,
                "original_prompt_tokens": item.original_prompt_tokens,
                "truncated": item.truncated,
                "generated_tokens": token_count_from_completion(completion),
                "finish_reason": getattr(completion, "finish_reason", None),
                "stop_reason": getattr(completion, "stop_reason", None),
                "response_text": generated_text,
                "parsed_response": parsed_response,
            },
        )
    return len(batch)


def token_count_from_completion(completion: Any | None) -> int | None:
    if completion is None:
        return None
    token_ids = getattr(completion, "token_ids", None)
    if token_ids is None:
        return None
    return len(token_ids)


def parse_json_response(text: str) -> Any | None:
    candidates = [text.strip()]
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            candidates.append("\n".join(lines[1:-1]).strip())

    json_slice = extract_first_json_object(stripped)
    if json_slice:
        candidates.append(json_slice)

    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def load_completed_ids(output_path: Path) -> set[str]:
    if not output_path.exists():
        return set()
    completed: set[str] = set()
    with output_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                print(
                    f"Skipping malformed JSONL line {line_number} in {output_path}.",
                    file=sys.stderr,
                )
                continue
            arxiv_id = record.get("arxiv_id")
            if arxiv_id:
                completed.add(str(arxiv_id))
    return completed


def append_record(output_path: Path, record: dict[str, Any]) -> None:
    with output_path.open("a", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False)
        handle.write("\n")
        handle.flush()


if __name__ == "__main__":
    raise SystemExit(main())
