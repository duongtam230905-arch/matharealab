"""Kiểm thử API (cần cài fastapi + httpx)."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402

client = TestClient(app)


def test_calculate_ok():
    r = client.post("/api/calculate", json={"f1": "x^2", "f2": "0", "a": "0", "b": "3"})
    assert r.status_code == 200 and r.json()["area"] == "9"


def test_calculate_error_shape():
    r = client.post("/api/calculate", json={"f1": "x**2+++"})
    assert r.status_code == 400
    body = r.json()
    assert body["ok"] is False and body["error"]["code"] == "parse" and "Không thể đọc biểu thức" in body["error"]["message"]


def test_intersections_and_examples():
    assert client.post("/api/intersections", json={"f1": "x^2", "f2": "x+2"}).json()["suggested"] == {"a": "-1", "b": "2"}
    assert len(client.get("/api/examples").json()["examples"]) >= 8
    assert client.get("/api/health").json()["status"] == "ok"


def test_index_served():
    assert client.get("/").status_code == 200


def test_v2_endpoints():
    s = client.post("/api/sample", json={"f1": "x^2", "f2": "0", "x0": -50, "x1": 50, "y0": -5, "y1": 100, "n": 200})
    assert s.status_code == 200 and len(s.json()["x"]) == 200
    p = client.post("/api/parse", json={"text": "sin^2 x", "kind": "fn"})
    assert p.status_code == 200 and "sin" in p.json()["latex"]
    assert client.post("/api/parse", json={"text": "x^^2+"}).status_code == 400
    g = client.get("/api/guide").json()
    assert g["ok"] and len(g["groups"]) >= 5
