# Directus + FastAPI: CRUD de tareas

FastAPI recibe peticiones HTTP, consume la API de Directus y Directus guarda las
tareas en PostgreSQL. La colección `tasks` tiene `id`, `title` y `completed`;
el servicio `init` la crea automáticamente y conserva los datos al reiniciar.

## Ejecutar

Requisitos: Docker con Compose v2 y Python 3.12.

```bash
python3 scripts/configure.py
docker compose up --build --wait
```

El script genera un `.env` privado con valores aleatorios. También puedes copiar
`.env.example` a `.env` y completar todos sus campos. Nunca subas `.env`.
FastAPI: http://localhost:8000/docs. Directus: http://localhost:8055;
las credenciales están en `.env`. PostgreSQL no publica puertos.

```bash
curl -X POST localhost:8000/tasks -H 'Content-Type: application/json' \
  -d '{"title":"Preparar entrega"}'
curl localhost:8000/tasks
curl localhost:8000/tasks/1
curl -X PATCH localhost:8000/tasks/1 -H 'Content-Type: application/json' \
  -d '{"completed":true}'
curl -X DELETE localhost:8000/tasks/1
```

Rutas: `GET/POST /tasks`, `GET/PATCH/DELETE /tasks/{id}` y `GET /health`.
El listado admite `limit` (1–100) y `offset`. PATCH modifica solo los campos
enviados. Entradas inválidas devuelven 422; tareas inexistentes, 404; errores de
Directus, 502; demoras, 504. La salud comprueba acceso a la colección.

## Pruebas y entrega

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
TEST_BASE_URL=http://localhost:8000 python -m pytest -q tests/test_integration.py
docker compose down
```

pytest cubre validación, traducción HTTP, fallos de Directus y un CRUD real con
lectura posterior para comprobar persistencia. La prueba real se omite si falta
`TEST_BASE_URL`. Actions ejecuta ambas suites, levanta Compose y construye la
imagen; en cada push a `main` la publica en
`ghcr.io/capstone-2026-disc/directus-fastapi-demo` con etiquetas `latest` y SHA.
No requiere secretos configurados en GitHub; utiliza su token temporal.

Demo local: FastAPI no exige autenticación y usa el token del administrador de
Directus. Ambos puertos están ligados a localhost. Para un despliegue compartido,
añade autenticación y un usuario de servicio con permisos limitados a `tasks`.
El volumen conserva PostgreSQL; `docker compose down -v` elimina esos datos.
Al reutilizar el volumen, conserva el `.env` original.

## Colaboración

Nicolás (`nico-alvz`) y `CrisPalaUnion` pertenecen a la organización.
Fabián tiene una invitación pendiente a Capstone-2026-DISC; se incorporará al
repositorio cuando acepte.

Referencias: [Docker](https://docs.directus.io/self-hosted/docker-guide),
[colecciones](https://docs.directus.io/reference/system/collections) y
[autenticación](https://docs.directus.io/reference/authentication) de Directus.
