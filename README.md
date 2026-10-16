<div align="center">

<img src="docs/banner.svg" alt="Directus y FastAPI" width="100%">

# Directus + FastAPI

CRUD de tareas que muestra cómo una API en FastAPI puede apoyarse en Directus para guardar datos en SQLite

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Directus](https://img.shields.io/badge/Directus-11-6644FF?style=for-the-badge&logo=directus&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![CI](https://img.shields.io/github/actions/workflow/status/Capstone-2026-DISC/directus-fastapi-demo/ci.yml?branch=main&style=for-the-badge&label=CI&logo=githubactions&logoColor=white)

</div>

## Arquitectura

FastAPI valida las peticiones y las traduce a llamadas HTTP contra Directus. Directus aplica sus reglas y accede a SQLite mediante Knex.js, su constructor de consultas SQL, con el controlador `sqlite3`. Los datos se guardan en el archivo `data.db` del volumen `directus_data`. En el flujo del CRUD, solo Directus accede al archivo.

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
            sqlite["Controlador sqlite3"]
        end
        subgraph volumen ["Volumen directus_data"]
            db[("SQLite: data.db")]
        end
        init["init (crea la colección)"]
    end

    cliente -->|JSON| rutas
    rutas --> modelos
    rutas --> http
    http -->|"Bearer token"| rest
    rest --> servicios --> knex
    knex --> sqlite
    sqlite -->|"SQL / acceso al archivo"| db
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
    participant S as sqlite3
    participant B as data.db (volumen directus_data)

    C->>F: POST /tasks con title
    F->>F: Valida con Pydantic
    F->>D: POST /items/tasks con Bearer token
    D->>D: Revisa permisos y reglas
    D->>K: Crea la consulta
    K->>S: Ejecuta la consulta SQL
    S->>B: INSERT INTO tasks
    B-->>S: Fila creada
    S-->>K: Registro
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
    note for tasks "Tabla en data.db (volumen directus_data)"
    TaskCreate <|-- Task
    Task ..> tasks : se guarda en
    TaskUpdate ..> tasks : PATCH parcial
```

## Servicios

| Servicio | Imagen | Rol | Puerto |
| --- | --- | --- | --- |
| `directus` | Directus 11 | API de datos, panel y acceso al archivo SQLite | 8055 |
| `init` | Imagen propia | Crea la colección `tasks` y termina | ninguno |
| `fastapi` | Imagen propia | Expone el CRUD | 8000 |

El orden de arranque es `directus`, `init` y `fastapi`. Cuando Directus está saludable, `init` crea la colección; al terminar correctamente, arranca FastAPI. SQLite no necesita un servicio aparte.

## Entender el backend

FastAPI valida los datos con Pydantic y usa `httpx` para llamar a Directus; no ejecuta SQL. Directus gestiona la colección `tasks`, sus permisos y las consultas que Knex.js ejecuta mediante `sqlite3`. El archivo `/directus/database/data.db` contiene tanto las tareas como las tablas internas de Directus.

Con los servicios levantados y la herramienta `sqlite3` instalada, puedes copiar la base e inspeccionar su esquema:

```bash
docker compose cp directus:/directus/database/data.db ./data.db
sqlite3 data.db .schema
```

La tabla `tasks` tiene las columnas `id`, `title` y `completed`. La copia permite leer el esquema localmente; modificarla no cambia la base que usa Directus. `data.db` y sus archivos auxiliares quedan excluidos de Git y del contexto Docker.

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

Es una demo local. FastAPI no pide autenticación y usa el token del administrador de Directus, y ambos puertos escuchan solo en localhost. Para un despliegue compartido conviene agregar autenticación y un usuario de servicio con permisos limitados a `tasks`. El volumen `directus_data` conserva el archivo SQLite `data.db` al reiniciar los servicios, y `docker compose down -v` elimina ese volumen y sus datos.

## Referencias

[Directus con Docker](https://docs.directus.io/self-hosted/docker-guide) · [Colecciones](https://docs.directus.io/reference/system/collections) · [Autenticación](https://docs.directus.io/reference/authentication) · [FastAPI](https://fastapi.tiangolo.com/)
