"""
checker.py — Verifica status de todas las cuentas en Accounts.
Visita reddit.com/user/{username}.json como navegador normal.
Actualiza: Status, Followers, Post Karma, Comment Karma, Total Karma, Posts Made.
Corre cada 24 horas.
"""

import os
import time
import logging
import requests
from datetime import datetime, timezone

import airtable as AT
from config import *

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CHECKER] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Mismo User-Agent que reddit.py para consistencia
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Accept": "application/json, text/html, */*",
}

STATUS_ACTIVE    = "Active"
STATUS_SUSPENDED = "SUSPENDED"
STATUS_BANNED    = "BANNED"
STATUS_UNKNOWN   = "UNKNOWN"


def check_account(username):
    """
    Visita reddit.com/user/{username}/about.json
    Retorna dict con status y estadísticas de la cuenta.
    """
    result = {
        "status":        STATUS_UNKNOWN,
        "followers":     None,
        "post_karma":    None,
        "comment_karma": None,
        "total_karma":   None,
        "posts_made":    None,
    }

    url = f"https://www.reddit.com/user/{username}/about.json"

    try:
        resp = requests.get(url, headers=BROWSER_HEADERS, timeout=20)

        if resp.status_code == 404:
            result["status"] = STATUS_BANNED
            return result

        if resp.status_code == 403:
            result["status"] = STATUS_SUSPENDED
            return result

        if resp.status_code != 200:
            logging.warning(f"  u/{username} → HTTP {resp.status_code}")
            result["status"] = STATUS_UNKNOWN
            return result

        body = resp.json()
        data = body.get("data", {})

        # Verificar suspensión desde el JSON
        if data.get("is_suspended"):
            result["status"] = STATUS_SUSPENDED
            return result

        if body.get("error") in [403, 404]:
            result["status"] = STATUS_BANNED if body["error"] == 404 else STATUS_SUSPENDED
            return result

        # Cuenta activa — extraer estadísticas
        result["status"]        = STATUS_ACTIVE
        result["post_karma"]    = data.get("link_karma", 0)
        result["comment_karma"] = data.get("comment_karma", 0)
        result["total_karma"]   = data.get("total_karma", 0)

        # Followers (icon_img no es followers, usamos subreddit subscribers si aplica)
        subs = data.get("subreddit", {})
        result["followers"] = subs.get("subscribers", 0)

        return result

    except requests.Timeout:
        logging.error(f"  u/{username} → Timeout")
        return result
    except requests.ConnectionError:
        logging.error(f"  u/{username} → Error de conexión")
        return result
    except Exception as e:
        logging.error(f"  u/{username} → Error: {e}")
        return result


def run_checker():
    logging.info("=" * 60)
    logging.info("Iniciando verificación de cuentas...")

    accounts = AT.fetch_all(TABLE_ACCOUNTS)
    if not accounts:
        logging.info("No hay cuentas en Airtable.")
        return

    now_iso  = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    updated  = 0

    for rec in accounts:
        record_id = rec["id"]
        fields    = rec.get("fields", {})
        username  = fields.get(ACC_USERNAME, "").strip()

        if not username:
            continue

        logging.info(f"Chequeando u/{username}...")
        info = check_account(username)

        update_fields = {
            ACC_STATUS:       info["status"],
            ACC_LAST_CHECKED: now_iso,
        }

        # Solo actualizar stats si la cuenta está activa
        if info["status"] == STATUS_ACTIVE:
            if info["post_karma"]    is not None:
                update_fields[ACC_POST_KARMA]    = info["post_karma"]
            if info["comment_karma"] is not None:
                update_fields[ACC_COMMENT_KARMA] = info["comment_karma"]
            if info["total_karma"]   is not None:
                update_fields[ACC_TOTAL_KARMA]   = info["total_karma"]
            if info["followers"]     is not None:
                update_fields[ACC_FOLLOWERS]     = info["followers"]

        try:
            AT.update_record(TABLE_ACCOUNTS, record_id, update_fields)
            logging.info(f"  ✅ u/{username} → {info['status']}")
            updated += 1
        except Exception as e:
            logging.error(f"  ❌ Error actualizando u/{username}: {e}")

        # Pausa para no levantar banderas
        time.sleep(4)

    logging.info(f"✅ Verificación completada. {updated}/{len(accounts)} cuentas actualizadas.")


if __name__ == "__main__":
    INTERVAL_HOURS = 24
    while True:
        try:
            run_checker()
        except Exception as e:
            logging.error(f"Error crítico en checker: {e}", exc_info=True)
        logging.info(f"Esperando {INTERVAL_HOURS}h...")
        time.sleep(INTERVAL_HOURS * 3600)
