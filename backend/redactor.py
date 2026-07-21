import logging

from transformers import pipeline

logger = logging.getLogger(__name__)

# Attention memory and time grow far faster than input length on CPU. Measured on
# this model: 4,000 characters redacts in about 12 seconds, 10,000 did not finish
# in ten minutes, and 168,000 asked the allocator for 12.8 GB and raised. The
# 10 MB upload limit does not bound any of that, so every entry point caps text
# here instead. Raising this needs chunked inference, not a bigger number.
MAX_TEXT_CHARS = 4_000

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
    logger.warning("PII model failed to load: %s", _e)


def detect_pii(text: str) -> list:
    if _nlp is None:
        raise RuntimeError("PII model is not loaded.")
    return _nlp(text)


def redaction_placeholder(label: str) -> str:
    return f"[{label} REDACTED]"


def merge_adjacent(text: str, entities: list) -> list:
    """Join the detector's fragments back into whole entities.

    The pipeline splits one name or address across touching spans, and those
    spans tend to swallow the space in front of them, so redacting each one
    separately produced a placeholder per fragment. Join spans that touch and
    share a label, then trim the surrounding whitespace back off.
    """
    merged = []
    for ent in sorted(entities, key=lambda e: e["start"]):
        label = ent["entity_group"]
        start = ent["start"]
        end = ent["end"]

        if merged and merged[-1]["label"] == label and merged[-1]["end"] == start:
            merged[-1]["end"] = end
            continue

        merged.append({"label": label, "start": start, "end": end})

    trimmed = []
    for span in merged:
        original = text[span["start"] : span["end"]]
        if not original.strip():
            continue
        span["start"] += len(original) - len(original.lstrip())
        span["end"] -= len(original) - len(original.rstrip())
        trimmed.append(span)

    return trimmed


def redact_text(text: str, entities: list) -> tuple:
    spans = merge_adjacent(text, entities)

    redacted = text
    seen = set()
    summary = []

    for span in reversed(spans):
        label = span["label"]
        start = span["start"]
        end = span["end"]
        original = text[start:end]

        redacted = redacted[:start] + redaction_placeholder(label) + redacted[end:]

        key = (label, original)
        if key not in seen:
            seen.add(key)
            summary.append({"label": label, "start": start, "end": end})

    return redacted, summary
