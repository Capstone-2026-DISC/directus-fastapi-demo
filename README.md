<div align="center">

<img src="docs/banner.svg" alt="Directus y FastAPI" width="100%">

# Directus + FastAPI

CRUD de tareas que muestra cómo una API en FastAPI puede apoyarse en Directus para guardar datos en PostgreSQL

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Directus](https://img.shields.io/badge/Directus-11-6644FF?style=for-the-badge&logo=directus&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![CI](https://img.shields.io/github/actions/workflow/status/Capstone-2026-DISC/directus-fastapi-demo/ci.yml?branch=main&style=for-the-badge&label=CI&logo=githubactions&logoColor=white)

</div>

## Arquitectura

FastAPI valida las peticiones y las traduce a llamadas HTTP contra Directus. Directus aplica sus reglas y accede a la base de datos mediante Knex, su constructor de consultas SQL, con el controlador `pg` de PostgreSQL. Nada fuera de Directus toca la base.

```mermaid
flowchart LR
    cliente(["Cliente HTTP"])

    subgraph compose ["Docker Compose"]
        direction LR
        subgraph api ["fastapi"]
            rutas["Rutas /tasks"]
            modelos["Modelos Pydantic"]
            http["Cliente httpx"]
        end
        subgraph cms ["directus"]
            rest["API REST /items"]
            servicios["Servicios y permisos"]
            knex["Knex.js"]
        end
        pg[("postgres")]
        init["init (crea la colección)"]
    end

    cliente -->|JSON| rutas
    rutas --> modelos
    rutas --> http
    http -->|"Bearer token"| rest
    rest --> servicios --> knex
    knex -->|"SQL vía pg"| pg
    init -.->|"una sola vez"| rest
```

## Flujo de una petición

Así viaja un `POST /tasks` desde el cliente hasta la base y de vuelta.

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente
    participant F as FastAPI
    participant D as Directus
    participant K as Knex.js
    participant P as PostgreSQL

    C->>F: POST /tasks con title
    F->>F: Valida con Pydantic
    F->>D: POST /items/tasks con Bearer token
    D->>D: Revisa permisos y reglas
    D->>K: Crea la consulta
    K->>P: INSERT INTO tasks
    P-->>K: Fila creada
    K-->>D: Registro
    D-->>F: 200 con data
    F-->>C: 201 con la tarea
```

## Modelo

```mermaid
classDiagram
    class TaskCreate {
        +str title
        +bool completed
    }
    class TaskUpdate {
        +str title
        +bool completed
    }
    class Task {
        +int id
    }
    class tasks {
        <<colección Directus>>
        id integer
        title string
        completed boolean
    }
    TaskCreate <|-- Task
    Task ..> tasks : se guarda en
    TaskUpdate ..> tasks : PATCH parcial
```

## Servicios

| Servicio | Imagen | Rol | Puerto |
| --- | --- | --- | --- |
| `postgres` | PostgreSQL 17 | Almacena los datos | interno |
| `directus` | Directus 11 | API de datos y panel | 8055 |
| `init` | Imagen propia | Crea la colección `tasks` y termina | ninguno |
| `fastapi` | Imagen propia | Expone el CRUD | 8000 |

El orden de arranque es `postgres`, `directus`, `init` y `fastapi`, cada uno cuando el anterior está saludable.

## Uso

```bash
python3 scripts/configure.py
docker compose up --build --wait
```

El script crea un `.env` con valores aleatorios, que no se sube al repositorio. La documentación interactiva queda en http://localhost:8000/docs y el panel de Directus en http://localhost:8055.

```bash
curl -X POST localhost:8000/tasks -H 'Content-Type: application/json' \
  -d '{"title":"Preparar entrega"}'
curl localhost:8000/tasks
curl -X PATCH localhost:8000/tasks/1 -H 'Content-Type: application/json' \
  -d '{"completed":true}'
curl -X DELETE localhost:8000/tasks/1
```

| Ruta | Descripción |
| --- | --- |
| `GET /tasks` | Lista con `limit` (1 a 100) y `offset` |
| `POST /tasks` | Crea una tarea |
| `GET /tasks/{id}` | Obtiene una tarea |
| `PATCH /tasks/{id}` | Modifica solo los campos enviados |
| `DELETE /tasks/{id}` | Elimina una tarea |
| `GET /health` | Comprueba el acceso a la colección |

Una entrada inválida responde 422, una tarea inexistente 404, un error de Directus 502 y una demora 504.

## Pruebas y CI/CD

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
TEST_BASE_URL=http://localhost:8000 python -m pytest -q tests/test_integration.py
```

```mermaid
flowchart LR
    push(["push o pull request"]) --> unit["pytest unitarias"]
    unit --> up["docker compose up"]
    up --> real["CRUD real"]
    real --> build["Build de la imagen"]
    build -->|"solo en main"| ghcr[("GHCR")]
```

En cada push a `main` la imagen se publica en `ghcr.io/capstone-2026-disc/directus-fastapi-demo` con las etiquetas `latest` y el SHA del commit. El workflow usa el token temporal de Actions, sin secretos adicionales.

## Notas

Es una demo local. FastAPI no pide autenticación y usa el token del administrador de Directus, y ambos puertos escuchan solo en localhost. Para un despliegue compartido conviene agregar autenticación y un usuario de servicio con permisos limitados a `tasks`. El volumen conserva los datos de PostgreSQL, y `docker compose down -v` los elimina.

## Referencias

[Directus con Docker](https://docs.directus.io/self-hosted/docker-guide) · [Colecciones](https://docs.directus.io/reference/system/collections) · [Autenticación](https://docs.directus.io/reference/authentication) · [FastAPI](https://fastapi.tiangolo.com/)
