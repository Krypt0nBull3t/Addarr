---
name: i18n-key
description: Use when adding, renaming, or removing a translation key in Addarr, or when a handler needs new user-facing text. Covers the template plus all 9 locale files, the flat-key rule, placeholder and emoji checks, and validation.
---

# Addarr Translation Keys

Every user-facing string lives in `translations/`. A key must exist in the template and in all 9 locales, or `--validate-i18n` fails in CI.

## Files

The template root key is `template:`. Each locale file has its locale code as root key (`en-us:`, `de-de:`, ...).

| File | Root key |
|-|-|
| `translations/addarr.template.yml` | `template` |
| `translations/addarr.de-de.yml` | `de-de` |
| `translations/addarr.en-us.yml` | `en-us` |
| `translations/addarr.es-es.yml` | `es-es` |
| `translations/addarr.fr-fr.yml` | `fr-fr` |
| `translations/addarr.it-it.yml` | `it-it` |
| `translations/addarr.nl-be.yml` | `nl-be` |
| `translations/addarr.pl-pl.yml` | `pl-pl` |
| `translations/addarr.pt-pt.yml` | `pt-pt` |
| `translations/addarr.ru-ru.yml` | `ru-ru` |

## Rules

1. **Flat top-level keys only.** `TranslationService.get_text()` does a single-level `.get(key)`. A nested key such as `Commands.start` never resolves. Use CamelCase at the top level of the root key: `AlbumTracksTitle`, not `Album: {TracksTitle: ...}`.
2. **Same key in all 10 files.** Put it in the same section (the files group keys under `# Section` comments) so the files stay in the same order.
3. **Placeholders must match the template exactly.** The validator compares the `%{name}` set of each value with the template value.
4. **Keep the emoji.** If the template value contains an emoji, every locale value must contain one too.
5. **Translate.** Do not copy the English text into other locales. For `nl-be`, write standard Netherlands Dutch, not Flemish.
6. **Quote values** that start with an emoji or contain `:`, `#`, or `%`.

## Use in code

```python
text = self.translation.get_text("AlbumTracksTitle")
```

Missing keys fall back to `en-us`, then to the key name itself, with a warning in the log.

## Validate

```bash
PYTHONIOENCODING=utf-8 .venv/bin/python run.py --validate-i18n
```

The validator **always exits 0**. Read the output: success is the line `All translations are valid!`. Anything under `Missing keys`, `Extra keys`, `Format errors`, or `Emoji consistency issues` is a failure.

The project PostToolUse hook runs this validator after each edit to a translation file. While you edit the 10 files one by one, it reports the files you have not edited yet. That is expected. After the last file, the hook must pass.

## Rename or remove

Do the same change in all 10 files. Then search `src/` and `tests/` for the old key name and update every `get_text("OldKey")` call.
