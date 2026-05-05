import os
import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from preprocessor import extract_text
from redactor import MODEL_LOADED, detect_pii, redact_text

INPUTS_DIR = Path(__file__).parent / "inputs"
OUTPUTS_DIR = Path(__file__).parent / "outputs"
INPUTS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

SUPPORTED_TYPES = {"pdf", "csv", "txt"}

app = FastAPI(title="PII Redaction Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": MODEL_LOADED}


@app.post("/redact")
async def redact(file: UploadFile = File(...)):
    if not MODEL_LOADED:
        raise HTTPException(status_code=503, detail="PII model failed to load on startup.")

    suffix = Path(file.filename).suffix.lstrip(".").lower()
    if suffix not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '.{suffix}'. Accepted: {', '.join(SUPPORTED_TYPES)}.",
        )

    input_path = INPUTS_DIR / file.filename
    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        text = extract_text(str(input_path), suffix)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    entities = detect_pii(text)
    redacted, summary = redact_text(text, entities)

    output_filename = f"redacted_{Path(file.filename).stem}.txt"
    output_path = OUTPUTS_DIR / output_filename
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(redacted)

    return {
        "redacted_text": redacted,
        "entity_summary": summary,
        "entity_count": len(entities),
        "file_name": output_filename,
    }


@app.get("/download/{filename}")
def download(filename: str):
    file_path = OUTPUTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(path=str(file_path), filename=filename, media_type="text/plain")
