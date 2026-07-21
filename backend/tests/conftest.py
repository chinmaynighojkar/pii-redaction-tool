import os

import pytest
import requests

BASE_URL = os.getenv("PII_TEST_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def api():
    """Base URL of a running backend, or skip the test.

    The API tests need the model loaded, which is too slow to spin up per run,
    so they check for a server already listening and skip if there is not one.
    Start it with `uvicorn main:app --port 8000` before running these.
    """
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=3).json()
    except requests.exceptions.RequestException:
        pytest.skip(f"no backend listening on {BASE_URL}")

    if not health.get("model_loaded"):
        pytest.skip("backend is up but the model failed to load")

    return BASE_URL
