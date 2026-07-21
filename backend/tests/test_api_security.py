"""The security properties the README claims. Needs a running backend."""

import io

import requests

from redactor import MAX_TEXT_CHARS

PII = "Contact Aoife Murphy at aoife.murphy@example.ie"
SECRETS = ("Aoife", "aoife.murphy@example.ie")

REDACT_MUTATION = (
    "mutation($t:String!){ redactText(text:$t)"
    "{ redactedText entities{type start end redactedText} } }"
)


def upload(api, name, body, mime):
    return requests.post(f"{api}/redact", files={"file": (name, body, mime)}, timeout=120)


class TestUploadValidation:
    def test_rejects_unsupported_extension(self, api):
        assert upload(api, "evil.exe", b"MZ\x90", "application/x-msdownload").status_code == 422

    def test_rejects_mismatched_content_type(self, api):
        assert upload(api, "ok.txt", b"hello", "application/x-msdownload").status_code == 422

    def test_rejects_files_over_ten_megabytes(self, api):
        big = io.BytesIO(b"a" * (10 * 1024 * 1024 + 100))
        assert upload(api, "big.txt", big, "text/plain").status_code == 413


class TestPathTraversal:
    def test_download_cannot_escape_the_outputs_directory(self, api):
        r = requests.get(f"{api}/download/..%2F..%2Fmain.py", timeout=10)
        assert r.status_code == 404
        assert "import" not in r.text


class TestTextLengthCap:
    """A 10MB file is far more text than the model can take.

    168k characters previously asked the allocator for 12.8GB and raised, so
    both entry points cap the text itself rather than trusting the file limit.
    """

    def test_rest_rejects_text_over_the_cap(self, api):
        payload = ("word " * (MAX_TEXT_CHARS // 2)).encode()
        r = upload(api, "long.txt", payload, "text/plain")
        assert r.status_code == 413

    def test_graphql_rejects_text_over_the_cap(self, api):
        r = requests.post(
            f"{api}/graphql",
            json={"query": REDACT_MUTATION, "variables": {"t": "x" * (MAX_TEXT_CHARS + 1)}},
            timeout=30,
        )
        assert "Text too long" in r.text

    def test_text_at_the_cap_is_accepted(self, api):
        r = requests.post(
            f"{api}/graphql",
            json={"query": REDACT_MUTATION, "variables": {"t": "a" * MAX_TEXT_CHARS}},
            timeout=300,
        )
        assert "Text too long" not in r.text


class TestNoPiiInResponses:
    """An API response that echoes the input defeats the point of the tool."""

    def test_rest_response_has_no_raw_pii(self, api):
        r = upload(api, "t.txt", PII.encode(), "text/plain")
        assert r.status_code == 200
        assert not [s for s in SECRETS if s in r.text]

    def test_graphql_response_has_no_raw_pii(self, api):
        r = requests.post(
            f"{api}/graphql",
            json={"query": REDACT_MUTATION, "variables": {"t": PII}},
            timeout=120,
        )
        assert r.status_code == 200
        assert not [s for s in SECRETS if s in r.text]


class TestGraphqlTransport:
    def test_queries_cannot_travel_in_a_url(self, api):
        """PII in a query string would end up in access logs and history."""
        r = requests.get(f"{api}/graphql?query=%7BmodelLoaded%7D", timeout=10)
        assert r.status_code == 400
