#!/usr/bin/env python3
"""
Reddit Posting Tracker Bot
- Runs every 24h via GitHub Actions (free)
- Updates Accounts table with Reddit profile stats
- Scans Content table and fills Posting Schedule
- Skips Content rows whose account is Banned
- No Reddit API key needed -- uses public JSON endpoints
"""

import os
import time
import requests
from datetime import datetime, timezone
from pyairtable import Api

# --- CONFIG ---
AIRTABLE_API_KEY = os.environ["AIRTABLE_API_KEY"]
AIRTABLE_BASE_ID = os.environ["AIRTABLE_BASE_ID"]
PROXY_URL = os.environ.get("PROXY_URL")  # optional: http://user:pass@host:port
REDDIT_COOKIE = os.environ.get("REDDIT_COOKIE")

# Using table IDs (more reliable than names with emojis)
TABLE_ACCOUNTS         = "tblbj1r7Ty7ZDckYA"
TABLE_CONTENT          = "tblYJ1Q07A1R9UAsq"
TABLE_POSTING_SCHEDULE = "tblGOErjZ39deFM29"

REDDIT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cookie":          REDDIT_COOKIE or "intl_splash=false",
    "sec-ch-ua":        '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    "sec-ch-ua-mobile":   "?0",
    "sec-ch-ua-platform":  '"Windows"',
    "sec-fetch-dest":  "empty",
    "sec-fetch-mode":  "cors",
    "sec-fetch-site":  "same-origin",
}

