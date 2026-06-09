import pdfplumber
import pandas as pd


def extract_text(file_path: str, file_type: str) -> str:
    if file_type == "pdf":
        with pdfplumber.open(file_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages)

    if file_type == "csv":
        df = pd.read_csv(file_path)
        rows = []
        for _, row in df.iterrows():
            parts = [f"{col}: {val}" for col, val in row.items()]
            rows.append(", ".join(parts))
        return "\n".join(rows)

    if file_type == "txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    raise ValueError(f"Unsupported file type: '{file_type}'.")
