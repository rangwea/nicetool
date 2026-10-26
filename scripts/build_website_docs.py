"""Build the static website documentation page from localized docs/*.md files."""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
EN_DOCS_DIR = DOCS_DIR / "en"
OUTPUT = ROOT / "website" / "docs.html"

DOC_ORDER = [
    "README.md",
    "nicetool-skill.md",
    "nicetool-skill-usage.md",
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
        if not {"en", "plans"}.intersection(path.relative_to(DOCS_DIR).parts)
        and path.relative_to(DOCS_DIR) not in ordered
    )
    return ordered + remaining


def website_links(markdown: str, current: Path) -> str:
    """Route included Markdown documents within the static viewer."""
    known = {path.as_posix() for path in ordered_paths() if (DOCS_DIR / path).exists()}

    def replace(match):
        label, target = match.groups()
        path = target.split("#", 1)[0]
        resolved = posixpath.normpath((current.parent / path).as_posix())
        if resolved in known:
            return f"[{label}](#{slug_for(Path(resolved))})"
        if resolved.startswith("../docs/"):
            source = resolved.removeprefix("../docs/").removeprefix("en/")
            if source in known:
                return f"[{label}](#{slug_for(Path(source))})"
        if resolved.startswith("../") and Path(resolved).name in {
            "README.md",
            "README.en.md",
        }:
            return f"[{label}](#project)"
        if resolved in {"../LICENSE", "LICENSE"}:
            return f"[{label}](LICENSE)"
        return match.group(0)

    return re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", replace, markdown)


