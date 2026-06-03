"""
config.py — Nombres exactos de tablas y campos en Airtable.
Ajusta aquí si cambias algo en Airtable.
"""

# ─── TABLAS ──────────────────────────────────────────────────────────────────
TABLE_ACCOUNTS         = "Accounts"
TABLE_CONTENT          = "Content"
TABLE_POSTING_SCHEDULE = "Posting Schedule"

# ─── CAMPOS: Accounts ────────────────────────────────────────────────────────
ACC_USERNAME        = "Reddit Username"
ACC_NOMBRE_CUENTA   = "nombre de cuenta"
ACC_MODEL_NAME      = "Model Name"
ACC_FOLLOWERS       = "Followers"
ACC_POSTS_MADE      = "Posts Made"
ACC_POST_KARMA      = "Post Karma"
ACC_COMMENTS_MADE   = "Comments Made"
ACC_COMMENT_KARMA   = "Comment Karma"
ACC_TOTAL_KARMA     = "Total Karma"
ACC_STATUS          = "Status"          # "Active" | "SUSPENDED" | "BANNED" | "UNKNOWN"
ACC_LAST_CHECKED    = "Last Checked"    # campo que el checker actualiza
ACC_ACCOUNT_AGE     = "Account Age"
ACC_START_DATE      = "Start Date"
ACC_DAYS_SINCE      = "Days Since Started"

# ─── CAMPOS: Content ─────────────────────────────────────────────────────────
CON_ID              = "ID"              # autonumber
CON_REDDIT_NAMAE    = "REDDIT NAMAE"    # link a Accounts
CON_SUBREDDIT       = "Subreddit"       # link a Subreddits
CON_TITULO          = "titulo"
CON_FLAIR           = "flair"
CON_NOTAS           = "notas"
CON_METODO          = "metodo"          # "organico" etc
CON_BANN            = "bann?"           # single select: "no" | "si"
CON_FECHA_PUB       = "fecha de publicacion"
CON_PUBLICADO       = "publicado?"      # checkbox — DETONADOR
CON_URL_POST        = "URL del post"
CON_PICTURE         = "Picture"
CON_REDGIF_URL      = "RedGif URL"
CON_TYPE            = "Type"
CON_STATUS          = "Status"          # "Pending" | "Published"
CON_VISITAS         = "visitas"
CON_VOTES_NORMAL    = "votes normales ganados"
CON_VOTES_COMPRADOS = "up votes comprados"
CON_INVERSION       = "INVERSION EN UPVOTES"
CON_GANANCIA        = "GANANCIA?"
CON_VOTOS_MALOS     = "votos malos"
CON_NUM_COMMENTS    = "num. post coments"

# ─── CAMPOS: Posting Schedule ────────────────────────────────────────────────
PS_PUBLICADO        = "PUBLICADO?"           # single select: "SI" | "NO"
PS_FECHA_PUB        = "Fecha de publicacion"
PS_CONTENT_ID       = "Content ID"           # número — ID del registro Content
PS_CONTENT_LINK     = "Content"              # link al registro Content
PS_REDDIT_NAMAE     = "REDDIT NAMAE"         # texto (copiado de Content)
PS_MODEL_NAME       = "Model Name"
PS_SUBREDDITS       = "Subreddits"
PS_NICHE            = "Niche"
PS_POSTER           = "Poster"
PS_AGENCY           = "Agency"
PS_SUBREDDIT_NAME   = "Subreddit"            # nombre del subreddit
PS_NICHO_SUB        = "nicho (de Subreddit)"
PS_MEJOR_HORARIO    = "mejor horario (de Subreddit)"
PS_TIPO_CONTENIDO   = "tipo de contenido (de Subreddit)"
PS_PICTURE          = "Picture"
PS_REDGIF_URL       = "RedGif URL"
PS_TYPE             = "Type"
PS_TITULO           = "titulo"
PS_TITULO_2         = "titulo 2.0"           # vacío — se llena manualmente
PS_FLAIR            = "flair"
PS_METODO           = "metodo"
PS_BANN             = "bann?"
PS_STATUS           = "Status"
PS_URL_POST         = "URL del post"
PS_NUM_VISITAS      = "num. visitas"         # vacío — manual
PS_VOTES_NORMAL     = "UP votes normal"
PS_VOTES_COMPRADOS  = "UP votes comprados"   # vacío — manual
PS_INVERSION        = "INVERSION EN UPVOTES" # vacío — manual
PS_GANANCIA         = "GANANCIA?"            # vacío — manual (o formula)
PS_VOTOS_MALOS      = "votos malos"
PS_NUM_COMMENTS     = "num. post coment"
PS_VIRALITY         = "Virality score"       # upvotes / horas desde publicacion (Number)
PS_CONTENT_PROC     = "Content procesado"    # campo interno para no reprocesar
