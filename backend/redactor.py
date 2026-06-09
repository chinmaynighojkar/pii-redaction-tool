from transformers import pipeline

try:
    _nlp = pipeline(
        "token-classification",
        model="openai/privacy-filter",
        aggregation_strategy="simple",
    )
    MODEL_LOADED = True
except Exception as _e:
    _nlp = None
    MODEL_LOADED = False
    print(f"[redactor] WARNING: model failed to load — {_e}")


def detect_pii(text: str) -> list:
    if _nlp is None:
        raise RuntimeError("PII model is not loaded.")
    return _nlp(text)


def redact_text(text: str, entities: list) -> tuple:
    sorted_entities = sorted(entities, key=lambda e: e["start"], reverse=True)

    redacted = text
    seen = set()
    summary = []

    for ent in sorted_entities:
        label = ent["entity_group"]
        start = ent["start"]
        end = ent["end"]
        original = text[start:end]

        redacted = redacted[:start] + f"[{label} REDACTED]" + redacted[end:]

        key = (label, original)
        if key not in seen:
            seen.add(key)
            summary.append({"label": label, "start": start, "end": end})

    return redacted, summary
