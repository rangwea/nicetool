"""Environment-configured platform translations. Business data is never translated implicitly."""

import json
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path

_ENGLISH = json.loads(
    (Path(__file__).parent / "en-US.json").read_text(encoding="utf-8")
)


def normalize_locale(value: str | None) -> str | None:
    if not value:
        return None
    value = value.lower().replace("_", "-")
    return {"zh": "zh-CN", "zh-cn": "zh-CN", "en": "en-US", "en-us": "en-US"}.get(value)


def get_locale() -> str:
    from core.settings import settings

    return normalize_locale(settings.language) or "zh-CN"


def t(message: str, **values) -> str:
    template = _ENGLISH.get(message, message) if get_locale() == "en-US" else message
    return template.format(**values) if values else template


def option_labels(options):
    """Keep select values stable across languages; translate only display labels."""
    if isinstance(options, dict):
        return {
            key: t(label) if isinstance(label, str) else label
            for key, label in options.items()
        }
    return {
        value: t(value) if isinstance(value, str) else str(value) for value in options
    }


def _display_expression(value: str) -> str:
    # Only display expressions are passed here; event handlers and conditions
    # keep their original machine values.
    return re.sub(
        r"'([^']*)'", lambda match: json.dumps(t(match[1]), ensure_ascii=False), value
    )


class _HTMLTranslator(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []
        self.raw_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.raw_depth += 1
        if tag == "html":
            attrs = [
                (key, get_locale() if key == "lang" else value) for key, value in attrs
            ]
        attrs = [
            (key, _display_expression(value) if key == ":label" and value else value)
            for key, value in attrs
        ]
        self.parts.append(
            "<"
            + tag
            + "".join(
                " " + key
                if value is None
                else f' {key}="{escape(t(value) if key in {"placeholder", "title", "aria-label", "label"} else value, quote=True)}"'
                for key, value in attrs
            )
            + ">"
        )

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.parts[-1] = self.parts[-1][:-1] + " />"

    def handle_endtag(self, tag):
        self.parts.append(f"</{tag}>")
        if tag in {"script", "style"}:
            self.raw_depth -= 1

    def handle_data(self, data):
        if self.raw_depth or not data.strip():
            self.parts.append(data)
        else:
            stripped = data.strip()
            if "{{" in stripped:
                translated = re.sub(
                    r"{{(.*?)}}",
                    lambda m: "{{" + _display_expression(m[1]) + "}}",
                    data,
                    flags=re.DOTALL,
                )
                self.parts.append(translated)
            else:
                self.parts.append(data.replace(stripped, escape(t(stripped))))

    def handle_entityref(self, name):
        self.parts.append("&" + name + ";")

    def handle_charref(self, name):
        self.parts.append("&#" + name + ";")

    def handle_decl(self, decl):
        self.parts.append("<!" + decl + ">")

    def handle_comment(self, data):
        self.parts.append("<!--" + data + "-->")


def html_t(markup: str) -> str:
    """Translate static platform markup; never call this on tool/user-provided HTML."""
    parser = _HTMLTranslator()
    markup = markup.replace(
        "toLocaleString('zh-CN')", f"toLocaleString('{get_locale()}')"
    )
    parser.feed(markup)
    return "".join(parser.parts)