def project_content(markdown: str) -> str:
    """Omit repository badges and language navigation from the website article."""
    return "\n".join(
        line
        for line in markdown.split("\n")
        if not line.startswith("[![")
        and line
        not in {
            "简体中文 | [English](README.en.md)",
            "[简体中文](README.md) | English",
        }
    )


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
            localized_markdown[lang] = website_links(markdown, rel_path)
            localized_titles[lang] = title_for(markdown, rel_path)
        docs.append(
            LocalizedDoc(
                slug=slug_for(rel_path),
                path=rel_path,
                titles=localized_titles,
                markdown=localized_markdown,
            )
        )
    project_markdown = {
        lang: website_links(
            project_content((ROOT / filename).read_text(encoding="utf-8")),
            Path("../README.md"),
        )
        for lang, filename in (("zh-CN", "README.md"), ("en-US", "README.en.md"))
    }
    docs.insert(
        0,
        LocalizedDoc(
            slug="project",
            path=Path("../README.md"),
            titles={"zh-CN": "项目介绍与快速开始", "en-US": "Overview and quick start"},
            markdown=project_markdown,
        ),
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
    <title>使用文档 — NiceTool</title>
    <meta name="description" content="NiceTool 使用文档：快速开始、工具开发、配置与部署指南。" />
    <meta name="theme-color" content="#f4f7f5" />
    <link rel="icon" href="assets/favicon.svg" type="image/svg+xml" />
    <link rel="stylesheet" href="styles.css?v=20261026-docs-v1" />
    <link rel="stylesheet" href="docs.css?v=20261026-docs-v1" />
  </head>
  <body>
    <a class="skip-link" href="#content" data-i18n="skip">跳至内容</a>
    <header class="site-header">
      <nav class="nav inner" aria-label="Main navigation">
        <a class="brand" href="index.html" aria-label="NiceTool home"><span class="brand-mark">N</span>NiceTool</a>
        <div class="nav-links" id="nav-links"><a href="index.html#demos" data-i18n="nav.demos">流程演示</a><a href="index.html#workflow" data-i18n="nav.workflow">如何工作</a><a href="docs.html" aria-current="page" data-i18n="nav.docs">使用文档</a></div>
        <div class="nav-actions"><button class="language-switch" type="button" data-language-toggle aria-label="Switch to English">EN</button><a class="button button-small" href="#demo" data-i18n="nav.start">开始体验 ↗</a><button class="menu-toggle" type="button" aria-label="Menu" aria-expanded="false" aria-controls="nav-links">☰</button></div>
      </nav>
    </header>
    <main class="inner docs-layout">
      <aside class="docs-directory" aria-label="文档目录">
        <button class="directory-toggle" type="button" aria-controls="doc-list" aria-expanded="false"><span data-i18n="directory">文档目录</span><span aria-hidden="true">⌄</span></button>
        <div class="sidebar" id="doc-list">
          <p class="eyebrow" data-i18n="directory">文档目录</p>
{nav}
        </div>
      </aside>
      <article class="viewer">
        <div class="toolbar"><span id="doc-title">{escape(first.titles["zh-CN"])}</span></div>
        <div id="content" tabindex="-1"></div>
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
          html += '<div class="table-scroll"><table><thead><tr>' + header.map((cell) => `<th>${{inline(cell)}}</th>`).join('') + '</tr></thead><tbody>';
          html += body.map((row) => '<tr>' + row.map((cell) => `<td>${{inline(cell)}}</td>`).join('') + '</tr>').join('');
          html += '</tbody></table></div>';
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
        document.querySelectorAll('.doc-link').forEach((link) => {{
          const active = link.dataset.doc === currentDoc;
          link.classList.toggle('active', active);
          if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
        }});
        document.querySelector('.directory-toggle').setAttribute('aria-expanded', 'false');
        document.querySelector('.docs-directory').classList.remove('open');
        document.title = `${{titles[currentLanguage][currentDoc]}} — NiceTool`;
        history.replaceState(null, '', `#${{currentDoc}}`);
      }}

      const messages = {{
        'zh-CN': {{ skip:'跳至内容', directory:'文档目录', 'nav.demos':'流程演示', 'nav.workflow':'如何工作', 'nav.docs':'使用文档', 'nav.start':'开始体验 ↗' }},
        'en-US': {{ skip:'Skip to content', directory:'Documentation', 'nav.demos':'See it in action', 'nav.workflow':'How it works', 'nav.docs':'Documentation', 'nav.start':'Get started ↗' }}
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
        const toggle = document.querySelector('[data-language-toggle]');
        toggle.textContent = currentLanguage === 'en-US' ? '中文' : 'EN';
        toggle.setAttribute('aria-label', currentLanguage === 'en-US' ? '切换为中文' : 'Switch to English');
        document.querySelector('.docs-directory').setAttribute('aria-label', messages[currentLanguage].directory);
        try {{ localStorage.setItem('nicetool-website-language', currentLanguage); }} catch {{ /* Optional preference. */ }}
        showDoc(currentDoc);
      }}

      document.querySelector('[data-language-toggle]').addEventListener('click', () => setLanguage(currentLanguage === 'zh-CN' ? 'en-US' : 'zh-CN'));
      document.querySelector('.directory-toggle').addEventListener('click', (event) => {{
        const open = document.querySelector('.docs-directory').classList.toggle('open');
        event.currentTarget.setAttribute('aria-expanded', String(open));
      }});
      document.querySelector('.menu-toggle').addEventListener('click', (event) => {{
        const open = document.getElementById('nav-links').classList.toggle('open');
        event.currentTarget.setAttribute('aria-expanded', String(open));
      }});
      document.querySelectorAll('.doc-link').forEach((link) => link.addEventListener('click', () => showDoc(link.dataset.doc)));
      document.getElementById('content').addEventListener('click', (event) => {{
        const anchor = event.target.closest('a');
        if (!anchor) return;
        const href = anchor.getAttribute('href');
        if (href && href.startsWith('#') && titles[currentLanguage][href.slice(1)]) {{
          event.preventDefault();
          showDoc(href.slice(1));
        }}
      }});
      window.addEventListener('hashchange', () => {{
        const slug = decodeURIComponent(location.hash.slice(1));
        if (titles[currentLanguage][slug]) showDoc(slug);
      }});
      currentDoc = decodeURIComponent(location.hash.slice(1)) || defaultDoc;
      let savedLanguage;
      try {{ savedLanguage = localStorage.getItem('nicetool-website-language'); }} catch {{ /* Optional preference. */ }}
      setLanguage(savedLanguage || (navigator.language.toLowerCase().startsWith('zh') ? 'zh-CN' : 'en-US'));
    </script>
  </body>
</html>
"""


def main() -> None:
    docs = load_docs()
    if not docs:
        raise SystemExit("No docs found")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_page(docs), encoding="utf-8")
    (OUTPUT.parent / "LICENSE").write_text(
        (ROOT / "LICENSE").read_text(encoding="utf-8"), encoding="utf-8"
    )
    print(
        f"built {OUTPUT.relative_to(ROOT)} with {len(docs)} docs and {len(LANGUAGES)} languages"
    )


if __name__ == "__main__":
    main()
