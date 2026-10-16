"""CRUD de tareas que utiliza la API HTTP de Directus."""
import os
from collections.abc import Iterator
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Path, Query, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

app = FastAPI(title="Tareas: FastAPI + Directus")


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=200)
    completed: bool = False


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    completed: bool | None = None

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("Indica al menos un campo.")
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("Los campos no admiten null.")
        return self


class Task(TaskCreate):
    id: int


def get_directus() -> Iterator[httpx.Client]:
    token = os.environ.get("DIRECTUS_TOKEN")
    if not token:
        raise HTTPException(503, "Falta configurar Directus.")
    with httpx.Client(
        base_url=os.environ.get("DIRECTUS_URL", "http://directus:8055"),
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    ) as client:
        yield client


Directus = Annotated[httpx.Client, Depends(get_directus)]
TaskId = Annotated[int, Path(gt=0)]


def request(client: httpx.Client, method: str, path: str, **kwargs):
    try:
        response = client.request(method, path, **kwargs)
    except httpx.TimeoutException:
        raise HTTPException(504, "Directus no respondió a tiempo.") from None
    except httpx.RequestError:
        raise HTTPException(502, "No se pudo conectar con Directus.") from None
    if response.status_code == 404:
        raise HTTPException(404, "Tarea no encontrada.")
    if response.is_error:
        raise HTTPException(502, "Directus rechazó la operación.")
    if response.status_code == 204:
        return None
    try:
        return response.json()["data"]
    except (ValueError, KeyError, TypeError):
        raise HTTPException(502, "Respuesta inválida de Directus.") from None


def find_task(client: httpx.Client, task_id: int):
    tasks = request(client, "GET", "/items/tasks", params={
        "filter[id][_eq]": task_id, "limit": 1,
    })
    if not tasks:
        raise HTTPException(404, "Tarea no encontrada.")
    return tasks[0]


@app.get("/health")
def health(client: Directus):
    request(client, "GET", "/items/tasks", params={"limit": 1})
    return {"status": "ok"}


@app.get("/tasks", response_model=list[Task])
def list_tasks(client: Directus,
               limit: Annotated[int, Query(ge=1, le=100)] = 100,
               offset: Annotated[int, Query(ge=0)] = 0):
    return request(client, "GET", "/items/tasks",
                   params={"sort": "id", "limit": limit, "offset": offset})


@app.post("/tasks", response_model=Task, status_code=201)
def create_task(task: TaskCreate, client: Directus):
    return request(client, "POST", "/items/tasks", json=task.model_dump())


@app.get("/tasks/{task_id}", response_model=Task)
def read_task(task_id: TaskId, client: Directus):
    return find_task(client, task_id)


@app.patch("/tasks/{task_id}", response_model=Task)
def update_task(task_id: TaskId, task: TaskUpdate, client: Directus):
    find_task(client, task_id)
    return request(client, "PATCH", f"/items/tasks/{task_id}",
                   json=task.model_dump(exclude_unset=True))


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: TaskId, client: Directus):
    find_task(client, task_id)
    request(client, "DELETE", f"/items/tasks/{task_id}")
    return Response(status_code=204)
