# NiceTool Landing Site

This directory contains the standalone static landing website for NiceTool.

It is intentionally separate from the application routes under `public/`.
You can deploy this directory with any static hosting service, such as Nginx,
GitHub Pages, Cloudflare Pages, or an object storage bucket.

Open `index.html` directly in a browser. `docs.html` is generated from the Chinese Markdown files under `docs/` and English Markdown files under `docs/en/`. It includes a small client-side renderer, so it also works from `file://` without a NiceTool server.

Regenerate the static docs page after editing files under `docs/` or `docs/en/`:

```bash
uv run python scripts/build_landing_docs.py
```

You can also serve this directory with a simple static server:

```bash
python -m http.server 8080 -d landing
```
