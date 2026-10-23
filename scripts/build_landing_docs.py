"""Build the static landing documentation page from localized docs/*.md files."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
EN_DOCS_DIR = DOCS_DIR / "en"
OUTPUT = ROOT / "landing" / "docs.html"

DOC_ORDER = [
    "README.md",
    "nicetool-skill.md",
    "nicetool-skill-usage.md",
    "nicechart-skill.md",
    "demo.md",
    "user-guide.md",
    "configuration.md",
    "deployment.md",
    "upgrading.md",
    "tool-development.md",
    "api.md",
    "internationalization.md",
    "oauth2-auth.md",
    "nicetool-token-setup.md",
    "contributing.md",
    "plans/2026-09-11-project-rbac-design.md",
]
LANGUAGES = ("zh-CN", "en-US")
DOC_ROOTS = {"zh-CN": DOCS_DIR, "en-US": EN_DOCS_DIR}


@dataclass(frozen=True)
class LocalizedDoc:
    slug: str
    path: Path
    titles: dict[str, str]
    markdown: dict[str, str]


def slug_for(path: Path) -> str:
    return path.with_suffix("").as_posix().replace("/", "-")


def title_for(markdown: str, path: Path) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").title()


def ordered_paths() -> list[Path]:
    ordered = [Path(item) for item in DOC_ORDER]
    remaining = sorted(
        path.relative_to(DOCS_DIR)
        for path in DOCS_DIR.rglob("*.md")
        if "en" not in path.relative_to(DOCS_DIR).parts
        and path.relative_to(DOCS_DIR) not in ordered
    )
    return ordered + remaining


def load_docs() -> list[LocalizedDoc]:
    docs = []
    for rel_path in ordered_paths():
        zh_path = DOCS_DIR / rel_path
        if not zh_path.exists():
            continue
        localized_markdown = {}
        localized_titles = {}
        fallback = zh_path.read_text(encoding="utf-8")
        for lang in LANGUAGES:
            candidate = DOC_ROOTS[lang] / rel_path
            markdown = (
                candidate.read_text(encoding="utf-8")
                if candidate.exists()
                else fallback
            )
            localized_markdown[lang] = markdown
            localized_titles[lang] = title_for(markdown, rel_path)
        docs.append(
            LocalizedDoc(
                slug=slug_for(rel_path),
                path=rel_path,
                titles=localized_titles,
                markdown=localized_markdown,
            )
        )
    return docs


def js_string(value: str) -> str:
    return repr(value)


def render_page(docs: list[LocalizedDoc]) -> str:
    first = docs[0]
    nav = "\n".join(
        f'        <button class="doc-link{" active" if doc == first else ""}" data-doc="{escape(doc.slug)}">'
        f'<span data-doc-title="{escape(doc.slug)}">{escape(doc.titles["zh-CN"])}</span></button>'
        for doc in docs
    )
    embedded = "\n\n".join(
        f'    <script type="text/markdown" id="doc-{lang}-{escape(doc.slug)}">\n{doc.markdown[lang]}\n    </script>'
        for lang in LANGUAGES
        for doc in docs
    )
    title_map = (
        "{\n"
        + ",\n".join(
            "        "
            + js_string(lang)
            + ": {"
            + ", ".join(
                js_string(doc.slug) + ": " + js_string(doc.titles[lang]) for doc in docs
            )
            + "}"
            for lang in LANGUAGES
        )
        + "\n      }"
    )
    default_slug = first.slug
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>NiceTool Docs - 静态文档</title>
    <meta name="description" content="NiceTool 静态文档查看页，由 docs 目录 Markdown 构建生成，不依赖 NiceTool server。" />
    <style>
      :root {{ --ink:#111827; --muted:#5b6475; --line:#e5e7eb; --blue:#2563eb; --surface:#f8fafc; --code:#0f172a; }}
      * {{ box-sizing: border-box; }}
      body {{ margin:0; color:var(--ink); background:#fff; font-family:Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height:1.65; }}
      a {{ color:inherit; text-decoration:none; }}
      .wrap {{ width:min(1180px, calc(100% - 40px)); margin:0 auto; }}
      .nav {{ position:sticky; top:0; z-index:10; border-bottom:1px solid rgba(229,231,235,.86); background:rgba(255,255,255,.92); backdrop-filter:blur(14px); }}
      .nav-inner {{ min-height:72px; display:flex; align-items:center; justify-content:space-between; gap:24px; }}
      .brand {{ display:flex; align-items:center; gap:22px; color:#111827; font-size:28px; font-weight:850; letter-spacing:-.03em; }}
      .brand-mark {{ display:grid; width:72px; height:72px; place-items:center; border-radius:18px; color:#fff; background:#111827; font-size:32px; font-weight:850; letter-spacing:0; box-shadow:0 16px 34px rgba(17,24,39,.12); }}
      .nav-links {{ display:flex; align-items:center; gap:18px; color:#4b5563; font-size:14px; font-weight:650; }}
      .lang-switch {{ display:inline-flex; align-items:center; gap:4px; border:1px solid var(--line); border-radius:999px; padding:4px; background:#fff; }}
      .lang-button {{ border:0; border-radius:999px; padding:5px 10px; color:#64748b; background:transparent; font:inherit; font-size:13px; font-weight:750; cursor:pointer; }}
      .lang-button.active {{ color:#fff; background:var(--ink); }}
      h1 {{ max-width:820px; margin:22px 0 12px; font-size:clamp(38px,5vw,58px); line-height:1.08; }}
      .layout {{ display:grid; grid-template-columns:300px minmax(0,1fr); gap:28px; padding:28px 0 84px; }}
      .sidebar {{ position:sticky; top:96px; height:calc(100vh - 120px); overflow:auto; border:1px solid var(--line); border-radius:16px; padding:10px; background:#fff; }}
      .doc-link {{ display:block; width:100%; border:0; border-radius:10px; padding:11px 12px; color:#4b5563; background:transparent; font:inherit; font-weight:500; text-align:left; cursor:pointer; }}
      .doc-link span {{ display:block; }}
      .doc-link:hover, .doc-link.active {{ color:var(--ink); background:#eff6ff; }}
      .viewer {{ min-width:0; border:1px solid var(--line); border-radius:18px; padding:34px; background:#fff; box-shadow:0 16px 48px rgba(15,23,42,.06); }}
      .viewer h1, .viewer h2, .viewer h3, .viewer h4 {{ line-height:1.25; }}
      .viewer h1 {{ margin-top:0; font-size:36px; }}
      .viewer h2 {{ margin-top:34px; padding-top:24px; border-top:1px solid var(--line); font-size:26px; }}
      .viewer h3 {{ margin-top:24px; font-size:20px; }}
      .viewer h4 {{ margin-top:20px; font-size:16px; }}
      .viewer p, .viewer li {{ color:#4b5563; }}
      .viewer a {{ color:var(--blue); font-weight:700; }}
      .viewer code {{ border-radius:6px; padding:2px 6px; background:#eef2f7; color:#0f172a; font-size:.92em; }}
      .viewer pre {{ overflow:auto; border-radius:14px; padding:18px; background:var(--code); color:#e5e7eb; }}
      .viewer pre code {{ padding:0; background:transparent; color:inherit; }}
      .viewer blockquote {{ margin:18px 0; border-left:4px solid var(--blue); padding:2px 0 2px 16px; color:#475569; background:#f8fafc; }}
      .viewer table {{ width:100%; border-collapse:collapse; margin:18px 0; }}
      .viewer th, .viewer td {{ border:1px solid var(--line); padding:10px 12px; text-align:left; vertical-align:top; }}
      .viewer th {{ background:#f8fafc; }}
      .toolbar {{ display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:18px; color:#64748b; font-size:14px; }}
      @media (max-width: 900px) {{ .layout {{ grid-template-columns:1fr; }} .sidebar {{ position:static; height:auto; max-height:420px; }} .nav-links {{ gap:12px; }} }}
    </style>
  </head>
  <body>
    <nav class="nav">
      <div class="wrap nav-inner">
        <a class="brand" href="./index.html" aria-label="NiceTool"><span class="brand-mark">N</span><span>NiceTool</span></a>
        <div class="nav-links"><a href="./index.html#features" data-i18n="nav.features">平台能力</a><a href="./index.html#workflow" data-i18n="nav.workflow">工作流</a><a href="./docs.html" data-i18n="nav.docs">文档</a><div class="lang-switch" aria-label="Language"><button class="lang-button" type="button" data-lang="zh-CN">中</button><button class="lang-button" type="button" data-lang="en-US">EN</button></div></div>
      </div>
    </nav>
    <main class="wrap layout">
      <aside class="sidebar" aria-label="文档目录">
{nav}
      </aside>
      <article class="viewer">
        <div class="toolbar"><span id="doc-title">{escape(first.titles["zh-CN"])}</span></div>
        <div id="content"></div>
      </article>
    </main>

{embedded}

    <script>
      const titles = {title_map};
      const defaultDoc = {default_slug!r};
      let currentDoc = defaultDoc;
      let currentLanguage = 'zh-CN';
      const escapeHtml = (value) => value.replace(/[&<>\"]/g, (char) => ({{ '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;' }})[char]);
      const inline = (text) => escapeHtml(text)
        .replace(/!\\[([^\\]]*)\\]\\(([^)]+)\\)/g, '<span>$1</span>')
        .replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, '<a href="$2">$1</a>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');

      function renderMarkdown(markdown) {{
        const lines = markdown.trim().split('\\n');
        let html = '';
        let inCode = false;
        let code = [];
        let list = [];
        let table = [];
        const flushList = () => {{
          if (!list.length) return;
          html += '<ul>' + list.map((item) => `<li>${{inline(item)}}</li>`).join('') + '</ul>';
          list = [];
        }};
        const flushTable = () => {{
          if (table.length < 2) {{ table = []; return; }}
          const rows = table.map((row) => row.split('|').slice(1, -1).map((cell) => cell.trim()));
          const header = rows[0];
          const body = rows.slice(2);
          html += '<table><thead><tr>' + header.map((cell) => `<th>${{inline(cell)}}</th>`).join('') + '</tr></thead><tbody>';
          html += body.map((row) => '<tr>' + row.map((cell) => `<td>${{inline(cell)}}</td>`).join('') + '</tr>').join('');
          html += '</tbody></table>';
          table = [];
        }};
        const flushBlocks = () => {{ flushList(); flushTable(); }};
        for (const rawLine of lines) {{
          const line = rawLine.trimEnd();
          if (line.startsWith('```')) {{
            flushBlocks();
            if (inCode) {{
              html += `<pre><code>${{escapeHtml(code.join('\\n'))}}</code></pre>`;
              code = [];
              inCode = false;
            }} else {{
              inCode = true;
            }}
            continue;
          }}
          if (inCode) {{ code.push(rawLine); continue; }}
          if (!line.trim()) {{ flushBlocks(); continue; }}
          if (/^\\|.*\\|$/.test(line)) {{ flushList(); table.push(line); continue; }}
          flushTable();
          if (line.startsWith('# ')) {{ flushList(); html += `<h1>${{inline(line.slice(2))}}</h1>`; continue; }}
          if (line.startsWith('## ')) {{ flushList(); html += `<h2>${{inline(line.slice(3))}}</h2>`; continue; }}
          if (line.startsWith('### ')) {{ flushList(); html += `<h3>${{inline(line.slice(4))}}</h3>`; continue; }}
          if (line.startsWith('#### ')) {{ flushList(); html += `<h4>${{inline(line.slice(5))}}</h4>`; continue; }}
          if (/^[-*] /.test(line)) {{ list.push(line.slice(2)); continue; }}
          if (/^\\d+\\. /.test(line)) {{ list.push(line.replace(/^\\d+\\. /, '')); continue; }}
          if (line.startsWith('> ')) {{ flushList(); html += `<blockquote>${{inline(line.slice(2))}}</blockquote>`; continue; }}
          flushList();
          html += `<p>${{inline(line)}}</p>`;
        }}
        flushBlocks();
        return html;
      }}

      function showDoc(name) {{
        currentDoc = titles[currentLanguage][name] ? name : defaultDoc;
        const source = document.getElementById(`doc-${{currentLanguage}}-${{currentDoc}}`);
        document.getElementById('doc-title').textContent = titles[currentLanguage][currentDoc];
        document.getElementById('content').innerHTML = renderMarkdown(source.textContent);
        document.querySelectorAll('.doc-link').forEach((link) => link.classList.toggle('active', link.dataset.doc === currentDoc));
        history.replaceState(null, '', `#${{currentDoc}}`);
      }}

      const messages = {{
        'zh-CN': {{ 'nav.features': '平台能力', 'nav.workflow': '工作流', 'nav.docs': '文档' }},
        'en-US': {{ 'nav.features': 'Capabilities', 'nav.workflow': 'Workflow', 'nav.docs': 'Docs' }}
      }};
      function setLanguage(lang) {{
        currentLanguage = messages[lang] ? lang : 'zh-CN';
        document.documentElement.lang = currentLanguage;
        document.querySelectorAll('[data-i18n]').forEach((node) => {{
          node.textContent = messages[currentLanguage][node.dataset.i18n] || node.textContent;
        }});
        document.querySelectorAll('[data-doc-title]').forEach((node) => {{
          node.textContent = titles[currentLanguage][node.dataset.docTitle] || node.textContent;
        }});
        document.querySelectorAll('[data-lang]').forEach((button) => {{
          button.classList.toggle('active', button.dataset.lang === currentLanguage);
        }});
        localStorage.setItem('nicetool-landing-language', currentLanguage);
        showDoc(currentDoc);
      }}

      document.querySelectorAll('[data-lang]').forEach((button) => button.addEventListener('click', () => setLanguage(button.dataset.lang)));
      document.querySelectorAll('.doc-link').forEach((link) => link.addEventListener('click', () => showDoc(link.dataset.doc)));
      currentDoc = decodeURIComponent(location.hash.slice(1)) || defaultDoc;
      setLanguage(localStorage.getItem('nicetool-landing-language') || (navigator.language === 'zh-CN' ? 'zh-CN' : 'en-US'));
    </script>
  </body>
</html>
"""


def main() -> None:
    docs = load_docs()
    if not docs:
        raise SystemExit("No docs found")
    OUTPUT.write_text(render_page(docs), encoding="utf-8")
    print(
        f"built {OUTPUT.relative_to(ROOT)} with {len(docs)} docs and {len(LANGUAGES)} languages"
    )


if __name__ == "__main__":
    main()
