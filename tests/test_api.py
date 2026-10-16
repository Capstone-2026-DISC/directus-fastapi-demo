import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app, get_directus

TASK = {"id": 1, "title": "Estudiar", "completed": False}


@pytest.fixture
def client_factory():
    clients = []

    def factory(handler):
        upstream = httpx.Client(
            base_url="http://directus",
            transport=httpx.MockTransport(handler),
        )
        clients.append(upstream)
        app.dependency_overrides[get_directus] = lambda: upstream
        return TestClient(app)

    yield factory
    app.dependency_overrides.clear()
    for client in clients:
        client.close()


def test_crud_translates_requests(client_factory):
    calls = []

    def handler(request):
        import json
        calls.append(request)
        assert request.url.path.startswith("/items/tasks")
        if request.method == "POST":
            assert json.loads(request.content) == {
                "title": "Estudiar", "completed": False,
            }
            return httpx.Response(200, json={"data": TASK})
        if request.method == "PATCH":
            assert request.url.path == "/items/tasks/1"
            assert json.loads(request.content) == {"completed": True}
            return httpx.Response(200, json={"data": {**TASK, "completed": True}})
        if request.method == "DELETE":
            assert request.url.path == "/items/tasks/1"
            return httpx.Response(204)
        if "filter[id][_eq]" in request.url.params:
            assert request.url.params["filter[id][_eq]"] == "1"
        else:
            assert request.url.params["sort"] == "id"
            assert request.url.params["limit"] == "2"
            assert request.url.params["offset"] == "3"
        return httpx.Response(200, json={"data": [TASK]})

    client = client_factory(handler)
    assert client.post("/tasks", json={"title": "Estudiar"}).status_code == 201
    assert client.get("/tasks?limit=2&offset=3").json() == [TASK]
    assert client.get("/tasks/1").json() == TASK
    assert client.patch("/tasks/1", json={"completed": True}).json()["completed"]
    assert client.delete("/tasks/1").status_code == 204
    assert [r.method for r in calls] == [
        "POST", "GET", "GET", "GET", "PATCH", "GET", "DELETE",
    ]


@pytest.mark.parametrize("method,path,payload", [
    ("POST", "/tasks", {"title": "   "}),
    ("POST", "/tasks", {"title": "x" * 201}),
    ("POST", "/tasks", {"title": "x", "extra": 1}),
    ("PATCH", "/tasks/1", {}),
    ("PATCH", "/tasks/1", {"title": None}),
    ("PATCH", "/tasks/1", {"completed": None}),
    ("GET", "/tasks/0", None),
    ("GET", "/tasks?limit=101", None),
    ("GET", "/tasks?offset=-1", None),
])
def test_validation(client_factory, method, path, payload):
    def handler(request):
        pytest.fail("La entrada inválida no debe llegar a Directus.")
    client = client_factory(handler)
    assert client.request(method, path, json=payload).status_code == 422


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
def test_missing_task(client_factory, method):
    client = client_factory(lambda r: httpx.Response(200, json={"data": []}))
    kwargs = {"json": {"completed": True}} if method == "PATCH" else {}
    assert client.request(method, "/tasks/999", **kwargs).status_code == 404


@pytest.mark.parametrize("upstream", [401, 403, 500, 503])
def test_upstream_errors_are_sanitized(client_factory, upstream):
    client = client_factory(
        lambda r: httpx.Response(upstream, json={"errors": [{"message": "privado"}]})
    )
    response = client.get("/tasks")
    assert response.status_code == 502
    assert "privado" not in response.text


@pytest.mark.parametrize("error,status", [
    (httpx.ReadTimeout, 504), (httpx.ConnectError, 502),
])
def test_connection_errors(client_factory, error, status):
    def handler(request):
        raise error("privado", request=request)
    assert client_factory(handler).get("/tasks").status_code == status


def test_malformed_upstream(client_factory):
    client = client_factory(lambda r: httpx.Response(200, text="invalid"))
    assert client.get("/tasks").status_code == 502


def test_missing_configuration(monkeypatch):
    monkeypatch.delenv("DIRECTUS_TOKEN", raising=False)
    with TestClient(app) as client:
        assert client.get("/tasks").status_code == 503
