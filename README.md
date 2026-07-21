# PII Redaction Tool (Personally Identifiable Information)

A document anonymisation service that automatically detects and masks personally identifiable information using a purpose-built token classification model. Built with FastAPI and React.

---

## The Story Behind This Project

My day job involves working with documents at volume. Not reading them casually but building with them, structuring them, and thinking carefully about what information they contain and how that information moves between people and systems. After spending enough time doing that kind of work, you start noticing things that are easy to miss when you interact with documents one at a time.

One pattern kept coming up. Almost every professional document contains information that could identify a real person. Names, contact details, location data, reference numbers. And in most workflows, someone has to go through and strip that information out before the document moves to the next stage. That cleaning step is almost always done by hand. One person, one document, scanning for fields that should not be there. At low volume it is manageable. At any kind of scale it becomes a bottleneck and a liability waiting to happen.

I was thinking about that gap when I also started paying closer attention to where I live and work. Ireland is not a typical European country when it comes to data privacy. It hosts the EU headquarters of some of the largest technology companies in the world, which makes it one of the most closely watched jurisdictions for GDPR enforcement on the continent. The Data Protection Commission here handles cases that set precedent across the EU. Working in data in Ireland means GDPR is not a compliance checkbox you fill in once a year. It is a live operational consideration that shapes how documents are handled, how records are shared, and how work gets reviewed before it moves between teams.

Both of those things together made the problem very clear to me. Manual redaction does not scale and the regulatory consequences of getting it wrong are serious. So I built something to fix the first part of that. A tool that handles the automated first pass so that human attention goes only where it is actually needed.

So here it is. Upload a document and get back a redacted version with every detected entity masked and labelled within seconds.

---

## Why I Chose This Model

When I started working out the technical approach, I noticed something that bothered me. Most developers reaching for a document redaction solution default to general purpose named entity recognition models. Models like spaCy or standard BERT NER variants are well documented, widely used, and easy to drop into a pipeline. They label people, places, and organisations.

But labelling people, places, and organisations is not the same as identifying what is actually sensitive inside a document. A general NER model will catch a person's name in many cases. It is far less reliable on email addresses, phone numbers, identification numbers, and the kinds of contact details that make a document personally identifiable in practice. Those are precisely the fields that matter most in a GDPR context, and they are exactly what general NER models were not designed to prioritise.

`openai/privacy-filter` on HuggingFace is a 1B parameter token classification model trained specifically for privacy-relevant entity detection. It was built to find what is sensitive, not just what is a named entity. The difference in recall on fields like email addresses, phone numbers, and address components is meaningful, and meaningful recall is what matters when the cost of a miss is a reportable data breach.

Most developers overlook it because it is far less visible than the standard NER options. Choosing it deliberately and being able to explain why is itself a demonstration of how model selection should work in practice. Start from the problem, not from the most familiar tool.

---

## What It Does

Upload any document and the tool will:

- Extract text from PDFs, CSVs, or plain text files
- Run it through `openai/privacy-filter`, detecting PII at the character span level
- Replace each detected entity with a labelled placeholder such as `[private_person REDACTED]` or `[private_email REDACTED]`
- Display the redacted output with all masked spans highlighted in amber
- Show a summary panel listing every entity type found and how many instances were detected
- Let you download the clean redacted file immediately

---

## Demo

```
Input:
  Please contact Aoife Murphy at aoife.murphy@example.ie or call her on +353 87 123 4567.
  Her office is at 14 Fitzgerald Road, Cork, T12 XY34.

Output:
  Please contact [private_person REDACTED] at [private_email REDACTED] or call her on
  [private_phone REDACTED]. Her office is at [private_address REDACTED].
```

The placeholder labels come from the model's own entity classes rather than a
mapping of my own, so they read as `private_person` instead of `NAME`. Note that
the town and Eircode are absorbed into the single `private_address` span, which
is the model's judgement rather than four separate detections.

---

## How It Works

### The Model

`openai/privacy-filter` runs through the HuggingFace `transformers` pipeline with `aggregation_strategy="simple"`. That groups consecutive tokens carrying the same predicted label into a span with a start index, an end index, and a label.

I read that as a guarantee of one span per entity. It is not, and I did not find out until I properly looked at a redacted sentence:

