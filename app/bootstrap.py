"""Crea la colección inicial mediante la API de Directus."""
import os

import httpx


def main():
    headers = {"Authorization": f"Bearer {os.environ['DIRECTUS_TOKEN']}"}
    with httpx.Client(
        base_url=os.environ.get("DIRECTUS_URL", "http://directus:8055"),
        headers=headers,
        timeout=30,
    ) as client:
        response = client.get("/collections")
        response.raise_for_status()
        if any(item["collection"] == "tasks" for item in response.json()["data"]):
            print("La colección tasks ya existe.")
            return
        response = client.post("/collections", json={
            "collection": "tasks",
            "schema": {},
            "meta": {"icon": "checklist", "note": "Tareas del ejemplo CRUD"},
            "fields": [
                {"field": "id", "type": "integer",
                 "schema": {"is_primary_key": True, "has_auto_increment": True},
                 "meta": {"hidden": True}},
                {"field": "title", "type": "string",
                 "schema": {"is_nullable": False, "max_length": 200},
                 "meta": {"interface": "input", "required": True}},
                {"field": "completed", "type": "boolean",
                 "schema": {"is_nullable": False, "default_value": False},
                 "meta": {"interface": "boolean"}},
            ],
        })
        response.raise_for_status()
        print("Colección tasks creada.")


if __name__ == "__main__":
    main()
