---
title: "Fix translation grammar, wrong terms and untranslated keys"
labels: [bug, i18n, priority:medium]
slice: 29
findings: [F211, F212, F213, F214, F215, F216, F217, F210]
---

## Bug

- **F211** The delete confirm text is ungrammatical: fr "Ce Le film", it "questo Il film", pt "É este A série", de "Möchten sie" (= "do they want").
- **F212** `DeleteSuccess`: de says "entfernt" (= removed). fr has the wrong gender ("La série a été supprimé").
- **F213** de-de uses the English word "Password".
- **F214** pt-pt uses Brazilian forms ("Configurações", "mídia", "Precisa se autenticar").
- **F215** The pl and ru `MusicWithArticle` gender breaks the templates ("Ta muzyka został usunięty", "Этот музыка").
- **F216** `HistoryGrabbed` is translated as "Downloaded" in 6 locales.
- **F217** nl-be "Geef de zoekterm:" misses "in". nl-be also uses Flemish forms, but the i18n-key skill and the owner's rule ask for Netherlands Dutch.
- **F210** About 80 keys are still English in all 8 locales: the add and delete flows, `Help*`, `Bazarr*`, `Webhook*` and `*Error`.

## Steps to reproduce

1. Set the language to fr-fr. Send /delete and pick a movie. The prompt reads "Ce Le film est-il à supprimer ?". Do the same in it-it (movie), pt-pt (series) and de-de. (F211)
2. In de-de, confirm a delete: the reply says "entfernt". In fr-fr, delete a series: "La série a été supprimé". (F212)
3. In de-de, send /auth: "Bitte gib dein Password ein." (F213)
4. In pt-pt, open Settings: "Configurações". Send a command before /auth: "Precisa se autenticar primeiro." (F214)
5. In pl-pl, delete an artist: "Ta muzyka został pomyślnie usunięty". In ru-ru, the delete prompt reads "Этот музыка". (F215)
6. In es-es, fr-fr, it-it, pl-pl, pt-pt or ru-ru, open /history: grabbed events read "Downloaded" (es "Descargado"). (F216)
7. In nl-be, start a search: the prompt reads "Geef de zoekterm:". (F217)
8. In any non-English locale, open /help or trigger a search error: the text is English. (F210)

## Expected behavior

Each locale reads as correct, natural text in that language, with the same placeholders and emoji as the template. Dutch is the `nl-nl` locale in Netherlands Dutch. `language: nl-be` still works and loads `nl-nl`.

## Fix

- [ ] **F211** Set `ThisDelete` to the text below, after the leading question-mark emoji the values already have (`translations/addarr.{fr-fr,it-it,pt-pt,de-de}.yml:71`):
  - fr: `Est-ce %{subjectWithArticle} que vous souhaitez supprimer ?`
  - it: `Vuoi eliminare %{subjectWithArticle}?`
  - pt: `Pretende eliminar %{subjectWithArticle}?`
  - de: `Möchtest du %{subjectWithArticle} wirklich löschen?`
- [ ] **F212** Set `DeleteSuccess`, keeping the leading check-mark emoji and the trailing smiley the values already have (`translations/addarr.de-de.yml:75`, `translations/addarr.fr-fr.yml:75`):
  - de: `%{subjectWithArticle} wurde erfolgreich gelöscht` (only "entfernt" changes)
  - fr: `Suppression réussie : %{subjectWithArticle}`
- [ ] **F213** Replace "Password" with "Passwort" (`translations/addarr.de-de.yml:58`, `:110`, `:111`)
- [ ] **F214** Replace "Configurações" with "Definições", "mídia" with "média", and "Precisa se autenticar primeiro." with "Precisa de se autenticar primeiro." (`translations/addarr.pt-pt.yml:10`, `:18`, `:19`, `:62`, `:279`, `:281`)
- [ ] **F215** Set `MusicWithArticle` to pl `Ten wykonawca` and ru `исполнитель` (`translations/addarr.pl-pl.yml:35`, `translations/addarr.ru-ru.yml:35`)
- [ ] **F216** Set `HistoryGrabbed` to es `Capturado`, fr `Récupéré`, it `Acquisito`, pl `Przechwycono`, pt `Capturado`, ru `Захвачено` (`translations/addarr.{es-es,fr-fr,it-it,pl-pl,pt-pt,ru-ru}.yml:297`)
- [ ] **F217** Add an `nl-nl` locale in Netherlands Dutch. Follow the `i18n-key` skill:
  - Rename `translations/addarr.nl-be.yml` to `addarr.nl-nl.yml` and set its root key to `nl-nl`.
  - Set `Title` to `Geef een zoekterm in:` after the leading magnifier emoji the value already has. Replace the Flemish forms ("Je kan", "ingeven", "vooraleer") with Netherlands Dutch (old file `:58`, `:60`, `:113`, `:207`, `:209`).
  - Map `language: nl-be` to `nl-nl` as an alias (`src/services/translation.py:41`). Accept both codes in `src/config/settings.py:196` and `src/utils/validation.py:59`.
  - Offer `nl-nl` in the wizard and the language menu (`src/setup/prompts.py:95`, `src/bot/keyboards.py:175`).
  - Update `config_example.yaml:177`, `README.md:576`, `:719` and the `i18n-key` skill (file table and the Netherlands Dutch rule; slice 26, F295, edits the same skill).
- [ ] **F210** Translate the ~80 English keys in all 8 locales (`translations/*.yml:303-317` and others)

## Acceptance criteria

- [ ] F211-F216: a test in `tests/test_services/test_translation_service.py` loads the shipped files (as `test_shipped_files_resolve_keys`, line 253, does) and asserts the new values: `ThisDelete` (fr, it, pt, de), `DeleteSuccess` (de, fr), no "Password" in de-de, no "Configurações", "mídia" or "Precisa se" in pt-pt, `MusicWithArticle` (pl, ru) and `HistoryGrabbed` (6 locales). It fails before the fix.
- [ ] F217: `tests/test_services/test_translation_service.py`: with `language: nl-be`, the current language is `nl-nl` and texts come from `addarr.nl-nl.yml`. The shipped-files test asserts that nl-nl `Title` is the magnifier emoji plus `Geef een zoekterm in:` and that nl-nl has no "Je kan", "ingeven" or "vooraleer". `tests/test_bot/test_keyboards.py`: the Dutch button sends `lang_nl-nl`. Each fails before the fix.
- [ ] F210: the English-copy check from slice 25 (F204) reports no English copy in the 8 locales, apart from an allowlist of words that are the same in the target language (service names and similar).
- [ ] Every change follows the `i18n-key` skill (template plus all 9 locales; placeholders and emoji match).
- [ ] `pytest`, `flake8`, `mypy src/` and `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F211, F212, F213, F214, F215, F216, F217, F210).
- Priority: max P 15 (F211), sum P 83, `priority:medium`.
- Decided 2026-10-28: F217 add an `nl-nl` locale in Netherlands Dutch; `language: nl-be` keeps working as an alias mapped to `nl-nl`; the wizard offers `nl-nl`.
- F211 edits `ThisDelete`, which slice 1 (F003) also changes (adds `%{title}` and the file-deletion text). Land slice 1 first or merge the wording.
- F210 relies on the English-copy check of slice 25 (F204). Slice 27 (F120) edits `Help*` keys in the same files.
- Related open issues: none.