```
Contact[private_person REDACTED][private_person REDACTED] at[private_email REDACTED]...
```

The model works on tokens, so a name it has not seen before gets broken into pieces. "Fhaolain" came back as "Fhaol" and "ain" in two spans that touch each other, and each of those spans had quietly taken the space in front of it as well, which is why the text runs straight into the placeholder. The redaction engine below cleans up both problems.

### The Redaction Engine

Two things happen before any text gets replaced.

First, `merge_adjacent()` walks the spans in order and joins any two that share a label and touch exactly, which puts the pieces of a split name back together. It then trims whitespace off the edges of whatever it produced, so the space in front of each placeholder survives. Skip this step and you get a placeholder per fragment instead of per entity.

```python
if merged and merged[-1]["label"] == label and merged[-1]["end"] == start:
    merged[-1]["end"] = end
```

Second, the merged spans get replaced in reverse order of start index. Going left to right would shift the character offsets of everything after each substitution and send later replacements to the wrong place. Working backwards means every replacement lands on indices that have not moved yet, however many entities a document turns out to have.

Each span becomes `[LABEL REDACTED]`, where the label is whatever class the model assigned. Alongside the redacted text there is a summary listing the type and position of everything that was masked, so a reviewer can check what was caught instead of trusting a silently altered document. The summary leaves the original values out on purpose, for the reason in the security section.

### The Stack

| Layer | Technology |
|---|---|
| Model | openai/privacy-filter (HuggingFace Transformers) |
| Backend | Python, FastAPI, Uvicorn |
| File parsing | pdfplumber for PDF, pandas for CSV |
| Frontend | React 18, Vite |
| Styling | Plain CSS |

---

## Project Structure

```
pii-redaction-tool/
├── backend/
│   ├── inputs/              # Uploads land here, deleted after extraction
│   ├── outputs/             # Redacted outputs saved here, not cleaned up
│   ├── main.py              # FastAPI app and REST endpoints
│   ├── graphql_api.py       # GraphQL schema and router
│   ├── redactor.py          # Model loading, span merging, redaction
│   ├── preprocessor.py      # File parsing by type
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── UploadZone.jsx
│   │   │   ├── RedactedViewer.jsx
│   │   │   └── EntityBadge.jsx
│   │   └── index.css
│   └── vite.config.js
├── sample_inputs/
│   ├── sample.txt
│   └── sample.csv
└── README.md
```

---

