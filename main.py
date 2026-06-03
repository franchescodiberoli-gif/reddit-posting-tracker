"""
main.py — Reddit Post Scraper
Detonador: campo "publicado?" = True en Content.
Por cada registro nuevo marcado:
  1. Lee datos de Content (y sus lookups)
  2. Busca el post en Reddit por título + subreddit
  3. Crea fila en Posting Schedule con todo lo que encontró
Corre cada 24 horas.
"""

import os
import time
import logging
from datetime import datetime, timezone

import airtable as AT
import reddit   as RD
from config import *

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCRAPER] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def safe(fields, key, default=""):
    """Lee un campo de forma segura."""
    val = fields.get(key, default)
    if val is None:
        return default
    return val


def lookup_str(fields, key):
    """
    Los campos lookup en Airtable devuelven listas.
    Retorna el primer elemento como string, o "".
    """
    val = fields.get(key)
    if isinstance(val, list):
        return str(val[0]) if val else ""
    if val is None:
        return ""
    return str(val)


def find_existing_ps_row(content_num_id):
    """
    Busca si ya existe una fila en Posting Schedule para este Content ID.
    Retorna (record_id, fields) de la fila existente, o (None, None).
    """
    formula  = f'{{Content ID}}="{content_num_id}"'
    existing = AT.fetch_all(TABLE_POSTING_SCHEDULE, filter_formula=formula)
    if existing:
        return existing[0]["id"], existing[0].get("fields", {})
    return None, None


# ─── CORE ────────────────────────────────────────────────────────────────────

