# PII Redaction Tool

A production-ready local application for detecting and masking Personally Identifiable Information (PII) in documents. Built for compliance teams, legal professionals, and data engineers who need to anonymise sensitive documents as part of due diligence workflows, GDPR Article 25 (data minimisation by design), or pre-sharing data review. The tool processes PDF, CSV, and plain-text files entirely on your machine — no data is transmitted to any external service.

---

## Backend Setup

```bash
cd pii-redaction-tool/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The first run downloads the `openai/privacy-filter` model weights from HuggingFace (~500 MB). Subsequent starts are instant.

---

## Frontend Setup

```bash
cd pii-redaction-tool/frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## How the Model Works

The tool uses [`openai/privacy-filter`](https://huggingface.co/openai/privacy-filter), a token-classification model fine-tuned to recognise PII entity spans in free text. The HuggingFace `pipeline` is initialised with `aggregation_strategy="simple"`, which merges consecutive sub-word tokens that share the same entity label into a single span — preventing fragmented detections across word-pieces. Each span is characterised by its `entity_group` (e.g. `NAME`, `EMAIL`, `PHONE`), `start` and `end` character offsets, and a confidence `score`. The redaction step sorts spans in reverse order of their start offset before substituting them, ensuring earlier replacements do not shift the character indices used by later ones.

---

## Known Limitations

- **Model accuracy**: `openai/privacy-filter` may miss uncommon name formats, non-English PII, or highly domain-specific identifiers (e.g. medical record numbers). Always perform a human review of redacted output before sharing.
- **Long documents**: Very large files are passed to the model as a single string. Texts exceeding the model's context window (~512 tokens) may be truncated by the tokeniser, causing PII near the end of very long documents to go undetected.
- **Scanned PDFs**: `pdfplumber` extracts digital text only. PDFs that consist of scanned images require an OCR pre-processing step (e.g. Tesseract) before this tool can process them.
- **CSV structure**: The CSV preprocessor flattens all cells into a plain-text representation. Column order and row boundaries are preserved as labels but the output file is plain text, not a redacted CSV.
- **No re-identification guarantee**: Redaction removes detected spans; it does not provide a mathematical privacy guarantee (e.g. k-anonymity or differential privacy).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| API framework | FastAPI + Uvicorn |
| NLP / PII detection | HuggingFace Transformers |
| PII model | `openai/privacy-filter` |
| PDF extraction | pdfplumber |
| CSV handling | pandas |
| Frontend framework | React 18 |
| Frontend build tool | Vite 5 |
