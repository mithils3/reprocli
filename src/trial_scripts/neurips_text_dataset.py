from datasets import load_dataset
from transformers import AutoTokenizer
from itertools import groupby

tokenizer = AutoTokenizer.from_pretrained("MiniMaxAI/MiniMax-M2.7", trust_remote_code=True)

paper_id = "2509.09802"

ds = load_dataset(
    "parquet",
    data_files="data/parquet_dataset/data/train-*.parquet",
    split="train",
    streaming=True,
)

def iter_papers(ds):
    """One pass over the (arxiv_id-grouped) stream, yielding (meta, paper_text)."""
    for arxiv_id, group in groupby(ds, key=lambda r: r["arxiv_id"]):
        rows = list(group)
        meta = {
            "arxiv_id": arxiv_id,
            "title": rows[0]["title"],
            "status": rows[0]["paper_status"],
            "files_expected": rows[0]["paper_files_written"],
        }
        # dedup on relative_path; sort for deterministic section order
        tex = {r["relative_path"]: r["text"]
               for r in rows if r["is_text"] and r["extension"] == ".tex"}
        paper_text = "\n\n".join(f"### {p}\n{t}" for p, t in sorted(tex.items()))
        yield meta, paper_text


for meta, paper_text in iter_papers(ds):
    if meta["arxiv_id"] != paper_id:      # drop this line to process ALL papers
        continue

    if not paper_text:
        print(f"{meta['arxiv_id']}: no .tex rows (status={meta['status']})")
        break

    n_tok = len(tokenizer(paper_text)["input_ids"])
    print(paper_text)
    print(f"{meta['title']}")
    print(f"Number of tokens: {n_tok}  (over context!)" if n_tok > 200_000
          else f"Number of tokens: {n_tok}")

    with open(f"{meta['arxiv_id']}.txt", "w") as f:
        f.write(paper_text)

    break   # remove together with the arxiv_id filter to do the full corpus
