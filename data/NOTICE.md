# Word study sources

Word and lexical metadata: **STEP Bible**, https://www.stepbible.org/.
Source repository: https://github.com/STEPBible/STEPBible-Data.
License: Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/.
Data originated at Tyndale House Cambridge and is curated by STEP Bible.

This application reformats a subset of TAGNT, TAHOT, TBESG and TBESH as a local SQLite index. It includes Greek words marked NA28 and Hebrew primary L/Q/R rows; other Greek editions, Hebrew X additions and alternate readings are omitted. Original lexical tags, glosses, forms, transliterations and morphology are retained. For 26 corpus IDs absent from the separate brief lexicons, corpus dictionary-form/gloss metadata is exposed as a distinct entry; its transliteration comes from an attested word form. These entries are labeled as corpus glossary data, without guessed full definitions. References follow STEP English/NRSV versification. Inflected words may include attached Hebrew prefixes/suffixes; the lexical match may concern only one component of the displayed word.

TBESG Greek definitions are included. TBESH full Hebrew definitions are **excluded** because its header requests permission from Online Bible for applying those definitions. Hebrew metadata and concise STEP glosses (columns 0–6) are retained. No Hebrew full-definition text is copied into this index.

Verse previews: **World English Bible (WEB)**, public domain, https://worldenglish.bible/; downloaded from https://bolls.life/static/translations/WEB.json. Only books 1–66 are included. HTML markup is removed for plain-text display. WEB English verses are not aligned word-for-word to the STEP original-word tags and can follow different textual readings or versification.

`word_sources.json` records file fingerprints, selected corpus, counts, transformations, and the uncompressed database fingerprint. `scripts/build_word_data.py` reproduces the transformation from the listed source TSV files plus WEB.json. This is a 2026-10-07 snapshot; source updates are not downloaded automatically.

Occurrence counts use the selected **extended lexical ID**, distinguishing words sharing a basic Strong's number. Legacy saved studies without an extended ID use broader Strong's-number grouping, explicitly labeled in the app. Counts are token counts; verse counts and book counts are displayed separately. They can differ from Blue Letter Bible or another edition.

The AI explanation is generated application content, separate from the source dataset. It may contain interpretive errors. Its reference labels are checked against supplied passages; this check does not establish that every claim follows from that evidence.
