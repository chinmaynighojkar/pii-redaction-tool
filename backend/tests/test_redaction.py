"""Redaction logic. No server and no inference: the functions take plain dicts."""

from redactor import merge_adjacent, redact_text


def ent(label, start, end):
    return {"entity_group": label, "start": start, "end": end}


class TestMergeAdjacent:
    def test_joins_touching_spans_with_the_same_label(self):
        text = "Contact Siobhan Ni Fhaolain today"
        spans = merge_adjacent(text, [ent("person", 7, 24), ent("person", 24, 27)])
        assert len(spans) == 1
        assert text[spans[0]["start"] : spans[0]["end"]] == "Siobhan Ni Fhaolain"

    def test_keeps_spans_with_different_labels_apart(self):
        text = "Aoife aoife@example.ie"
        spans = merge_adjacent(text, [ent("person", 0, 5), ent("email", 5, 22)])
        assert len(spans) == 2

    def test_keeps_spans_that_do_not_touch_apart(self):
        text = "Aoife and Niamh"
        spans = merge_adjacent(text, [ent("person", 0, 5), ent("person", 10, 15)])
        assert len(spans) == 2

    def test_trims_whitespace_the_detector_swallowed(self):
        text = "Contact Aoife now"
        spans = merge_adjacent(text, [ent("person", 7, 13)])
        assert text[spans[0]["start"] : spans[0]["end"]] == "Aoife"

    def test_drops_spans_that_are_only_whitespace(self):
        assert merge_adjacent("a   b", [ent("person", 1, 4)]) == []


class TestRedactText:
    def test_one_placeholder_per_entity_not_per_fragment(self):
        """Regression: touching sub-word spans produced a placeholder each."""
        text = "Contact Siobhan Ni Fhaolain today"
        redacted, _ = redact_text(text, [ent("person", 7, 24), ent("person", 24, 27)])
        assert redacted.count("[person REDACTED]") == 1
        assert redacted == "Contact [person REDACTED] today"

    def test_keeps_the_space_before_a_placeholder(self):
        text = "Contact Aoife now"
        redacted, _ = redact_text(text, [ent("person", 7, 13)])
        assert "Contact [person REDACTED]" in redacted

    def test_offsets_stay_correct_across_several_entities(self):
        """Replacing left to right would shift later spans out of position."""
        text = "Aoife emailed Niamh about Cork"
        redacted, _ = redact_text(
            text, [ent("person", 0, 5), ent("person", 14, 19), ent("place", 26, 30)]
        )
        assert redacted == "[person REDACTED] emailed [person REDACTED] about [place REDACTED]"

    def test_summary_never_carries_the_original_value(self):
        """The whole point of the tool: responses must not contain the PII."""
        text = "Contact Aoife at aoife@example.ie"
        _, summary = redact_text(text, [ent("person", 8, 13), ent("email", 17, 33)])
        for item in summary:
            assert set(item) == {"label", "start", "end"}
            assert "Aoife" not in str(item)
            assert "aoife@example.ie" not in str(item)

    def test_no_entities_leaves_text_untouched(self):
        assert redact_text("nothing here", []) == ("nothing here", [])
