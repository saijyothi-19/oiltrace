import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure both /backend and monorepo root / are in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
root_dir = os.path.abspath(os.path.join(backend_dir, ".."))

for p in (backend_dir, root_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.main import app

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