## Setup and Installation

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The first run downloads the model weights from HuggingFace, roughly 2GB. After the initial download the model is cached locally and loads in a few seconds on every run after that.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The React app runs at `http://localhost:5173` and proxies all API calls to the FastAPI backend at port 8000.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/redact` | Upload a file, returns redacted text and entity summary |
| GET | `/health` | Confirms the API is running and the model is loaded |
| GET | `/download/{filename}` | Downloads a redacted output file by name |
| POST | `/graphql` | GraphQL endpoint, see below |

### GraphQL

The REST route above is file-oriented: you upload a PDF, CSV, or TXT and get a
redacted file back. The GraphQL endpoint covers the other case, redacting a
string in place, and calls the same `detect_pii` and `redact_text` functions in
`redactor.py` rather than reimplementing anything.

```graphql
mutation {
  redactText(text: "Contact Aoife at aoife@example.ie") {
    redactedText
    entities { type start end redactedText }
  }
}
```

Redaction is a mutation even though no server state changes. The argument
carries un-redacted PII, and GraphQL tooling will cache, replay, and put queries
in URLs, but never does any of that to a mutation. For the same reason
`allow_queries_via_get` is off, so nothing in this schema can reach a server log
by way of a query string.

Set `PII_DEBUG=1` to serve the GraphiQL playground at `/graphql` and enable
introspection. Both are off by default, so a deployed instance does not hand out
its own schema map.

`Entity.redactedText` is the placeholder that replaced the span, never the value
that was removed, for the reason described under Security Hardening below.

### Why GraphQL, Honestly

GraphQL is worth the trouble when a lot of different clients need different
slices of related data. One request can pull a whole tree instead of chaining
calls, a client can ask only for the fields it will actually render, and the API
can grow without anyone standing up a `/v2`. Because the schema is typed and
introspectable, tooling can generate client types from it and GraphiQL can
autocomplete against a server that is actually running.

Not much of that applies here. There is one resource and one operation, nothing
to fetch as a tree, and no N+1 problem to solve. For the file upload path that
most people use, REST is simply the better fit. It costs something, too: every
response comes back as HTTP 200 with any errors buried in the body, and HTTP
caching stops helping you.

What I did get out of it is narrower. The contract is checked before a resolver
runs, so a client asking for a field that does not exist fails straight away
rather than quietly reading `null` in production months later. A caller that only
wants `redactedText` is not handed the entity list, which counts for a bit more
than usual when the payload concerns sensitive documents. And GraphiQL builds its
own documentation from the live schema, so that part cannot drift.

REST is still the main way in. GraphQL is a second door onto the same redaction
code, and both call `detect_pii` and `redact_text`. That last part is the bit I
would not compromise on.

---

## Where This Is Useful

This tool is applicable anywhere documents containing personal data need to be cleaned before they are shared, stored, or processed downstream.

In financial services and fund administration, client onboarding packs, KYC documents, and counterparty reports need to be handled carefully before internal distribution. In legal and compliance work, case files and correspondence often contain identifiers that should be stripped before a document reaches a wider team. In AI training data pipelines, corpora built from realistic document scenarios need a cleaning pass to ensure that realistic-looking personal identifiers do not introduce data quality or privacy issues into the resulting model.

Ireland's position as a GDPR enforcement hub makes this kind of tooling relevant across virtually every sector that handles documents at volume.

---

## Limitations and Honest Caveats

This tool is a first pass detection layer, not a legally certified redaction system.

It also only handles short documents. Text is capped at 4,000 characters per request, which is roughly a page and a half. That is a limit of running a 1B parameter model on CPU without chunking rather than anything fundamental, but it is the honest state of it today, and the Known Gaps section below explains what happens if you lift the cap.

The model performs well on common entity types including names, emails, phone numbers, and addresses. Recall is lower on domain-specific identifiers such as Irish PPS numbers, internal client reference codes, or proprietary account formats used by specific institutions.

False negatives (missed PII) are more dangerous than false positives (over-redaction) in a compliance context. In a production deployment, a human review step should follow the automated pass for high-stakes documents.

The tool is designed to be auditable. Every entity that was detected and masked is listed in the summary panel so the reviewer can verify what was caught, rather than receiving a document where changes were made silently.

---

## What I Learned Building This

The most useful thing this project clarified for me was how the precision versus recall tradeoff changes completely depending on context. In an academic classification task, chasing a higher F1 score is the goal. When the task is redacting a document before it enters a regulated pipeline, the asymmetry between a false negative and a false positive becomes very concrete. Missing a name that should have been masked is a different category of problem from masking something that did not need to be masked. That shift in consequence changes how you think about model selection, threshold tuning, and what good enough actually means in practice.

Implementing the reverse sort replacement logic was a small detail that required thinking carefully before writing any code. It is the kind of thing that works perfectly in testing on short strings and silently breaks on longer documents with many entities if you get the ordering wrong.

The bug I actually shipped was the one I never thought about. The reverse sort was right from the start because I sat down and worked through it before writing anything. The fragmented spans were wrong the entire time because I assumed the library was handling that for me and never looked at a full sentence of output, only at whether a response came back. Months later I looked, and there it was.

---

## Security Hardening

After the initial build, a systematic review identified vulnerabilities and reliability gaps across the backend and frontend. The following changes were made.

### Critical fixes

**Path traversal on upload and download** — Both the `/redact` endpoint and the `/download/{filename}` endpoint accepted filenames directly from user input without stripping directory components. A crafted filename like `../../etc/passwd` could read or overwrite files outside the intended upload and output directories. Both paths now use `Path(filename).name` to sanitise the name before constructing the final file path.

**CORS wildcard** — The middleware was configured with `allow_origins=["*"]`, which allows any origin to make cross-site requests to the API. The allowed origin is now restricted to `http://localhost:5173`, `allow_credentials` is set to `False`, and only `GET` and `POST` methods are permitted.

**PII values in API response** — The entity summary returned by `/redact` included an `original_value` field containing the exact text that was detected and masked. This meant the API response itself contained the PII the tool was supposed to remove, which defeats the purpose for any workflow that logs or stores API responses. The summary now returns only the entity type and character span positions.

