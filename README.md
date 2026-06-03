# Reddit-Airtable Scraper v2

## Archivos

| Archivo | Qué hace |
|---|---|
| `config.py` | Nombres de todas las tablas y campos |
| `airtable.py` | Funciones para leer/escribir Airtable |
| `reddit.py` | Funciones para la API de Reddit |
| `checker.py` | Verifica status de cuentas cada 24h |
| `main.py` | Scraper principal — detonado por publicado? |
| `runner.py` | Arranca ambos procesos, los reinicia si se caen |

---

## Flujo del bot

```
Content (publicado? = ✅)
        │
        ▼
¿Ya existe fila en Posting Schedule (por Content ID)?
        │
    ┌───┴────┐
   NO       SÍ
    │        │
    ▼        ▼
 CREAR    ACTUALIZAR (re-scrapea upvotes,
  fila     comentarios, virality, etc.
           sin pisar campos manuales)
    │        │
    └───┬────┘
        ▼
Buscar post en Reddit (u/username → r/subreddit → titulo similar)
```

**Ventana de actualización: 48 horas.** Cada corrida (cada 24h) re-scrapea los
posts publicados que tengan MENOS de 48h de vida y actualiza sus stats (upvotes,
comentarios, votos malos, virality score). Después de 48h el post de Reddit ya
murió orgánicamente (la vida media de un post es ~2.5h y casi toda la actividad
ocurre en las primeras 24-48h), así que sus stats quedan congeladas. Los campos
manuales (num. visitas, UP votes comprados, INVERSION, GANANCIA, titulo 2.0)
NUNCA se sobrescriben.

---

## Variables de entorno en Render

```
AIRTABLE_API_KEY      → token de Airtable (empieza con pat...)
AIRTABLE_BASE_ID      → apphyb3tOmjIemkN6
REDDIT_CLIENT_ID      → de reddit.com/prefs/apps
REDDIT_CLIENT_SECRET  → de reddit.com/prefs/apps
REDDIT_USER_AGENT     → reddit-scraper-bot/1.0
```

---

## Campos que el bot llena en Posting Schedule

| Campo | Fuente | Bot? |
|---|---|---|
| PUBLICADO? | Lógica | ✅ SI / NO |
| Fecha de publicacion | Reddit | ✅ |
| Content ID | Airtable | ✅ |
| REDDIT NAMAE | Airtable (Content) | ✅ |
| Model Name | Airtable (lookup) | ✅ |
| Subreddits | Airtable (lookup) | ✅ |
| Niche | Airtable (lookup) | ✅ |
| Poster | Airtable (lookup) | ✅ |
| Agency | Airtable (lookup) | ✅ |
| Subreddit | Airtable (Content) | ✅ |
| nicho (de Subreddit) | Airtable (lookup) | ✅ |
| mejor horario | Airtable (lookup) | ✅ |
| tipo de contenido | Airtable (lookup) | ✅ |
| Picture | Reddit (si se encontró) | ✅ / vacío |
| RedGif URL | Content | ✅ |
| Type | Content | ✅ |
| titulo | Reddit (si se encontró) | ✅ / vacío |
| flair | Reddit (si se encontró) | ✅ / vacío |
| metodo | Airtable (Content) | ✅ |
| bann? | Airtable (Content) | ✅ |
| Status | Airtable (Content) | ✅ |
| URL del post | Reddit | ✅ / vacío |
| UP votes normal | Reddit | ✅ / vacío |
| votos malos | Reddit | ✅ / vacío |
| num. post coment | Reddit | ✅ / vacío |
| num. visitas | — | ❌ manual |
| UP votes comprados | — | ❌ manual |
| INVERSION EN UPVOTES | — | ❌ manual |
| GANANCIA? | — | ❌ manual / fórmula |
| titulo 2.0 | — | ❌ manual |

---

## Campos que el bot actualiza en Accounts (checker)

- Status → Active / SUSPENDED / BANNED / UNKNOWN
- Post Karma
- Comment Karma
- Total Karma
- Followers
- Last Checked

---

## Ajustar nombres de campos

Si algún campo en Airtable tiene un nombre diferente al código,
edita `config.py` y cambia la constante correspondiente.
Los nombres de lookup (campos que vienen "from Content", "from Accounts")
son los más propensos a variar — revísalos en config.py.
