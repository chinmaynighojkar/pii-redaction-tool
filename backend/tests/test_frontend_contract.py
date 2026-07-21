"""The frontend hardcodes assumptions about backend output. Check they hold.

The highlight regex matched uppercase labels only, while the model emits
lowercase ones like private_person, so nothing was ever highlighted and no
test would have caught it from the Python side alone.
"""

import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"
VIEWER = FRONTEND / "components" / "RedactedViewer.jsx"
APP = FRONTEND / "App.jsx"

REAL_LABELS = ["private_person", "private_email", "private_phone", "private_address"]
FAKE_LABELS = ["[NAME REDACTED]", "[EMAIL REDACTED]", "[EIRCODE REDACTED]"]


def highlight_pattern():
    source = VIEWER.read_text(encoding="utf-8")
    return re.compile(re.search(r"escaped\.replace\(\s*/(.+?)/g", source, re.S).group(1))


def test_highlight_regex_matches_the_labels_the_model_emits():
    pattern = highlight_pattern()
    for label in REAL_LABELS:
        assert pattern.search(f"[{label} REDACTED]"), f"{label} would not be highlighted"


def test_ui_copy_does_not_advertise_labels_that_do_not_exist():
    copy = APP.read_text(encoding="utf-8")
    assert not [label for label in FAKE_LABELS if label in copy]
