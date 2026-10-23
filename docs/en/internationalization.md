# Internationalization

NiceTool supports Chinese and English UI text.

## Application language

Set the language in `.env`:

```env
LANGUAGE=en-US
```

Supported values:

- `zh-CN`
- `en-US`

Restart the server after changing the value.

## Translation files

Runtime translations are stored under `core/i18n/`. UI code should wrap visible text with the translation helper so pages can render in the configured language.

## Static landing site

The static landing site uses a browser-side language switcher. It stores the selected language in `localStorage`. The docs page embeds both Chinese and English Markdown content during build.