def process_content_record(rec):
    """
    Procesa un registro de Content marcado como publicado.
    Crea la fila correspondiente en Posting Schedule.
    """
    record_id = rec["id"]
    fields    = rec.get("fields", {})

    # ID numérico del registro (autonumber de Airtable)
    content_num_id = safe(fields, CON_ID, "")

    # ¿Ya existe una fila para este Content?
    existing_row_id, existing_fields = find_existing_ps_row(str(content_num_id))

    # Si ya existe Y el post tiene más de 48h de publicado → NO actualizar más.
    # El post de Reddit ya murió organicamente, sus stats quedan congeladas.
    UPDATE_WINDOW_HOURS = 48
    if existing_row_id and existing_fields:
        fecha_pub_existente = existing_fields.get(PS_FECHA_PUB)
        if fecha_pub_existente:
            try:
                from datetime import datetime, timezone
                dt_pub = datetime.fromisoformat(
                    fecha_pub_existente.replace("Z", "+00:00")
                )
                horas_desde_pub = (
                    datetime.now(tz=timezone.utc) - dt_pub
                ).total_seconds() / 3600
                if horas_desde_pub > UPDATE_WINDOW_HOURS:
                    logging.info(
                        f"  Content ID {content_num_id}: post tiene "
                        f"{horas_desde_pub:.0f}h (>{UPDATE_WINDOW_HOURS}h), "
                        f"congelado. Saltando."
                    )
                    return
            except Exception as e:
                logging.warning(f"  No se pudo parsear fecha de publicacion: {e}")

    # ── Datos básicos de Content ──────────────────────────────────────────
    username   = lookup_str(fields, CON_REDDIT_NAMAE)  # nombre de cuenta de Reddit
    titulo     = safe(fields, CON_TITULO)
    flair_val  = safe(fields, CON_FLAIR)
    metodo     = safe(fields, CON_METODO)
    bann       = safe(fields, CON_BANN)
    status_con = safe(fields, CON_STATUS)
    picture    = safe(fields, CON_PICTURE)
    redgif_url = safe(fields, CON_REDGIF_URL)
    type_val   = safe(fields, CON_TYPE)

    # Subreddit: viene como lookup (lista)
    subreddit_name = lookup_str(fields, "subreddit name (de Subreddit)")
    if not subreddit_name:
        # Intentar campo directo
        subreddit_name = lookup_str(fields, CON_SUBREDDIT)

    # Lookups de Accounts (vienen como listas)
    model_name      = lookup_str(fields, "Model Name (from Accounts)")
    niche_val       = lookup_str(fields, "Niche (from Subreddits) (from Accounts)")
    poster_val      = lookup_str(fields, "Poster (from Accounts)")
    agency_val      = lookup_str(fields, "Agency (from Accounts)")
    subreddits_val  = lookup_str(fields, "Subreddits (from Accounts)")

    # Lookups de Subreddits
    nicho_sub       = lookup_str(fields, "nicho (de Subreddit)")
    mejor_horario   = lookup_str(fields, "mejor horario (de Subreddit)")
    tipo_contenido  = lookup_str(fields, "tipo de contenido (de Subreddit)")
    url_subreddit   = lookup_str(fields, "URL (de Subreddit)")

    logging.info(f"\n--- Content ID {content_num_id} | u/{username} | r/{subreddit_name} ---")
    logging.info(f"    Titulo: {titulo[:60]}")

    # ── Buscar post en Reddit ─────────────────────────────────────────────
    post_found = None
    if username and titulo:
        post_found = RD.find_post_by_title(username, subreddit_name, titulo)
        time.sleep(2)  # respetar rate limit

    # ── Construir fila de Posting Schedule ───────────────────────────────
    now_iso = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    ps_fields = {
        # ── Siempre se llenan ──────────────────────────────────────────
        PS_PUBLICADO:      "SI" if post_found else "NO",
        PS_CONTENT_ID:     str(content_num_id),
        PS_CONTENT_LINK:   [record_id],          # link al registro Content
        PS_REDDIT_NAMAE:   username,
        PS_MODEL_NAME:     model_name,
        PS_SUBREDDITS:     subreddits_val,
        PS_NICHE:          niche_val,
        PS_POSTER:         poster_val,
        PS_AGENCY:         agency_val,
        PS_SUBREDDIT_NAME: subreddit_name,
        PS_NICHO_SUB:      nicho_sub,
        PS_MEJOR_HORARIO:  mejor_horario,
        PS_TIPO_CONTENIDO: tipo_contenido,
        PS_METODO:         metodo,
        PS_BANN:           bann,
        PS_STATUS:         status_con,

        # ── Vacíos — se llenan manualmente ────────────────────────────
        # PS_NUM_VISITAS, PS_VOTES_COMPRADOS, PS_INVERSION, PS_GANANCIA
    }

    if post_found:
        # ── Datos reales del post en Reddit ───────────────────────────
        created_utc = post_found.get("created_utc")
        fecha_pub = RD.format_utc(created_utc)
        url_post  = f"https://www.reddit.com{post_found.get('permalink', '')}"
        upvotes   = post_found.get("ups", 0)
        downvotes = post_found.get("downs", 0)
        comments  = post_found.get("num_comments", 0)
        flair_r   = post_found.get("link_flair_text") or flair_val
        titulo_r  = post_found.get("title") or titulo
        media_url = RD.extract_media_url(post_found)

        # ── Virality score = upvotes / horas desde publicacion ────────
        # Mide la VELOCIDAD con la que gana upvotes, no el total acumulado.
        virality = 0.0
        if created_utc:
            horas = (time.time() - created_utc) / 3600
            if horas < 1:
                horas = 1  # evitar dividir por casi-cero en posts muy nuevos
            virality = round(upvotes / horas, 2)

        ps_fields[PS_FECHA_PUB]   = fecha_pub
        ps_fields[PS_URL_POST]    = url_post
        ps_fields[PS_VOTES_NORMAL]= upvotes
        ps_fields[PS_VOTOS_MALOS] = downvotes
        ps_fields[PS_NUM_COMMENTS]= comments
        ps_fields[PS_VIRALITY]    = virality
        ps_fields[PS_TITULO]      = titulo_r
        ps_fields[PS_FLAIR]       = flair_r
        ps_fields[PS_TYPE]        = type_val

        # Picture y RedGif: usar los del post real si hay, si no los de Content
        if media_url:
            ps_fields[PS_PICTURE] = media_url
        elif picture:
            ps_fields[PS_PICTURE] = picture

        if redgif_url:
            ps_fields[PS_REDGIF_URL] = redgif_url

        logging.info(f"  ✅ Post encontrado → {url_post}")
        logging.info(f"     Upvotes: {upvotes} | Virality: {virality}/h | Comentarios: {comments}")

    else:
        # ── Post no encontrado: campos de Reddit vacíos ───────────────
        # titulo, flair, picture, redgif, type → vacíos (no confirmar)
        logging.info(f"  ❌ Post NO encontrado en Reddit")

    # ── Guardar en Posting Schedule (crear o actualizar) ──────────────────
    try:
        if existing_row_id:
            # Actualizar fila existente — pero NO pisar los campos manuales
            # (num. visitas, UP votes comprados, INVERSION, GANANCIA, titulo 2.0)
            campos_manuales = {
                PS_NUM_VISITAS, PS_VOTES_COMPRADOS, PS_INVERSION,
                PS_GANANCIA, PS_TITULO_2
            }
            update_fields = {
                k: v for k, v in ps_fields.items()
                if k not in campos_manuales
            }
            AT.update_record(TABLE_POSTING_SCHEDULE, existing_row_id, update_fields)
            logging.info(f"  🔄 Fila actualizada en Posting Schedule")
        else:
            AT.create_record(TABLE_POSTING_SCHEDULE, ps_fields)
            logging.info(f"  💾 Fila creada en Posting Schedule")

        # Actualizar status en Content
        AT.update_record(TABLE_CONTENT, record_id, {
            CON_STATUS: "Published" if post_found else "Pending"
        })

    except Exception as e:
        logging.error(f"  ❌ Error guardando en Posting Schedule: {e}")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def run_scraper():
    logging.info("=" * 60)
    logging.info("Iniciando ciclo de scraping...")

    # Filtrar solo Content con publicado? = true
    # y que no tenga ya una fila en Posting Schedule (usamos Content ID)
    content_records = AT.fetch_all(
        TABLE_CONTENT,
        filter_formula=f'{{{CON_PUBLICADO}}}=1'
    )

    if not content_records:
        logging.info("No hay registros con publicado? marcado. Nada que procesar.")
        return

    logging.info(f"{len(content_records)} registros marcados como publicado?")

    for rec in content_records:
        try:
            process_content_record(rec)
        except Exception as e:
            logging.error(f"Error procesando registro {rec['id']}: {e}", exc_info=True)
        time.sleep(1)

    logging.info("✅ Ciclo completado.")


if __name__ == "__main__":
    INTERVAL_HOURS = 24
    while True:
        try:
            run_scraper()
        except Exception as e:
            logging.error(f"Error crítico en scraper: {e}", exc_info=True)
        logging.info(f"Esperando {INTERVAL_HOURS}h...")
        time.sleep(INTERVAL_HOURS * 3600)
