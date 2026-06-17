# Documentation site

Full project documentation lives in [`docs/`](../docs/) and is published as a
browsable site built with
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/):
**<https://mithils3.github.io/reprocli/>** (live once GitHub Pages is enabled).

## Read locally with live reload

```bash
uv pip install -r requirements-docs.txt   # one-time, into a venv of your choice
mkdocs serve                              # → http://127.0.0.1:8000
```

## Publish / refresh the public site

Builds and pushes to the `gh-pages` branch:

```bash
mkdocs gh-deploy
```
