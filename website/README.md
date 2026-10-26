# NiceTool Website

A standalone bilingual static site, inspired by Calabash's quiet green palette,
generous spacing and product-led demonstration layout. Its HTML, CSS, JavaScript,
images, license and documentation can be hosted directly from this directory.
No application server, frontend build step or external asset CDN is required.

```bash
python3 -m http.server 8088 --bind 127.0.0.1 --directory website
```

Open <http://127.0.0.1:8088>. `index.html` and `docs.html` also work through `file://`.
Deploy the **contents of `website/`** to your static host. The language preference
is shared between home and docs, and defaults to the browser language. Optional
local storage failures do not prevent rendering.

## Documentation

After editing files in `docs/` or `docs/en/`, regenerate the embedded static
viewer and its MIT license file:

```bash
uv run python scripts/build_website_docs.py
```

The viewer shares `styles.css` with the homepage and adds reading and responsive
directory styles in `docs.css`. Update the generator for markup changes; do not
edit the generated `docs.html` directly.

Historical `docs/plans/` design notes stay in the repository and are excluded from
the user-facing viewer.

The viewer embeds Markdown for both languages and routes included document links
without requesting `.md` files from the host. Links to a running NiceTool instance
still require that instance. The website never starts or publishes tools itself.

## Workflow media

The workflow is **Codex Desktop → preview → publish → NiceTool Workspace**.
The hero pairs the completed Codex generation scene with the team workspace.
It uses an independent still instance of the same component, so playing or switching
workflow stages cannot change the banner. The complete media is visible without cropping.

- Creation and deployment use a local HTML/CSS walkthrough in `desktop-demo.js`.
  Play types a request in a Codex-style desktop shell, shows generation or publication
  progress, then opens the tool on the right. Creation also demonstrates filtering.
  Deployment types “部署” (or “Deploy”) and opens the published workspace.
  These are workflow illustrations using synthetic data; no network requests or
  actual publication take place. The layout follows the supplied desktop references.
- `preview-zh/en` and `use-zh/en`: real NiceTool recordings with synthetic orders,
  including verified filtering and CSV export. Workspace playback and its poster begin
  on the real tool list, then follow a click into `order_workspace` before filtering.

Creation and deployment start with a still typing scene. Play starts an 26-second
loop; Pause freezes it. Stage changes reset the scene; hiding the page pauses it.
Reduced motion disables incidental CSS transitions and automatic playback remains off.
The other stages load WebP posters and play GIF recordings on request.
Previous AI illustrations and their provenance remain as archived media under
`assets/illustrations/`; they are no longer displayed in the workflow player.

### Rebuild media

Rebuild only the illustrated scenes with Pillow:

```bash
uv run --with pillow python website/demos/render_gifs.py --illustrations website/assets/illustrations --stages create publish
```

The encoder preserves the AI disclosure and animates step markers rather than
pretending to record desktop actions. Do not relabel these images as recordings.

For real recordings, use an isolated NiceTool instance. Save PNG frames under
`preview-zh`, `preview-en`, `use-zh`, `use-en`, with a `manifest.json` like
`[{"file":"00.png","duration":1800}, ...]`. Each needs at least two distinct captured
states. Keep raw captures outside Git, then encode:

```bash
uv run --with pillow python website/demos/render_gifs.py --frames /path/to/frames
```

Set `DEMO_FONT` to a Chinese/English-capable font if the bundled font paths are
not available. The tool source uses synthetic data only; its export was verified
to contain two completed Acme orders.
