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
- Replace each detected entity with a labelled placeholder such as `[NAME REDACTED]` or `[EMAIL REDACTED]`
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
  Please contact [NAME REDACTED] at [EMAIL REDACTED] or call her on [PHONE REDACTED].
  Her office is at [ADDRESS REDACTED], Cork, [EIRCODE REDACTED].
```

---

## How It Works

### The Model

`openai/privacy-filter` uses the HuggingFace `transformers` pipeline with `aggregation_strategy="simple"`, which merges consecutive tokens belonging to the same entity into a single span. A full name like "Aoife Murphy" comes back as one entity with a start index, end index, and label rather than two separate word level tokens. This makes the output clean and straightforward to process downstream.

### The Redaction Engine

Once the model returns a list of entity spans, the redaction engine sorts them by start index in reverse order. This is a deliberate design decision. Replacing spans from left to right shifts the character offsets of everything that follows, causing subsequent replacements to land in the wrong position. Sorting in reverse means each replacement operates on indices that have not yet been shifted, keeping the output accurate regardless of how many entities are detected in a single document.

Each span is replaced with `[LABEL REDACTED]` where the label reflects the entity type. The original entity values and their positions are preserved in a summary object returned alongside the redacted text, so the user can see exactly what was found and masked rather than receiving a silently altered document.

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
│   ├── inputs/              # Uploaded files land here
│   ├── outputs/             # Redacted outputs saved here
│   ├── main.py              # FastAPI app and endpoints
│   ├── redactor.py          # Model loading and redaction logic
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

---

## Where This Is Useful

This tool is applicable anywhere documents containing personal data need to be cleaned before they are shared, stored, or processed downstream.

In financial services and fund administration, client onboarding packs, KYC documents, and counterparty reports need to be handled carefully before internal distribution. In legal and compliance work, case files and correspondence often contain identifiers that should be stripped before a document reaches a wider team. In AI training data pipelines, corpora built from realistic document scenarios need a cleaning pass to ensure that realistic-looking personal identifiers do not introduce data quality or privacy issues into the resulting model.

Ireland's position as a GDPR enforcement hub makes this kind of tooling relevant across virtually every sector that handles documents at volume.

---

## Limitations and Honest Caveats

This tool is a first pass detection layer, not a legally certified redaction system.

The model performs well on common entity types including names, emails, phone numbers, and addresses. Recall is lower on domain-specific identifiers such as Irish PPS numbers, internal client reference codes, or proprietary account formats used by specific institutions.

False negatives (missed PII) are more dangerous than false positives (over-redaction) in a compliance context. In a production deployment, a human review step should follow the automated pass for high-stakes documents.

The tool is designed to be auditable. Every entity that was detected and masked is listed in the summary panel so the reviewer can verify what was caught, rather than receiving a document where changes were made silently.

---

## What I Learned Building This

The most useful thing this project clarified for me was how the precision versus recall tradeoff changes completely depending on context. In an academic classification task, chasing a higher F1 score is the goal. When the task is redacting a document before it enters a regulated pipeline, the asymmetry between a false negative and a false positive becomes very concrete. Missing a name that should have been masked is a different category of problem from masking something that did not need to be masked. That shift in consequence changes how you think about model selection, threshold tuning, and what good enough actually means in practice.

Implementing the reverse sort replacement logic was a small detail that required thinking carefully before writing any code. It is the kind of thing that works perfectly in testing on short strings and silently breaks on longer documents with many entities if you get the ordering wrong.

---

## Contact

Built by Chinmay Nighojkar | Data and Analytics Professional based in Ireland

Open to data analytics, compliance analytics, and BI engineering roles in Cork and Dublin.

[LinkedIn](https://www.linkedin.com/in/chinmaynighojkar/) | [GitHub](https://github.com/chinmaynighojkar/)
