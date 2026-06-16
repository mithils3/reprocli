from __future__ import annotations

from dataclasses import dataclass, field

from .supplements import supplement_text


@dataclass
class Paper:
    arxiv_id: str
    title: str = ""
    source_url: str = ""
    tex_files: dict[str, str] = field(default_factory=dict)
    paper_tex_text: str = ""
    supplement_source_url: str = ""
    supplement_status: str = ""
    supplement_files: list[dict] = field(default_factory=list)
    # Audit mode: the agent's reproduction run directory the auditor explores.
    run_dir: str = ""

    def text(self) -> str:
        header = [
            f"arxiv_id: {self.arxiv_id}",
            f"title: {self.title}",
            f"source_url: {self.source_url}",
        ]
        chunks = []
        supplement = supplement_text(
            self.supplement_status,
            self.supplement_source_url,
            self.supplement_files,
        )
        if supplement:
            chunks.append(supplement)
        paper_text = self.paper_tex_text or joined_tex_sections(self.tex_files)
        if paper_text:
            chunks.append("PAPER_LATEX:\n" + paper_text)
        return "\n".join(header) + "\n\n" + "\n\n".join(chunks)


def joined_tex_sections(tex_files: dict[str, str]) -> str:
    return "\n\n".join(
        f"### {path}\n{content}" for path, content in sorted(tex_files.items())
    )
