# Scripture · Study & Remember

A personal Bible study workspace with saved studies, source-based transcript questions, semantic search, topic exploration, and lexical guidance.

## New: a calmer interface and verse memorization

The interface now has grouped navigation (Start, Study, Practice, Your library), a personalized home screen, a daily review shortcut, more comfortable controls, visible keyboard focus, responsive practice cards, horizontally scrollable tabs, and reduced-motion support. Existing passage, word, sermon, topic, search, and notes tools remain available.

Open **Verse Memorization** in the sidebar:

1. In **Add a verse**, enter a verse or a same-chapter range of up to five verses, select your Bible version, and optionally name a collection. No Gemini key is needed.
2. In **Practice**, choose the due queue or all verses. Use **Flashcard** to recall and reveal, **Hide words** to gradually remove cues, or **Typed recall** to compare your attempt with the actual text.
3. After revealing the verse, choose **Again**, **Hard**, **Good**, or **Easy**. Again schedules tomorrow; the other ratings gradually extend the interval. Reviews are recorded only when you choose a rating, not on page refresh or reveal.
4. **My deck** lists collections, next review dates, and review counts. Removal requires checking the confirmation box. Download a reference-and-progress export; My Studies' account backup includes the deck too.
5. Passage Study's **Practice memorizing this passage** shortcut carries over your reference and version. It does not add a card until you submit the Add a verse form.

Typed recall ignores case, punctuation, and typographic apostrophe differences. Its wording-match percentage penalizes missing and extra words; it is a practice aid, not an AI judgment of understanding. You select your own review rating. Changing modes or starting a fresh attempt resets that attempt; ordinary reruns keep it.

Review progress, collections, and dates save separately for each signed-in account in the existing SQLite database. Re-adding the same canonical reference/version updates its collection without resetting progress. Different translations are separate cards. The home screen shows due cards, today's reviews, and a streak of consecutive review days (a streak remains active if the most recent day was yesterday). Dates default to `America/Los_Angeles`; set `SCRIPTURE_TIMEZONE` to another IANA timezone if needed.

**Cost and text access:** the feature makes no AI calls and requires no new paid service. WEB works offline. Other versions use your existing authorized provider access and quota. Cards store references and progress, never copyrighted verse text; an active practice session reuses its loaded verse, and reopening a licensed card retrieves it again. Provider failures retain the deck and offer an explicit retry. Free hosting still needs external persistent storage if users must reliably retain accounts/progress across redeployments. There are no background notifications or accountability-partner features in this release.

**Update:** stop Streamlit, extract the complete new ZIP into a separate folder, copy your existing `.env`, keep your `SCRIPTURE_DATA_DIR` setting, and restart. Existing accounts/studies remain in that same data folder; the new tables are created automatically. If you customized the translation choices in `translations.py`, carry those choices into the new file as well.

## New: Bible versions and clear word meanings

**Bible version** is now selectable in Passage Study and Word Study: WEB, ESV, NIV, NLT, CSB, and NKJV. The selected version follows word/passage links and chapter navigation. Passage notes remain shared for the same reference; generated backgrounds are retained separately for each version, so switching to NIV does not display a WEB-based background as if it were NIV-based.

WEB is bundled and works offline. The other versions load one chapter on demand through authorized provider connections. An unavailable version reports the access problem; the app never substitutes another translation without your selection.

### Enable the requested versions

