from __future__ import annotations

import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def auth_headers(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_empty_database_is_initialized(client: TestClient):
    from tests.conftest import TEST_DIR

    database = TEST_DIR / "test.db"
    assert database.exists()
    with sqlite3.connect(database) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"users", "reviews", "clauses", "risk_findings", "compliance_findings", "suggestions"} <= tables


def test_login_rejects_wrong_password(client: TestClient):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


def test_upload_requires_authentication(client: TestClient):
    response = client.post(
        "/api/v1/review/upload",
        files={"file": ("contract.txt", b"contract", "text/plain")},
    )
    assert response.status_code == 401


def test_upload_review_and_download_pdf(client: TestClient, auth_headers: dict[str, str]):
    content = (
        "第一条 服务内容\n乙方为甲方开发软件。\n"
        "第二条 违约责任\n乙方违约需支付三倍赔偿。\n"
        "第三条 争议解决\n双方提交法院解决。\n"
    ).encode("utf-8")
    response = client.post(
        "/api/v1/review/upload",
        headers=auth_headers,
        files={"file": ("contract.txt", content, "text/plain")},
    )
    assert response.status_code == 200, response.text
    review_id = response.json()["review_id"]

    detail = None
    for _ in range(40):
        time.sleep(0.25)
        detail_response = client.get(f"/api/v1/review/{review_id}", headers=auth_headers)
        assert detail_response.status_code == 200, detail_response.text
        detail = detail_response.json()
        if detail["status"] in {"completed", "failed"}:
            break

    assert detail is not None
    assert detail["status"] == "completed", detail
    assert detail["clauses"]
    assert detail["suggestions"]
    assert detail["step_log"]

    report = client.get(f"/api/v1/review/{review_id}/report", headers=auth_headers)
    assert report.status_code == 200
    assert report.headers["content-type"].startswith("application/pdf")
    assert report.content.startswith(b"%PDF")


def test_report_requires_authentication(client: TestClient):
    response = client.get("/api/v1/review/missing/report")
    assert response.status_code == 401
