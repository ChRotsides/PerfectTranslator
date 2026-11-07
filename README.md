# PerfectTranslator

A small desktop app that translates plain-text files between languages with OpenAI chat models. Pick a folder, pick a
`.txt` file, and the app detects the source language, splits long documents into chunks that fit the model's context,
translates the chunks in parallel and writes the result back as UTF-8.

![Demo](translatorDemo2.gif)

## Features

- Browse a folder, preview a `.txt` file and see its detected language with a confidence score.
- Translate into any of the ~100 target languages in the drop-down.
- Long files are split into chunks (line, then sentence, then word boundaries) and translated in parallel, with the
  chunks reassembled in their original order.
- Transient API errors (rate limits, timeouts, 5xx) are retried with exponential backoff.
- Optional review pass: a second request per chunk that checks and corrects the draft (roughly doubles the cost).
- The translation core has no GUI dependency, so it can be used from scripts as well (see below).

## Architecture

```
  main.py ──► perfect_translator/gui.py        FreeSimpleGUI window, background threads, events only
                       │
                       ▼
              perfect_translator/core.py       chunking, prompts, detection, retry, file I/O (no GUI imports)
                       │
                       ▼
              openai SDK  ──►  chat.completions API
```

- `core.py` holds all the logic and is what the tests exercise.
- `gui.py` runs network calls in worker threads. Workers never touch widgets; they post events to the main loop with
  `window.write_event_value`, which then updates the UI.
- `languages.py` is the list of target languages shown in the GUI.

### How chunking works

`chunk_text` packs lines into chunks of at most `max_tokens` (default 1500) estimated tokens. A line that is too big is
split at sentence ends, and a sentence that is still too big is split at words (and, for a single enormous "word", by
characters). Whitespace is preserved, so joining the chunks reproduces the input exactly.

Tokens are estimated with a small dependency-free heuristic (about 4 ASCII characters per token, 1 token per 1.5
non-ASCII characters). It errs on the side of over-counting so chunks stay under the limit, which means chunks for
English text are somewhat smaller than they strictly need to be. It is an estimate, not a real tokenizer.

### How language detection works

`detect_language` sends a deterministic sample of the text (the start, middle and end, up to ~1500 characters) and asks
for a JSON object: `{"language": ..., "code": ..., "confidence": ...}` using the API's JSON mode. The reply is parsed
defensively: code fences and surrounding prose are tolerated, confidence is clamped to 0..1 and the code is
lower-cased. If the reply cannot be parsed the result is `Unknown` rather than a crash. Detection is the model's own
judgement; the confidence value is self-reported by the model, not a calibrated probability.

## Setup

Requires Python 3.10+ and an OpenAI API key.

```bash
git clone https://github.com/ChRotsides/PerfectTranslator.git
cd PerfectTranslator
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env            # Windows: copy .env.example .env
# edit .env and set OPENAI_API_KEY=...
python main.py
```

The key is read only from the environment or `.env` (which is git-ignored) and is never logged. There is no key field
in the app any more.

### Configuration

| Variable         | Required | Default       | Meaning                                                         |
| ---------------- | -------- | ------------- | --------------------------------------------------------------- |
| `OPENAI_API_KEY` | yes      | none          | Your OpenAI API key, read by the `openai` SDK.                  |
| `OPENAI_MODEL`   | no       | `gpt-4o-mini` | Chat-completions model used for detection and translation.      |

Both can be set in `.env` or exported in your shell. The code does not send a `temperature`, so models that only accept
the default value work too.

## Use as a library

```python
from perfect_translator.core import translate_file

result = translate_file("story.txt", "story.en.txt", target="English", workers=3)
print(result.source_language, result.chunk_count, result.failed_chunks)
```

`failed_chunks` lists the indices of chunks that still failed after retries; their original text is left in place in
the output instead of being dropped.

## Tests and linting

Everything is offline: the OpenAI client is replaced by a fake, so no key or network is needed.

```bash
pip install -r requirements-dev.txt
pytest
ruff check .
```

The suite covers chunking (including reassembly and Unicode), prompt construction, detection parsing for good and
malformed replies, retry/backoff behaviour, and a Unicode file round trip. The GUI is only smoke-tested (the module
imports); it is not driven automatically. CI (`.github/workflows/ci.yml`) runs ruff and pytest on Ubuntu for Python
3.10 and 3.12.

## Limitations

- **Cost.** Every chunk is one API request (two with the review pass), plus one for detection. Long documents add up;
  check your model's pricing before translating a book.
- **Long documents.** Chunks are translated independently, so there is no shared context between them. Names, terms and
  tone can drift between chunks, and nothing enforces a glossary.
- **Formatting.** Only plain UTF-8 `.txt` files are supported. Line breaks are kept and the prompt asks the model to
  preserve structure, but the model may still change spacing or punctuation. Other encodings are rejected with an
  error.
- **Quality is the model's.** There is no automatic quality check beyond the optional review pass.
- **Not covered by automated tests:** the live API round trip and the GUI event loop.

## Roadmap

- Shared glossary / running summary passed between chunks for terminology consistency.
- Real tokenizer-based chunk sizing when available, and a configurable chunk size in the UI.
- Streaming output and a cancel button.
- Support for more file types (DOCX, SRT subtitles, Markdown) while preserving structure.
- Cost estimate before translating.

## Notes on dependencies

- The GUI uses **FreeSimpleGUI**, a maintained LGPL-3.0-or-later fork of PySimpleGUI 4 with the same API. PySimpleGUI 5 is
  proprietary and licensed separately, so this project does not use it.
- `openai` (Apache-2.0) and `python-dotenv` (BSD-3-Clause) are used as normal dependencies.

## License

Free for noncommercial and research use under the [PolyForm Noncommercial License 1.0.0](LICENSE). Commercial use
requires a separate license; contact [charalambosrotsides@gmail.com](mailto:charalambosrotsides@gmail.com) or [charalambosrotsides@outlook.com](mailto:charalambosrotsides@outlook.com).

Third-party libraries keep their own licenses: FreeSimpleGUI (LGPL-3.0-or-later), the `openai` SDK (Apache-2.0) and
`python-dotenv` (BSD-3-Clause).