1. Create an application at [API.Bible](https://api.bible/) and enable the translations you want to use. Account/plan access determines which versions its API key can retrieve. Copy the application key into `.env` as `API_BIBLE_KEY`.
2. ESV can use API.Bible if available to your key, or the direct [Crossway ESV API](https://api.esv.org/docs/). Add its key as `ESV_API_KEY`; the direct provider is preferred for ESV when this is set.
3. Restart Streamlit after changing `.env`.
4. Select a version, then **Read passage**. Merely choosing a dropdown value does not make an API call.

```dotenv
API_BIBLE_KEY=your_api_bible_application_key
# Optional alternative for ESV:
ESV_API_KEY=your_crossway_esv_key
```

The app uses your authorized API.Bible English catalog to resolve the requested version. If more than one edition has the same abbreviation, specify its ID using `API_BIBLE_NIV_ID`, `API_BIBLE_NLT_ID`, `API_BIBLE_CSB_ID`, `API_BIBLE_NKJV_ID`, or `API_BIBLE_ESV_ID`. IDs must belong to that requested version and be available to your key; an ID for a different translation is rejected.

Publisher copyright notices are shown with the text and retained in downloads. API.Bible attribution and returned view-tracking information are rendered using its documented tracker (or legacy tracking image). Copyrighted chapter text is kept in the active session, not bundled into the app or written into study records/backups. Saved studies retain the reference, version, original-word tags, explanations, and personal notes; reopening an online version retrieves the text again. Failed reopen requests can be retried explicitly without another request on every ordinary rerun.

### A definition that explains the word

The overview no longer depends only on a short gloss like **witness**. **Include a clear meaning explanation** is enabled by default; with your Gemini key, selecting a word generates and saves a concise explanation from the selected lexical entry, tagged forms, passage/chapter, and retrieved occurrences. It appears in the word card and overview:

- **Plain-language meaning:** what the original word refers to, beyond a repeated gloss or synonyms.
- **Meaning in this passage:** the specific sense supported by the selected verse(s).
- **Why this meaning fits:** concrete sentence/paragraph evidence.
- **Other possible senses:** kept distinct from the current use.
- **Interpretive boundary and source references.**

For example, try `witness` with `Acts 1:8`, then select the original noun G3144 if it appears among the matches. The prompt distinguishes a person giving testimony from testimony itself, and does not automatically equate the word with martyrdom. It uses the actual selected entry and passage rather than a hardcoded definition of the English query.

When no passage is supplied, or the selected lexical ID is absent, the app gives only a general sourced explanation and leaves the passage-specific fields blank. Generated references must match supplied source labels. This reference check does not prove every interpretation is correct.

Uncheck the option for source-only lookup. Without a Gemini key, the fuller lexical source is visible immediately, with the short gloss separated into an expander. **Explain this word clearly** can generate/retry the short explanation later; the longer **Explain this passage in depth** remains available separately.

Selected passage text uses your chosen version. Same-word occurrence previews remain WEB and are labeled separately; the original-language index stays STEP/NA28 or TAHOT. English words are not individually aligned to the original-language tags. Translation choice does not change that lexical index or its occurrence counts.

## New: read and study side by side

Passage Study now displays a Bible reading panel beside Context, Word study, Related reading, My notes, and Sources & download. It uses the WEB text already bundled with the word index.

- **Read passage** opens a chapter or same-chapter verse range without Gemini. WEB works without internet access; other versions require their provider connection. Reading-only studies save to My Studies, so you can take notes before generating any background.
- **Explore context** is a separate explicit action. It sends the displayed passage's full surrounding chapter in the selected version to the configured Gemini model with the reference and optional commentary URL.
- **Previous/next chapter** moves within a book and across book boundaries. Navigation opens text and any background already saved for that exact chapter reference; it never generates background or displays another passage's explanation. Buttons are disabled at Genesis 1 / Revelation 22.
- **Read surrounding context** expands the full chapter with your selected verses highlighted. **Read the full chapter** changes the current study to that chapter.
- **Word study** lets you type a word or Strong's number and select the current range or a specific verse. The selected reference follows the word into the upgraded Word Study tool. English words are not yet linked individually to original-language tags.
- **My notes** work before or after generation. Reopening a saved passage preserves its note and explanation. Different passage selections have separate notes.
- Markdown exports include the selected Bible text, available background, personal notes, and generated related reading. A plain-text WEB download is also available.

References opened from sermons, word occurrences, or related reading now load Bible text locally. These handoffs do not trigger AI generation. Older saved explanations still open; a local reading view is added where the reference fits a single chapter. Unsupported multi-chapter references retain their explanation and notes, with a prompt to enter a supported reading selection.

Stop the old app, extract the complete ZIP into a new folder, copy your existing `.env` into `bible-study-app`, and run the Mac commands below. Keep your current data folder setting to retain accounts and studies. This release includes the earlier word study upgrade and its complete data folder.

## Enhanced Word Study

1. Enter `love` and `John 15:9–17`, then **Find word**.
2. Choose the intended original word. The verb `ἀγαπάω` (G25) and noun `ἀγάπη` (G26) are separate choices; matches in your passage are listed first.
3. **Word overview** shows the script, transliteration, Strong's number, concise gloss, and expandable Greek lexical definition.
4. **Meaning in context** displays WEB verse text, verifies the selected lexical ID in the STEP edition, shows its inflected form and sourced grammar, and lets you read the surrounding chapter.
5. Select **Explain this passage in depth** for a structured Gemini explanation: contextual meaning, grammar, surrounding argument, background, comparisons, interpretation limits, and reflection questions. An optional clarification field focuses the explanation. A word absent from the selected passage cannot generate an explanation.
6. **Other occurrences** provides sourced counts, book filters, paginated verse previews, original forms, and links into Passage Study. **Sources & download** offers Markdown study export and a complete occurrence CSV.

Word lookup, verification, verse previews, and concordance work **offline without API keys**. The first lookup expands a bundled compressed index into the existing data folder; allow roughly 200 MB of disk space. Only the in-depth AI explanation uses Gemini and requires your configured API key and quota. No extra package or API subscription is needed.

This version uses a bundled STEP Bible snapshot, not Blue Letter Bible's own dataset. Source edition labels and licensing details are in `data/NOTICE.md` and `data/word_sources.json`. Greek definitions use TBESG. Hebrew provides original forms, transliterations, concise glosses, tagged occurrences, and contextual explanation, but full Hebrew definitions are not bundled. WEB English previews are not aligned word-for-word to the original-language tags. Some textual readings and verse numbering can differ.

Old saved word studies remain readable, including their notes and guidance. An explicit **Load passage and verify word** action adds passage data; opening an old record does not call Gemini. Newly selected lexical IDs have distinct saved-study identities, so different Greek/Hebrew equivalents do not share notes accidentally. Existing account databases and notes are kept outside the project folder. Search by Meaning includes the saved word explanation.

### Upgrade on your Mac

Stop the previous app with Control+C. Extract this full ZIP into a new folder, copy your existing `.env` into it, and keep the same `SCRIPTURE_DATA_DIR` if you configured one. From that folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Do not copy the old app's Python files over this version. The complete `data` folder is required. Your existing account and saved studies remain in `~/.scripture-study` unless configured otherwise.

## Phase 6: advanced tools

### Ask a sermon

New sermon summaries retain the original transcript in your local saved study. Open **Ask this sermon**, enter a specific question, and submit. The app splits the transcript into overlapping excerpts, retrieves the six most similar to your question using Gemini embeddings, and asks Gemini to answer only from those excerpts.

The response must include short quotations tied to the retrieved excerpt numbers. The app checks that each quotation occurs in the matching excerpt, ignoring capitalization and whitespace. An answer without verified evidence is rejected. If the model says evidence is insufficient, the app displays an abstention instead of a substantive answer. This does not prove that every claim follows from its quotations, and retrieval can miss relevant parts of the sermon.

The latest 20 questions and answers are saved with that sermon result and included in Markdown downloads and account backups. Regenerating the same sermon format keeps this history if the transcript is unchanged; a changed transcript starts a new question history. Each question is independent, rather than a conversational chat with previous questions supplied as context.

Older saved sermons have no transcript. The tab offers **Load original transcript**: this makes one explicit SerpAPI retrieval and saves the transcript. Merely opening an old sermon does not fetch it.

### Search by Meaning

The new page searches the signed-in account's saved studies by embedding similarity. It includes generated study content and available sermon transcripts. Filter by type or bookmarks; optionally include personal notes. Personal notes are excluded by default.

Submitting a search sends study excerpts and your query to the configured Gemini embedding API. It does not generate a new study answer. Local cached document embeddings are reused when the model, content, and inclusion settings match. New or changed content must be embedded; each query also makes an embedding call. Embedding calls use your provider quota. Opening a page or adjusting an unsubmitted form makes no call.

Results show the best matching excerpt from each study and a cosine similarity score. This score is not a confidence percentage. The closest eight studies are returned; a high rank does not establish relevance or truth. The original keyword search in My Studies remains available without embedding calls.

### Related passages and Topic Study

A passage result's **Related passages** tab can generate suggested reading with a reason and a context caution for each connection. These suggestions are saved and can open Passage Study with the reference filled in.

The new **Topic Study** page creates an exploratory overview, themes, suggested passages, and reflection questions. Topic guides are saved, searchable, bookmarkable, and support personal notes like the other tools.

These are AI-generated connections, not a retrieved or independently verified cross-reference database. Read the suggested passages in context; their reference labels and connections can be wrong. These tools request no Bible quotations and do not independently fetch Scripture text.

### Contextual word guidance

The earlier dictionary-only guidance has been replaced by **Meaning in context**, described above. Previously saved guidance remains readable in an expander. New explanations require a source-verified occurrence in the selected passage and use tagged forms plus chapter text.

### Configure embeddings

The default is `GEMINI_EMBEDDING_MODEL=gemini-embedding-001`; set this in `.env` if you need a different compatible embedding model from your account. The implementation uses `RETRIEVAL_DOCUMENT` for source excerpts, `RETRIEVAL_QUERY` for questions, and 768-dimensional vectors. Your model must support these settings. Restart Streamlit after changing configuration.

The existing `GEMINI_MODEL` remains the generation model. Embeddings and generated answers are different API operations with separate model names. Safe error details now display both settings. No live calls were made using your keys during development.

## Start on your Mac

Extract the ZIP into a new folder. Open a terminal inside `bible-study-app`. Use Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Copy your existing `.env` into the new folder. If starting fresh, copy `.env.example` to `.env` and fill in your Gemini and SerpAPI keys. Keep that file private.

```bash
python -m streamlit run app.py
```

Open the local URL printed in the terminal. Select **Create account**, choose a username and password, and start studying. Account creation does not need API keys. On Windows, activate the environment with `.venv\Scripts\Activate.ps1`.

The default Gemini model remains the original `gemini-3.5-flash` setting. Its availability to your account has not been verified. Set `GEMINI_MODEL` to a supported model from your account if needed. Sermon Study uses structured JSON output; passage commentary URLs use URL context. Restart Streamlit after changing `.env`.

## What Phase 5 adds

- **Local accounts:** sign in with a username and password. Account passwords are stored as salted PBKDF2 hashes, rather than plaintext. Signing out clears the current session's results and note widgets.
- **Automatic saving:** each successful passage, sermon, or word result is saved to your account. A failed provider request leaves the previous result intact.
- **Durable notes:** edits save to the local database when you finish editing the notes field. They survive refreshes and server restarts.
- **My Studies:** search titles and personal notes, filter by study type, or show only bookmarks.
- **Bookmarks:** bookmark a passage, sermon, or word study from its result or from My Studies.
- **History and resume:** reopen old results without another provider call. The homepage offers your three most recently updated saved studies.
- **Backup export:** download all studies, personal notes, and bookmark flags for the signed-in account as JSON. Account credential records and configured API keys are excluded.

Each source study has one saved record. Regenerating the same passage or sermon format updates that record while preserving personal notes and bookmark state. This is a history of distinct saved studies, not a version archive of every generated answer. Passage spellings such as `John 15` and `Jn 15` are separate identities. Word notes are separated by word and related passage; sermon notes by video and selected format.

## The study workflow

1. Use **Passage Study** to read Bible text and write observations, then optionally explore background around a biblical reference. Optional commentary retrieval is reported separately from generated claims.
2. Use **Sermon Study** for structured notes or an Observation → Interpretation → Application guide.
3. In a sermon's **Scripture mentions** tab, expand a reference and open it in Passage Study.
4. In a passage result's **Word study** tab, choose a word from your Bible and open it in Word Study. The related passage follows the word.
5. Write personal reflections in **My notes**. Finish editing the field to save changes.
6. Use **My Studies** or the homepage to return to saved work. Opening a saved result or following a link does not call Gemini; passage links open local WEB text.

AI-generated material may contain errors. Transcript excerpt matching checks wording, not theological correctness or the model's reference label. Word Study now checks the selected lexical ID against the STEP original-language corpus. English verse previews are displayed separately; English words are not individually aligned to original-language tags.

## Where your data lives

The default database is `~/.scripture-study/studies.sqlite3` on the computer running Streamlit. On your Mac, this is a folder in your home directory. It sits outside the downloaded project folder, so extracting a later app version does not erase your saved accounts or studies.

If you set `SCRIPTURE_DATA_DIR` in `.env`, the app uses that directory instead. Keep using the same directory when upgrading. This setting changes the data location; it does not migrate an existing database.

These accounts are local to this running app. There is no email login, password recovery, or cloud sync. A refresh or server restart may require you to sign in again; your saved data remains. If you later host the app for public use, add managed authentication and persistent hosting storage rather than treating this local account implementation as a finished public login system.

When upgrading from Phase 4, download any session-only notes before stopping the old app. Phase 5 cannot recover notes that were never saved to disk or exported. Copy your `.env` to this project, reinstall requirements, and create a local account. Accounts created in Phase 5 will remain available for future upgrades that use the same data folder.

## Back up and restore

**Readable account backup:** in My Studies, open **Backup your studies** and download JSON. This contains the current account's generated content, notes, bookmark state, and timestamps. This version exports JSON but does not yet import it through the app.

**Complete restore including accounts:** stop Streamlit with Control + C, then copy the entire `~/.scripture-study` folder somewhere safe. To restore, stop the app and put that folder back at the same location (or at the directory selected by `SCRIPTURE_DATA_DIR`). Copying while the app is stopped avoids an incomplete database copy. Your account password is still required after restoring.

Generated study Markdown downloads include personal notes, original sermon URLs, and source retrieval information when available. The notes tab also offers a personal-notes-only download.

## Understand the code

| File | Responsibility |
|---|---|
| `app.py` | Load local settings, require sign-in, register navigation, and display the shared frame |
| `accounts.py` | Registration, sign-in, and sign-out session cleanup |
| `storage.py` | SQLite tables, password verification, account-scoped reads/writes, and backup export |
| `library_actions.py` | Save generated results, bookmark studies, and reopen saved payloads |
| `study_notes.py` | Load durable notes, sync edits, and display the notes editor |
| `pages/my_studies.py` | Search, type filters, bookmarks, history, and backup UI |
| `study_links.py` | Fill the destination tool's input fields without an automatic provider call |
| `ui_common.py` | Result tabs, saved actions, generation feedback, and Markdown exports |
| `design.py`, `assets/styles.css` | Reusable presentation elements and visual styling |
| `prompts/`, `study_models.py` | AI instructions and expected sermon response structure |
| `get_summary.py`, `get_context.py` | Provider calls, structured validation, and source metadata |
| `bible_reader.py` | Reading snapshots, selected verse ranges, surrounding chapters, and chapter navigation |
| `translations.py`, `translation_ui.py` | Authorized version resolution, API.Bible/ESV retrieval, structured verse parsing, selection and attribution |
| `memorization.py`, `pages/memorize.py` | Account-scoped memory deck, deterministic practice, spaced review, and progress |
| `transcript.py`, `word_study.py` | Transcript retrieval; local lexical search, reference parsing, and concordance |
| `word_explanation.py` | Structured passage-grounded explanation and supplied-reference validation |
| `data/`, `scripts/build_word_data.py` | Bundled word index, source notices/fingerprints, and reproducible TSV transformation |
| `advanced_study.py` | Embeddings, cached retrieval, transcript answer checks, and generated study aids |
| `advanced_ui.py` | Explicit-submit advanced tool forms and source excerpts |
| `pages/search_studies.py`, `pages/topic_study.py` | Semantic search and saved topic study pages |
| `service_errors.py` | Actionable provider diagnostics with credentials and request URLs removed |

The central Phase 5 idea is separating **session state** from **durable storage**. Session state holds the currently open result and input widgets. SQLite holds account records and saved studies. My Studies loads a saved payload into session state, then navigates to its tool; it does not generate a replacement answer.

The new `embedding_cache` table stores account-scoped excerpt vectors. Its entries are tied to a saved study, content fingerprint, and embedding model. Changing the content or model invalidates a cache match. Vectors are regenerated from saved content as needed and are not included in the readable JSON backup; the full local data-folder backup includes them.

The `studies` table uses `(user_id, study_id)` as its primary key. Reads, note edits, bookmarks, and backups all include the signed-in user's ID. Saving the same identity updates generated content without resetting notes or bookmark state. Note updates occur only when the editor's text changes, avoiding a database write on every ordinary rerun.

## Validation

Run the included persistence tests from the project folder:

```bash
python -m unittest discover -s tests -v
```

Checks cover transcript excerpt verification and abstention, semantic-cache reuse, retrieval account isolation, vector dimensions, authentication, distinct password salts, account isolation, note and bookmark preservation across regeneration, search filters, and backup contents. Additional Streamlit checks passed for registration/sign-in/sign-out, automatic study saves, durable notes, bookmarks, and reopening in a fresh session without provider calls.

Live provider requests still require your keys and quota. Browser screenshot checks were not performed. The existing visual styling and linked workflow remain in place.

If generation fails, copy the text from **Error details — safe to share**. Do not send your `.env` or API keys. If a save fails, the app retains the current result in the session and displays a warning; download a copy before closing it.


Phase 6 Streamlit checks also passed with mocked provider responses for transcript Q&A, saved question history, topic saving and library display, semantic search, related-passage navigation, contextual word guidance, and no repeat provider calls on ordinary reruns. Existing Phase 5 account/persistence checks passed. Live provider availability and answer quality still need testing with your credentials.

For the next learning step, read `advanced_study.py` in this order: `chunks`, `embed`, `document_vectors`, `semantic_search`, then `ask_sermon`. The first four retrieve relevant material; the last one uses that material to generate an answer and check its quotations. This pattern is retrieval-augmented generation (RAG). The cache prevents repeat document-embedding work for matching content.

Official implementation references: [Gemini embeddings](https://ai.google.dev/gemini-api/docs/embeddings) and [Google GenAI Python SDK](https://googleapis.github.io/python-genai/).


Word Study Upgrade validation: all 14 included unit tests passed, including real bundled-corpus checks (Greek G26: 116 tokens in 106 verses for the selected STEP/NA28 index), Hebrew disambiguation, accents, invalid ranges, occurrence pagination, generated-reference rejection, absent-word blocking, and legacy-note identity. Streamlit interaction checks passed for lexical selection, verse forms, filters, explicit AI submission with mocked responses, saved explanations, notes, CSV export, reopening, and absent-word blocking. Existing account/persistence and Phase 6 tools passed regression checks. Live Gemini output quality and availability were not tested with your credentials.


Passage Reader validation: all 18 included tests passed. Streamlit interaction checks passed for offline reading, selected verses and chapter context, navigation across books/end boundaries, generation only on explicit request, chapter text supplied to the context prompt, saving before generation, notes/bookmark persistence, library resume, verse-specific word handoff, automatic local reading from incoming passage links, missing-key fallback, and invalid-reference preservation. Existing account, sermon/topic/search, and Word Study interaction checks passed. Live Gemini output and visual browser screenshots were not tested.


Versions & Clear Meanings validation: 25 included unit tests passed, covering authorized catalog resolution, ambiguous editions, safe API access failures, structured/bridged verse parsing, direct ESV text/copyright parsing, online reference-only persistence, richer meaning generation/reference checks, and all prior corpus/account tests. Streamlit checks passed with mocked provider responses for the five version options, version-specific backgrounds, version handoff, stable notes, no provider requests on ordinary reruns, automatic concise contextual meaning, and failed-request preservation. Existing reader, word study, accounts, sermon, topic and search checks passed. Live API.Bible/Crossway access and live Gemini wording remain untested because your provider credentials were not supplied.

Official integration references: [API.Bible Bibles](https://docs.api.bible/guides/bibles/), [Chapters](https://docs.api.bible/guides/chapters/), [JSON content formats](https://docs.api.bible/resources/content-output-formats/), [view tracking](https://docs.api.bible/resources/fair-use/), and [ESV text endpoint](https://api.esv.org/docs/passage-text/).


Study & Remember validation: 32 unit tests passed, including account isolation, duplicate-card progress retention, bounded review intervals, replay-safe ratings, due queues/streaks, verse bridges/range limits, deterministic recall/hints, and reference-only licensed-card exports. Streamlit workflow checks passed for all three modes, typed feedback, saved review progress, stable reruns, home progress, passage handoff, and account isolation. Reader and translation/meaning regression checks passed. Provider access was simulated; live provider credentials were not supplied. Browser screenshot verification was unavailable in this environment, so mobile styling still needs a real-device check.
