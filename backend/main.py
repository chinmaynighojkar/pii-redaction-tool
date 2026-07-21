import asyncio
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from graphql_api import graphql_router
from preprocessor import extract_text
from redactor import MODEL_LOADED, detect_pii, merge_adjacent, redact_text

INPUTS_DIR = Path(__file__).parent / "inputs"
OUTPUTS_DIR = Path(__file__).parent / "outputs"
INPUTS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

SUPPORTED_TYPES = {"pdf", "csv", "txt"}
SUPPORTED_MIME = {
    "application/pdf",
    "text/csv",
    "application/csv",
    "text/plain",
}

app = FastAPI(title="PII Redaction Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


app.include_router(graphql_router, prefix="/graphql")


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

    if file.content_type not in SUPPORTED_MIME:
        raise HTTPException(
            status_code=422,
            detail=f"Unexpected content type '{file.content_type}'. Upload a PDF, CSV, or TXT file.",
        )

    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")

    input_path = INPUTS_DIR / Path(file.filename).name
    input_path.write_bytes(data)

    try:
        text = extract_text(str(input_path), suffix)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    finally:
        input_path.unlink(missing_ok=True)

    entities = await asyncio.to_thread(detect_pii, text)
    redacted, summary = redact_text(text, entities)

    output_filename = f"redacted_{Path(file.filename).stem}.txt"
    output_path = OUTPUTS_DIR / output_filename
    output_path.write_text(redacted, encoding="utf-8")

    return {
        "redacted_text": redacted,
        "entity_summary": summary,
        # Whole entities, not the detector's sub-word fragments, so the count
        # agrees with the number of placeholders in the redacted text.
        "entity_count": len(merge_adjacent(text, entities)),
        "file_name": output_filename,
    }


@app.get("/download/{filename}")
def download(filename: str):
    safe_name = Path(filename).name
    file_path = OUTPUTS_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(path=str(file_path), filename=safe_name, media_type="text/plain")