**No MIME type validation** — The upload endpoint accepted any `Content-Type`. A file with a valid extension but a mismatched or malicious payload would be passed to the extraction pipeline. The endpoint now validates both the file extension and the `Content-Type` header against an explicit allowlist before any processing begins.

### Important fixes

**No file size limit** — There was no upper bound on upload size, making it trivial to exhaust server memory with a large file. Uploads are now capped at 10 MB. The backend enforces this by reading up to 10 MB plus one byte and rejecting anything that exceeds the limit before writing to disk.

**Uploaded file not cleaned up** — Input files written to `inputs/` were not deleted after the text extraction step. The file is now removed immediately after extraction inside a `finally` block, so cleanup happens even when processing fails partway through.

**Blocking inference on the async thread** — `detect_pii()` calls the transformer pipeline synchronously. Running it directly inside an `async` route handler stalls the event loop for the full duration of model inference, preventing the server from handling any other request in the meantime. The call is now offloaded to a thread pool worker with `asyncio.to_thread()`.

**`print()` in the model loader** — The model loading fallback used `print()` to surface failures. This bypasses any structured logging or log aggregation. The statement is now a `logging.warning()` call through a named module logger.

### Nits

**Client-side size check** — `UploadZone.jsx` now validates file size immediately on file selection and shows a clear error before the upload request is sent, rather than waiting for the backend to return a 413.

**Pinned dependency ranges** — `requirements.txt` now specifies compatible upper-bound version ranges for all dependencies rather than leaving them unpinned, which prevents silent breakage when a major version of a dependency ships.

**`dangerouslySetInnerHTML` comment** — `RedactedViewer.jsx` now includes an inline comment explaining that the usage is safe because `highlightRedactions()` HTML-escapes all document text before substituting backend-generated tokens with `<mark>` elements.

**Validation error message** — The `else` branch in `preprocessor.py`'s `extract_text()` now raises a consistently formatted error string rather than a dead code path with a mismatched message.

### Known gaps

These are real and none of them are fixed. I would rather write them down than leave someone to find them.

**Redacted outputs are never deleted** — Uploads are removed from `inputs/` immediately after text extraction, but the redacted file written to `outputs/` stays on disk indefinitely. There is no retention policy and no cleanup job, so a long-running instance accumulates every document it has ever processed. Redacted output is lower risk than the original, but it is not zero risk, since spans the model missed remain in plain text.

**`/download/{filename}` has no authentication and predictable names** — The route serves any file in `outputs/` to anyone who can reach it, and output names are derived from the uploaded filename as `redacted_{stem}.txt`. Two people uploading `report.pdf` overwrite each other's output, and either can retrieve the other's by guessing a common filename. Path traversal is handled, but authorisation is not, because there is no concept of a user. Fixing this properly means per-request identifiers rather than name-derived paths, plus ownership checks.

**No authentication or rate limiting anywhere** — Every endpoint is open. Model inference is expensive, so an unauthenticated caller can tie up the server with repeated requests. The GraphQL text argument is length capped and uploads are size capped, which bounds a single request but not the number of them.

**The model revision is not pinned** — `pipeline()` is called with a model name and no `revision` argument, so it resolves to whatever the HuggingFace repository currently points at. For a tool whose output is a security control, the detector changing underneath a deployment is a genuine supply chain concern. It should be pinned to a commit hash.

**No automated tests** — Every fix above was verified by hand. Nothing currently prevents a future change from silently reintroducing one of them, and that is the most useful next piece of work on this project.

**Documents have to be small, and that is the real limitation** — Inference cost climbs much faster than input length. Measured on this model on CPU, 4,000 characters redacts in about twelve seconds, 10,000 characters did not finish in ten minutes, and 168,000 characters asked the allocator for 12.8 GB and raised a `RuntimeError`. The 10 MB upload limit does nothing to bound any of that, so a 200 KB text file was enough to take the process down. Both entry points now cap extracted text at `MAX_TEXT_CHARS` and return 413 rather than dying, but a cap is containment, not a fix. Handling a document of realistic length means chunking the text and running inference over windows, which is the next real piece of engineering here.

---

## Contact

Built by Chinmay Nighojkar

[LinkedIn](https://www.linkedin.com/in/chinmaynighojkar/) | [GitHub](https://github.com/chinmaynighojkar/)
