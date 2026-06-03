"""
airtable.py — Funciones para leer y escribir en Airtable.
"""

import os
import time
import logging
import requests
from urllib.parse import quote

AT_API_KEY  = os.environ["AIRTABLE_API_KEY"]
AT_BASE_ID  = os.environ["AIRTABLE_BASE_ID"]
AT_BASE_URL = f"https://api.airtable.com/v0/{AT_BASE_ID}"
AT_HEADERS  = {
    "Authorization": f"Bearer {AT_API_KEY}",
    "Content-Type":  "application/json"
}


def _url(table):
    return f"{AT_BASE_URL}/{quote(table)}"


def fetch_all(table, filter_formula=None):
    """Trae todos los registros de una tabla con paginación."""
    records = []
    params  = {}
    if filter_formula:
        params["filterByFormula"] = filter_formula

    while True:
        resp = requests.get(_url(table), headers=AT_HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        body = resp.json()
        records.extend(body.get("records", []))
        offset = body.get("offset")
        if not offset:
            break
        params["offset"] = offset
        time.sleep(0.3)

    logging.info(f"[Airtable] '{table}': {len(records)} registros")
    return records


def create_record(table, fields):
    resp = requests.post(
        _url(table),
        json={"records": [{"fields": fields}]},
        headers=AT_HEADERS,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()["records"][0]


def update_record(table, record_id, fields):
    resp = requests.patch(
        f"{_url(table)}/{record_id}",
        json={"fields": fields},
        headers=AT_HEADERS,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def record_exists(table, filter_formula):
    """Devuelve True si ya existe al menos un registro que cumpla el filtro."""
    records = fetch_all(table, filter_formula=filter_formula)
    return len(records) > 0