MONTHS_ES = {
    1: "enero",    2: "febrero",   3: "marzo",     4: "abril",
    5: "mayo",     6: "junio",     7: "julio",     8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


# --- REDDIT HELPERS ---

def reddit_get(url: str):
    sep = "&" if "?" in url else "?"
    full_url = url + sep + "raw_json=1"
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    for attempt in range(3):
        try:
            time.sleep(2)
            r = requests.get(full_url, headers=REDDIT_HEADERS, proxies=proxies, timeout=15)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            print(f"  [HTTP {r.status_code}] attempt {attempt+1}/3")
        except requests.RequestException as e:
            print(f"  [error] attempt {attempt+1}/3: {e}")
        time.sleep(3)
    return None


def format_date_es(utc_timestamp: float) -> str:
    dt = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
    return f"{dt.day} de {MONTHS_ES[dt.month]} de {dt.year} {dt.hour:02d}:{dt.minute:02d}"


def to_iso(utc_timestamp: float) -> str:
    dt = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def get_user_about(username: str):
    data = reddit_get(f"https://www.reddit.com/user/{username}/about.json")
    if data is None:
        return None
    return data.get("data")


def get_user_submissions(username: str) -> list:
    data = reddit_get(
        f"https://www.reddit.com/user/{username}/submitted.json?sort=new&limit=100"
    )
    if not data:
        return []
    return [item["data"] for item in data["data"]["children"]]


def get_user_comments(username: str) -> list:
    data = reddit_get(
        f"https://www.reddit.com/user/{username}/comments.json?sort=new&limit=100"
    )
    if not data:
        return []
    return [item["data"] for item in data["data"]["children"]]


def count_last_24h(items: list) -> int:
    cutoff = time.time() - 86400
    return sum(1 for item in items if item.get("created_utc", 0) > cutoff)


def find_post_by_title(submissions: list, search_title: str):
    target = search_title.lower().strip()
    for post in submissions:
        if post.get("title", "").lower().strip() == target:
            return post
    return None


def clean_username(raw: str) -> str:
    return raw.strip().lstrip("u/")


def pick(val) -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        return str(val[0]) if val else ""
    return str(val)


# --- STEP 1: UPDATE ACCOUNTS ---

def update_accounts(api: Api):
    table = api.table(AIRTABLE_BASE_ID, TABLE_ACCOUNTS)
    records = table.all()
    print(f"[Accounts] {len(records)} account(s) found")

    for rec in records:
        f = rec["fields"]
        raw_username = f.get("Reddit Username", "").strip()
        if not raw_username:
            continue

        username = clean_username(raw_username)
        print(f"  Scraping u/{username}...")

        about = get_user_about(username)

        if about is None:
            print(f"  -> BANNED or not found -- marking Status=Banned")
            table.update(rec["id"], {"Status": "Banned"})
            continue

        subreddit_data = about.get("subreddit") or {}
        followers = subreddit_data.get("subscribers", 0)

        submissions = get_user_submissions(username)
        comments    = get_user_comments(username)

        posts_24h      = count_last_24h(submissions)
        comments_total = len(comments)

        updates = {
            "Account Age":        format_date_es(about["created_utc"]),
            "Followers":          followers,
            "Posts Made ( 24 h)": posts_24h,
            "Post Karma":         about.get("link_karma", 0),
            "Comments Made":      comments_total,
            "Comment Karma":      about.get("comment_karma", 0),
            "Status":             "Active",
        }

        table.update(rec["id"], updates)
        print(f"  Status=Active, post_karma={updates['Post Karma']}, comment_karma={updates['Comment Karma']}, followers={followers}, posts_24h={posts_24h}")


# --- STEP 2: CONTENT -> POSTING SCHEDULE ---

def process_content(api: Api):
    content_table = api.table(AIRTABLE_BASE_ID, TABLE_CONTENT)
    ps_table      = api.table(AIRTABLE_BASE_ID, TABLE_POSTING_SCHEDULE)

    # Build set of banned usernames -- these will be skipped entirely
    accounts_table = api.table(AIRTABLE_BASE_ID, TABLE_ACCOUNTS)
    banned = set()
    for acc in accounts_table.all():
        if acc["fields"].get("Status") == "Banned":
            raw = acc["fields"].get("Reddit Username", "").strip()
            if raw:
                banned.add(clean_username(raw).lower())
    if banned:
        print(f"[Content] Banned accounts skipped: {banned}")

    all_content = content_table.all()
    all_content.sort(
        key=lambda r: int(r["fields"].get("ID  🤳 Content") or 0)
    )

    all_ps = ps_table.all()
    ps_by_content_id = {
        str(r["fields"].get("ID 📈 Posting Schedule", "")).strip(): r
        for r in all_ps
    }

    print(f"[Content] {len(all_content)} row(s), {len(all_ps)} PS row(s) exist")

    for rec in all_content:
        f = rec["fields"]

        content_id = str(f.get("ID  🤳 Content", "")).strip()
        if not content_id or content_id == "0":
            continue

        # Only process rows with Status = "post"
        status = f.get("Status", "Pending")
        if status != "post":
            print(f"  ID {content_id}: Status='{status}' -- skipping")
            continue

        titulo = f.get("titulo", "").strip()
        if not titulo:
            print(f"  ID {content_id}: no titulo -- skipping")
            continue

        reddit_username = pick(f.get("Reddit Username (from 👤 Accounts) 2", ""))
        if not reddit_username:
            print(f"  ID {content_id}: no Reddit username -- skipping")
            continue

        username = clean_username(reddit_username)

        if username.lower() in banned:
            print(f"  ID {content_id}: u/{username} is Banned -- setting Status=STOP")
            content_table.update(rec["id"], {"Status": "STOP"})
            continue

        print(f"  -- Content ID {content_id}: '{titulo}' (u/{username}) --")

        submissions = get_user_submissions(username)
        post = find_post_by_title(submissions, titulo)

        if post:
            print(f"  Post found! score={post.get('score',0)}, comments={post.get('num_comments',0)}")
            publicado    = "Sí"
            fecha_pub    = to_iso(post["created_utc"])
            url_post     = "https://www.reddit.com" + post.get("permalink", "")
            up_votes     = post.get("score", 0)
            down_votes   = post.get("downs", 0)
            num_comments = post.get("num_comments", 0)
        else:
            print(f"  Post not found")
            publicado    = "No"
            fecha_pub    = None
            url_post     = None
            up_votes     = None
            down_votes   = None
            num_comments = None

        ps_fields = {
            "ID 📈 Posting Schedule":                                  content_id,
            "PUBLICADO?":                                                     publicado,
            "👤REDDIT NAMAE (from 🤳 Content)":                reddit_username,
            "USER NAME (from 👤 Accounts) (from 🤳 Content)":  pick(f.get("USER NAME (from 👤 Accounts)")),
            "Model Name (from 👤 Accounts) (from 🤳 Content)": pick(f.get("Model Name (from 👤 Accounts)")),
            "titulo (from 🤳 Content)":                               titulo,
            "flair (from 🤳 Content)":                                pick(f.get("flair")),
            "metodo (from 🤳 Content)":                               pick(f.get("metodo")),
            "bann? (from 🤳 Content)":                                pick(f.get("bann?")),
        }

        if fecha_pub:
            ps_fields["Fecha de publicacion"] = fecha_pub
        if url_post:
            ps_fields["URL del post"] = url_post
        if up_votes is not None:
            ps_fields["UP votes normal"] = up_votes
        if down_votes is not None:
            ps_fields["votos malos"] = down_votes
        if num_comments is not None:
            ps_fields["num. post coment"] = num_comments

        if content_id in ps_by_content_id:
            existing = ps_by_content_id[content_id]
            ps_table.update(existing["id"], ps_fields)
            print(f"  PS row UPDATED")
        else:
            ps_table.create(ps_fields)
            print(f"  PS row CREATED")

        if post:
            content_table.update(rec["id"], {"publicado?": True})
            print(f"  Content publicado? = True")


# --- MAIN ---

def main():
    print("=" * 50)
    print("Reddit Posting Tracker")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    api = Api(AIRTABLE_API_KEY)

    if PROXY_URL:
        try:
            proxies = {"http": PROXY_URL, "https": PROXY_URL}
            r = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=10)
            print(f"Proxy active — outbound IP: {r.json().get('origin')}")
        except Exception as e:
            print(f"Proxy check failed: {e}")
    else:
        print("No proxy configured — using direct connection")

    print("\n[Step 1] Updating Account stats from Reddit...")
    update_accounts(api)

    print("\n[Step 2] Processing Content -> Posting Schedule...")
    process_content(api)

    print("\n" + "=" * 50)
    print("Done!")
    print("=" * 50)


if __name__ == "__main__":
    main()
