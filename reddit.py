"""
reddit.py — Funciones para interactuar con Reddit.
Usa endpoints públicos .json — sin API key, sin OAuth.
Funciona como un navegador normal visitando perfiles públicos.
"""

import time
import logging
import requests

# Simular navegador real para no ser bloqueado
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}

BASE_URL = "https://www.reddit.com"


def _get(url, params=None, retries=3):
    """GET con manejo de rate limit y reintentos."""
    for attempt in range(retries):
        try:
            resp = requests.get(
                url,
                headers=HEADERS,
                params=params or {},
                timeout=20
            )

            # Rate limit — esperar y reintentar
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 60))
                logging.warning(f"[Reddit] Rate limit — esperando {wait}s")
                time.sleep(wait)
                continue

            return resp

        except requests.Timeout:
            logging.warning(f"[Reddit] Timeout en {url} (intento {attempt+1})")
            time.sleep(5)
        except requests.ConnectionError as e:
            logging.warning(f"[Reddit] Error de conexión: {e} (intento {attempt+1})")
            time.sleep(5)

    return None


def get_user_posts(username, limit=100):
    """
    Trae los posts más recientes de un usuario vía endpoint público.
    URL: reddit.com/user/{username}/submitted.json
    Retorna lista de dicts con los datos del post, o [] si hay error.
    """
    url  = f"{BASE_URL}/user/{username}/submitted.json"
    resp = _get(url, params={"limit": limit, "sort": "new", "t": "all"})

    if resp is None:
        logging.error(f"[Reddit] No se pudo conectar para u/{username}")
        return []

    if resp.status_code == 404:
        logging.warning(f"[Reddit] u/{username} no existe (404)")
        return []

    if resp.status_code == 403:
        logging.warning(f"[Reddit] u/{username} suspendida/privada (403)")
        return []

    if resp.status_code != 200:
        logging.error(f"[Reddit] HTTP {resp.status_code} para u/{username}")
        return []

    try:
        data  = resp.json()
        posts = data.get("data", {}).get("children", [])
        logging.info(f"[Reddit] u/{username}: {len(posts)} posts encontrados")
        return [p["data"] for p in posts]
    except Exception as e:
        logging.error(f"[Reddit] Error parseando JSON de u/{username}: {e}")
        return []


def find_post_by_title(username, subreddit, title, threshold=0.6):
    """
    Busca en los posts del usuario el que coincida con el título dado
    en el subreddit indicado. Usa similitud de texto simple.
    Retorna el post dict si lo encuentra, o None.
    """
    posts = get_user_posts(username, limit=100)
    title_clean = title.strip().lower()

    best_match  = None
    best_score  = 0.0

    for post in posts:
        # Filtrar por subreddit
        post_sub = post.get("subreddit", "").lower()
        if subreddit and post_sub != subreddit.lower():
            continue

        post_title = post.get("title", "").strip().lower()

        # Similitud simple: palabras en común / total palabras
        words_a = set(title_clean.split())
        words_b = set(post_title.split())
        if not words_a:
            continue

        common = words_a & words_b
        score  = len(common) / max(len(words_a), len(words_b))

        if score > best_score:
            best_score = score
            best_match = post

    if best_match and best_score >= threshold:
        logging.info(
            f"[Reddit] Post encontrado para '{title[:40]}' "
            f"(score={best_score:.2f}) → {best_match.get('url', '')}"
        )
        return best_match

    logging.info(
        f"[Reddit] No se encontró post para '{title[:40]}' "
        f"en r/{subreddit} (mejor score={best_score:.2f})"
    )
    return None


def extract_media_url(post):
    """Extrae URL de imagen o video del post."""
    url = post.get("url", "")
    if any(ext in url for ext in [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".gifv"]):
        return url
    # Reddit gallery
    if post.get("is_gallery"):
        meta = post.get("media_metadata", {})
        if meta:
            key  = next(iter(meta))
            item = meta[key]
            if item.get("status") == "valid":
                src = item.get("s", {})
                return src.get("u", "").replace("&amp;", "&")
    # Hosted video
    if post.get("is_video"):
        return post.get("media", {}).get("reddit_video", {}).get("fallback_url", "")
    return ""


def format_utc(ts):
    """Convierte timestamp Unix a ISO 8601 para Airtable."""
    if not ts:
        return None
    from datetime import datetime, timezone
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
