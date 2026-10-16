"""Prueba real contra los tres servicios iniciados con Compose."""
import os

import httpx
import pytest

BASE_URL = os.environ.get("TEST_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="Requiere Compose y TEST_BASE_URL")


def test_real_crud_and_persistence():
    with httpx.Client(base_url=BASE_URL, timeout=15) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.post("/tasks", json={"title": "Prueba de integración"})
        assert response.status_code == 201, response.text
        task = response.json()
        task_id = task["id"]
        try:
            assert task["completed"] is False
            assert client.get(f"/tasks/{task_id}").json() == task
            assert any(item["id"] == task_id for item in client.get("/tasks").json())
            response = client.patch(f"/tasks/{task_id}", json={"completed": True})
            assert response.status_code == 200
            assert response.json()["completed"] is True
            assert client.get(f"/tasks/{task_id}").json()["completed"] is True
        finally:
            assert client.delete(f"/tasks/{task_id}").status_code == 204
        assert client.get(f"/tasks/{task_id}").status_code == 404
