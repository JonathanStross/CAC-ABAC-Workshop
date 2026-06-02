#!/usr/bin/env python3
"""
DAC Workshop Leaderboard
========================
Runs on the off-grid server at http://10.8.0.1:9000

Participants register, then submit completion codes per level.
Leaderboard auto-refreshes and shows live rankings.

Run:
    pip install flask
    python3 leaderboard.py

Or via Docker:
    docker build -t dac-leaderboard .
    docker run -d -p 9000:9000 --name dac-leaderboard dac-leaderboard
"""

from flask import Flask, request, redirect, render_template_string, jsonify, Response, send_file
import sqlite3, hashlib, json, os, re, time, hmac, base64
from datetime import datetime
try:
    import markdown as _markdown_lib
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
from sap_user import create_workshop_user, user_exists, lock_sap_user, unlock_sap_user, kick_sap_user, delete_sap_user, SAP_AVAILABLE
from wireguard_peer import create_customer_peer, remove_customer_peer, WG_AVAILABLE

app = Flask(__name__)
DB = "/data/leaderboard.db"
CONFIG_FILE = "/data/level_codes.json"
LOGO_PATH = os.path.join(os.path.dirname(__file__), "pathlock-logo.svg")
# Level guide .md files — lives one directory above the leaderboard/ folder
HANDOUTS_DIR = os.path.join(os.path.dirname(__file__), "..", "handouts")

# ---------------------------------------------------------------------------
# Security config — set via environment variables
# ---------------------------------------------------------------------------

# Access code required to reach the /register form.
# Set to any memorable word you'll announce at the start of the session.
# Example:  REGISTER_CODE=meridian2026
REGISTER_CODE    = os.environ.get("REGISTER_CODE", "").strip()

# Shared cookie name and helper — used by /register and /levels/* gates
_ACCESS_COOKIE = "wb_access"

def _access_token() -> str:
    """HMAC token stored in the access cookie once the code is verified."""
    return hashlib.sha256(REGISTER_CODE.encode()).hexdigest() if REGISTER_CODE else ""

def _has_access_cookie() -> bool:
    """Return True if the browser has a valid access cookie (or no code is configured)."""
    if not REGISTER_CODE:
        return True
    token = request.cookies.get(_ACCESS_COOKIE, "")
    return hmac.compare_digest(token, _access_token())

# HTTP Basic Auth for /admin routes.
# ADMIN_USER: email / username accepted  (default: admin)
# ADMIN_PASSWORD: password
ADMIN_USER       = os.environ.get("ADMIN_USER",     "admin").strip()
ADMIN_PASSWORD   = os.environ.get("ADMIN_PASSWORD", "").strip()

# SAP connection details shown on the registration confirmation page
SAP_HOST         = os.environ.get("SAP_HOST",    "10.8.0.1")
SAP_SYSNR        = os.environ.get("SAP_SYSNR",   "00")
SAP_CLIENT       = os.environ.get("SAP_CLIENT",  "001")
# SAP GUI port: 32<SYSNR>  (e.g. SYSNR=00 → 3200)
_sap_port        = f"32{SAP_SYSNR.zfill(2)}"
SAP_CONN_DISPLAY = f"{SAP_HOST}  |  Instance {SAP_SYSNR}  |  Client {SAP_CLIENT}"

# Simple in-memory rate limiter  {ip: [timestamp, ...]}
# Max MAX_REG_PER_HOUR registration POSTs per IP per hour
MAX_REG_PER_HOUR = 5
_reg_attempts: dict[str, list[float]] = {}

def _check_rate_limit(ip: str) -> bool:
    """Return True if the IP is within limits, False if it should be blocked."""
    now = time.time()
    attempts = [t for t in _reg_attempts.get(ip, []) if now - t < 3600]
    _reg_attempts[ip] = attempts
    if len(attempts) >= MAX_REG_PER_HOUR:
        return False
    _reg_attempts[ip].append(now)
    return True

def _require_admin_auth():
    """Return a 401 response if ADMIN_PASSWORD is set and credentials don't match."""
    if not ADMIN_PASSWORD:
        return None  # auth disabled — VPN-only access assumed
    auth = request.authorization
    if auth and hmac.compare_digest(auth.username, ADMIN_USER) and hmac.compare_digest(auth.password, ADMIN_PASSWORD):
        return None
    return Response(
        "Admin access denied.",
        401,
        {"WWW-Authenticate": 'Basic realm="Workshop Admin"'})

def _sanitize_text(value: str, max_len: int) -> str:
    """Strip whitespace, remove control characters, enforce max length."""
    value = value.strip()
    value = re.sub(r'[\x00-\x1f\x7f]', '', value)   # strip control chars
    return value[:max_len]


def _detect_shenanigans(fields: dict[str, str]) -> str | None:
    """
    Check all input fields for injection attempts, script tags, and general
    nonsense. Returns a funny error message string if something smells off,
    or None if everything looks fine.
    """
    combined = " ".join(fields.values()).lower()

    sql_patterns = [
        r"('|\")\s*or\s+('|\")?\d",          # ' OR '1
        r"('|\")\s*or\s+\w+=\w+",             # ' OR a=a
        r"--\s",                               # SQL comment --
        r";\s*(drop|delete|insert|update|select|alter|create|truncate)\b",
        r"\bunion\b.+\bselect\b",
        r"\bselect\b.+\bfrom\b",
        r"xp_cmdshell",
        r"information_schema",
        r"sleep\s*\(\s*\d",
        r"waitfor\s+delay",
        r"1\s*=\s*1",
        r"benchmark\s*\(",
    ]
    script_patterns = [
        r"<\s*script",
        r"javascript\s*:",
        r"on\w+\s*=\s*[\"']",                  # onclick= onerror= etc
        r"<\s*iframe",
        r"<\s*img[^>]+onerror",
        r"eval\s*\(",
        r"document\s*\.\s*cookie",
        r"window\s*\.\s*location",
    ]
    path_patterns = [
        r"\.\./",                              # path traversal
        r"/etc/passwd",
        r"/proc/self",
        r"cmd\.exe",
        r"powershell",
    ]

    import random
    sql_jokes = [
        "Nice try, Bobby Tables. Your parents must be so proud.",
        "'; DROP TABLE participants; --  ...was almost our favourite username.",
        "SQL injection detected. Our database laughed, then reported you to the DPA.",
        "Cute query. Unfortunately we use parameterised statements. Go touch grass.",
        "UNION SELECT null, 'nope', null, null — counted the columns and everything. Impressive. Still no.",
        "Our SQLite database would like to inform you that it has feelings too.",
    ]
    xss_jokes = [
        "<script>alert('caught you')</script> — yes we see it, no it doesn't run here.",
        "XSS attempt detected. Your payload has been safely composted.",
        "Ooh, a script tag. Our Content Security Policy will frame that and hang it on the wall.",
        "Nice try. document.cookie is just an empty jar here.",
        "The <iframe> you ordered has been denied. Please try a salad instead.",
    ]
    path_jokes = [
        "../../etc/passwd — classic. It's on your CV, isn't it.",
        "Path traversal? The only path here leads to the leaderboard. You're already losing.",
        "cmd.exe not found. Have you tried turning it off and not turning it back on?",
        "We don't have a /proc/self/environ here. We barely have a self.",
    ]

    for p in sql_patterns:
        if re.search(p, combined):
            return random.choice(sql_jokes)
    for p in script_patterns:
        if re.search(p, combined):
            return random.choice(xss_jokes)
    for p in path_patterns:
        if re.search(p, combined):
            return random.choice(path_jokes)

    # SAP default / system usernames
    sap_defaults = {
        "SAP*", "DDIC", "DEVELOPER", "SAPCPIC", "TMSADM", "EARLYWATCH",
        "RFCUSER", "SOLMAN_BTC", "SM_INTERN", "SAPSYS", "SAPJSF", "SAPABC",
    }
    sap_username_val = fields.get("sap_username", "").strip().upper()
    if sap_username_val in sap_defaults:
        import random
        sap_jokes = [
            f"Nice try. {sap_username_val} is a SAP system account, not your name.",
            f"{sap_username_val}? Really? Did you think we wouldn't notice?",
            f"SAP* walks into a bar. The bartender says: 'We don't serve system users here.'",
            f"DDIC is a dictionary user, not a workshop participant. Try your own name.",
            f"Using {sap_username_val} as a username is like signing a contract as 'The Government'.",
        ]
        return random.choice(sap_jokes)

    # Suspiciously long single value
    for field, val in fields.items():
        if len(val) > 200:
            return f"That's a lot of characters for a {field}. Are you writing a novel or an exploit?"

    return None

# ---------------------------------------------------------------------------
# Static assets
# ---------------------------------------------------------------------------
@app.route("/logo")
def logo():
    return send_file(LOGO_PATH, mimetype="image/svg+xml")

# ---------------------------------------------------------------------------
# Level guide renderer — markdown files from the handouts/ directory
# ---------------------------------------------------------------------------
LEVEL_FILES = {
    0:  "level-00-orientation.md",
    1:  "level-01-pii-masking.md",
    2:  "level-02-contextual-access.md",
    3:  "level-03-scrambling.md",
    4:  "level-04-overprivileged-role.md",
    5:  "level-05-export-classification.md",
    6:  "level-06-multi-entity.md",
    7:  "level-07-fiori-masking.md",
    8:  "level-08-audit-trail.md",
    9:  "level-09-classification-framework.md",
    10: "level-10-gdpr-art30.md",
    11: "level-11-compliance-multiplier.md",
    12: "level-12-too-powerful-role.md",
    13: "level-13-red-blue-team.md",
}

LEVEL_STYLE = """
<style>
  body{font-family:'Segoe UI',sans-serif;background:#0f0f1a;color:#e0e0e0;margin:0;padding:0}
  .header{background:linear-gradient(135deg,#1a1a2e,#16213e);padding:20px 40px;border-bottom:2px solid #c8102e;display:flex;align-items:center;gap:24px}
  .header img{height:38px}
  .header-text h1{margin:0;color:#fff;font-size:1.3em}
  .header-text p{margin:2px 0 0;color:#aaa;font-size:0.85em}
  .container{max-width:820px;margin:30px auto;padding:0 24px 60px}
  .nav{margin-bottom:24px;font-size:0.9em}
  .nav a{color:#aaa;text-decoration:none;margin-right:16px}
  .nav a:hover{color:#fff}
  .level-badge{display:inline-block;background:#c8102e;color:#fff;border-radius:4px;padding:3px 10px;font-size:0.8em;font-weight:bold;margin-right:8px;vertical-align:middle}
  h1{color:#fff;border-bottom:1px solid #2a2a3e;padding-bottom:10px}
  h2{color:#e0e0e0;margin-top:36px}
  h3{color:#ccc}
  p{line-height:1.7;color:#ccc}
  a{color:#2ecc71}
  a:hover{color:#27ae60}
  code{background:#1a1a2e;padding:2px 6px;border-radius:3px;font-size:0.9em;color:#7ec8e3}
  pre{background:#1a1a2e;padding:16px;border-radius:6px;overflow-x:auto;border-left:3px solid #2ecc71}
  pre code{background:transparent;padding:0;color:#aef}
  table{width:100%;border-collapse:collapse;margin:16px 0}
  th{background:#c8102e;color:#fff;padding:8px 12px;text-align:left;font-size:0.85em}
  td{padding:8px 12px;border-bottom:1px solid #2a2a3e;color:#ccc}
  tr:hover td{background:#1a1a2e}
  blockquote{border-left:3px solid #c8102e;margin:16px 0;padding:10px 16px;background:#1a1a2e;color:#aaa;border-radius:0 6px 6px 0}
  blockquote p{margin:0;color:#ccc}
  hr{border:none;border-top:1px solid #2a2a3e;margin:28px 0}
  .hint-box{background:#1a2a1a;border:1px solid #2ecc71;border-radius:6px;padding:14px 18px;margin:16px 0}
  .warn-box{background:#2a1a0a;border:1px solid #f39c12;border-radius:6px;padding:14px 18px;margin:16px 0}
  .level-nav{display:flex;justify-content:space-between;margin-top:40px;padding-top:20px;border-top:1px solid #2a2a3e}
  .level-nav a{background:#1a1a2e;border:1px solid #3a3a5e;padding:10px 18px;border-radius:6px;color:#aaa;text-decoration:none;font-size:0.9em}
  .level-nav a:hover{background:#2a2a3e;color:#fff}
</style>
"""

@app.route("/levels/")
@app.route("/levels")
def levels_index():
    if not _has_access_cookie():
        return redirect("/register")
    codes = load_codes()
    items = []
    for lvl_key, info in codes.items():
        n = int(lvl_key[1:])
        available = n in LEVEL_FILES and os.path.exists(
            os.path.join(HANDOUTS_DIR, LEVEL_FILES[n]))
        items.append((n, lvl_key, info["title"], info["points"], available))
    items.sort(key=lambda x: x[0])
    rows = ""
    for n, key, title, pts, avail in items:
        if avail:
            link = f"<a href='/levels/{n}' style='color:#2ecc71'>{key} — {title}</a>"
        else:
            link = f"<span style='color:#555'>{key} — {title} <em style='font-size:0.8em'>(coming soon)</em></span>"
        rows += f"<tr><td>{link}</td><td style='color:#aaa'>{pts} pts</td></tr>"
    return f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>Level Guides</title>{LEVEL_STYLE}</head>
<body>
  <div class='header'><img src='/logo' alt='Pathlock'>
    <div class='header-text'><h1>Meridian AG — Level Guides</h1><p>DAC / ABAC Workshop</p></div>
  </div>
  <div class='container'>
    <div class='nav'><a href='/'>← Leaderboard</a><a href='/submit'>Submit Code</a></div>
    <h1>Workshop Levels</h1>
    <table><tr><th>Level</th><th>Points</th></tr>{rows}</table>
  </div>
</body></html>"""

@app.route("/levels/<int:level_num>")
def level_guide(level_num):
    if not _has_access_cookie():
        return redirect("/register")
    if level_num not in LEVEL_FILES:
        return "Level not found.", 404
    md_path = os.path.join(HANDOUTS_DIR, LEVEL_FILES[level_num])
    if not os.path.exists(md_path):
        return f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>Level {level_num}</title>{LEVEL_STYLE}</head>
<body>
  <div class='header'><img src='/logo' alt='Pathlock'>
    <div class='header-text'><h1>Level {level_num}</h1><p>Guide coming soon</p></div>
  </div>
  <div class='container'>
    <div class='nav'><a href='/levels'>← All Levels</a><a href='/'>Leaderboard</a></div>
    <p style='color:#666;padding:40px 0;text-align:center'>This level guide hasn't been published yet. Check back soon.</p>
  </div>
</body></html>""", 404
    with open(md_path, encoding="utf-8") as f:
        md_text = f.read()
    if MARKDOWN_AVAILABLE:
        body_html = _markdown_lib.markdown(
            md_text, extensions=["tables", "fenced_code", "toc"])
    else:
        # Fallback: wrap in <pre> if markdown lib not installed
        body_html = f"<pre style='white-space:pre-wrap'>{md_text}</pre>"
    # Prev / next navigation
    prev_link = f"<a href='/levels/{level_num-1}'>← Level {level_num-1}</a>" if level_num > 0 else "<span></span>"
    next_link = f"<a href='/levels/{level_num+1}'>Level {level_num+1} →</a>" if (level_num+1) in LEVEL_FILES else "<span></span>"
    codes = load_codes()
    key = f"L{level_num}"
    title = codes.get(key, {}).get("title", f"Level {level_num}")
    return f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>Level {level_num} — {title}</title>{LEVEL_STYLE}</head>
<body>
  <div class='header'><img src='/logo' alt='Pathlock'>
    <div class='header-text'>
      <h1><span class='level-badge'>L{level_num}</span>{title}</h1>
      <p>Meridian AG Audit Remediation &nbsp;|&nbsp; Pathlock DAC/ABAC Workshop</p>
    </div>
  </div>
  <div class='container'>
    <div class='nav'><a href='/levels'>← All Levels</a><a href='/'>Leaderboard</a><a href='/submit'>Submit Code</a></div>
    {body_html}
    <div class='level-nav'>{prev_link}{next_link}</div>
  </div>
</body></html>"""

# ---------------------------------------------------------------------------
# Level codes config — instructor sets these before the session
# Edit level_codes.json or set env var LEVEL_CODES_FILE
# ---------------------------------------------------------------------------
DEFAULT_CODES = {
    "L0":  {"code": "SET_BEFORE_SESSION", "points": 100, "title": "Orientation"},
    "L1":  {"code": "SET_BEFORE_SESSION", "points": 100, "title": "PII Masking"},
    "L2":  {"code": "SET_BEFORE_SESSION", "points": 100, "title": "Contextual Access"},
    "L3":  {"code": "SET_BEFORE_SESSION", "points": 100, "title": "Scrambling"},
    "L4":  {"code": "SET_BEFORE_SESSION", "points": 150, "title": "Overprivileged Role"},
    "L5":  {"code": "SET_BEFORE_SESSION", "points": 150, "title": "Export Block + Classification"},
    "L6":  {"code": "SET_BEFORE_SESSION", "points": 175, "title": "Multi-Entity ABAC"},
    "L7":  {"code": "SET_BEFORE_SESSION", "points": 175, "title": "Fiori/UI5 Masking"},
    "L8":  {"code": "SET_BEFORE_SESSION", "points": 175, "title": "Audit Trail"},
    "L9":  {"code": "SET_BEFORE_SESSION", "points": 200, "title": "Classification Framework"},
    "L10": {"code": "SET_BEFORE_SESSION", "points": 75,  "title": "GDPR Art.30 Report"},
    "L11": {"code": "SET_BEFORE_SESSION", "points": 75,  "title": "Compliance Multiplier"},
    "L12": {"code": "SET_BEFORE_SESSION", "points": 75,  "title": "Too Powerful Role"},
    "L13": {"code": "SET_BEFORE_SESSION", "points": 100, "title": "Red vs Blue Team"},
}

SPEED_BONUS = {1: 50, 2: 25, 3: 10}  # 1st/2nd/3rd place bonus per level
WRONG_PENALTY = 5

# ---------------------------------------------------------------------------
# DB setup
# ---------------------------------------------------------------------------
def get_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS participants (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            sap_username  TEXT NOT NULL UNIQUE,
            company       TEXT,
            sap_created   INTEGER DEFAULT 0,
            wg_ip         TEXT,
            wg_conf       TEXT,
            registered_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS submissions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            participant  TEXT NOT NULL,
            level        TEXT NOT NULL,
            code         TEXT NOT NULL,
            correct      INTEGER NOT NULL,
            points       INTEGER DEFAULT 0,
            submitted_at TEXT DEFAULT (datetime('now'))
        );
    """)
    # Migrate older DBs
    existing = {row[1] for row in db.execute("PRAGMA table_info(participants)")}
    for col, typedef in [("wg_ip", "TEXT"), ("wg_conf", "TEXT"),
                         ("locked", "INTEGER DEFAULT 0"), ("kicked_at", "TEXT")]:
        if col not in existing:
            db.execute(f"ALTER TABLE participants ADD COLUMN {col} {typedef}")
    db.commit()
    db.close()

def load_codes():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return DEFAULT_CODES

def get_leaderboard():
    db = get_db()
    rows = db.execute("""
        SELECT p.name, p.sap_username, p.company,
               COALESCE(SUM(CASE WHEN s.correct=1 THEN s.points ELSE 0 END), 0) as total,
               COUNT(CASE WHEN s.correct=1 THEN 1 END) as levels_done,
               MAX(s.submitted_at) as last_submission
        FROM participants p
        LEFT JOIN submissions s ON s.participant = p.sap_username
        GROUP BY p.sap_username
        ORDER BY total DESC, last_submission ASC
    """).fetchall()
    db.close()
    return rows

def get_level_completions():
    """How many people completed each level (for speed bonus calc)"""
    db = get_db()
    rows = db.execute("""
        SELECT level, COUNT(*) as cnt
        FROM submissions WHERE correct=1
        GROUP BY level
    """).fetchall()
    db.close()
    return {r["level"]: r["cnt"] for r in rows}

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
STYLE = """
<style>
  body { font-family: 'Segoe UI', sans-serif; background: #0f0f1a; color: #e0e0e0; margin: 0; padding: 0; }
  .header { background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 24px 40px; border-bottom: 2px solid #c8102e; display: flex; align-items: center; gap: 28px; }
  .header img.logo { height: 44px; width: auto; flex-shrink: 0; }
  .header-text h1 { margin: 0; color: #fff; font-size: 1.6em; }
  .header-text p { margin: 4px 0 0; color: #aaa; font-size: 0.9em; }
  .container { max-width: 900px; margin: 30px auto; padding: 0 20px; }
  table { width: 100%; border-collapse: collapse; background: #1a1a2e; border-radius: 8px; overflow: hidden; }
  th { background: #c8102e; color: white; padding: 12px 16px; text-align: left; font-size: 0.85em; text-transform: uppercase; }
  td { padding: 12px 16px; border-bottom: 1px solid #2a2a3e; }
  tr:hover td { background: #1f1f35; }
  .rank-1 td { color: #ffd700; font-weight: bold; }
  .rank-2 td { color: #c0c0c0; }
  .rank-3 td { color: #cd7f32; }
  .badge { display: inline-block; background: #c8102e; color: white; border-radius: 4px; padding: 2px 8px; font-size: 0.75em; margin-left: 6px; }
  .badge.green { background: #2ecc71; color: #000; }
  .btn { display: inline-block; background: #c8102e; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; border: none; cursor: pointer; font-size: 1em; }
  .btn:hover { background: #a00d24; }
  .btn.secondary { background: #2a2a3e; }
  .btn.secondary:hover { background: #3a3a5e; }
  form { background: #1a1a2e; padding: 30px; border-radius: 8px; max-width: 500px; margin: 0 auto; }
  input, select { width: 100%; padding: 10px; margin: 8px 0 16px; background: #0f0f1a; border: 1px solid #3a3a5e; color: #e0e0e0; border-radius: 4px; font-size: 1em; box-sizing: border-box; }
  .msg { padding: 12px 20px; border-radius: 6px; margin-bottom: 20px; }
  .msg.ok { background: #1a3a1a; border: 1px solid #2ecc71; color: #2ecc71; }
  .msg.err { background: #3a1a1a; border: 1px solid #c8102e; color: #ff6b6b; }
  .nav { margin-bottom: 20px; }
  .nav a { color: #aaa; text-decoration: none; margin-right: 20px; }
  .nav a:hover { color: #fff; }
  .refresh-note { color: #666; font-size: 0.8em; text-align: right; margin-top: 10px; }
  .level-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; margin: 20px 0; }
  .level-cell { background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 6px; padding: 10px; text-align: center; font-size: 0.85em; }
  .level-cell.done { border-color: #2ecc71; color: #2ecc71; }
</style>
"""

LEADERBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>DAC Workshop — Leaderboard</title>
  """ + STYLE + """
</head>
<body>
  <div class="header">
    <img src="/logo" class="logo" alt="Pathlock">
    <div class="header-text">
      <h1>Meridian AG — Audit Remediation</h1>
      <p>DAC / ABAC Workshop Leaderboard &nbsp;|&nbsp; Pathlock Live Demo</p>
    </div>
  </div>
  <div class="container">
    <div class="nav">
      <a href="/">🏆 Leaderboard</a>
      <a href="/levels">📖 Levels</a>
      <a href="/register">📝 Register</a>
      <a href="/submit">🔑 Submit Code</a>
    </div>

    <div style="background:#1a1a2e;border-radius:8px;padding:24px 28px;margin-bottom:28px;border-left:4px solid #c8102e">
      <h2 style="margin:0 0 10px;color:#fff;font-size:1.2em">👋 Welcome to the Pathlock DAC/ABAC Workshop</h2>
      <p style="margin:0 0 14px;color:#ccc;line-height:1.6">
        You are part of the <strong style="color:#fff">Meridian AG audit remediation team</strong>.
        The DPA has issued a formal warning — five critical access control findings must be closed before end of day.
        Work through the levels, find the completion codes inside SAP or Pathlock, and submit them here to earn points.
      </p>
      <div style="background:#0f0f1a;border-radius:6px;padding:16px 20px;font-size:0.9em;color:#ccc;line-height:2">
        <strong style="color:#fff">How to get started:</strong><br>
        <span style="color:#2ecc71">①</span> &nbsp;Make sure you have the following installed on your <strong style="color:#fff">laptop</strong>:<br>
        <div style="margin-left:28px;margin-top:4px;margin-bottom:4px;line-height:1.8">
          &bull; &nbsp;<a href="https://www.wireguard.com/install/" target="_blank" style="color:#2ecc71">WireGuard</a> &nbsp;<span style="color:#aaa;font-size:0.9em">— VPN client (phone only if tethering)</span><br>
          &bull; &nbsp;<a href="https://support.sap.com/en/product/connectors/sapgui.html" target="_blank" style="color:#2ecc71">SAP GUI</a> &nbsp;<span style="color:#aaa;font-size:0.9em">— to work in SAP transactions</span><br>
          &bull; &nbsp;<strong style="color:#fff">Google Chrome</strong> or <strong style="color:#fff">Microsoft Edge</strong> &nbsp;<span style="color:#aaa;font-size:0.9em">— recommended for SAP Fiori / UI5 (best compatibility; Firefox also works)</span>
        </div>
        <span style="color:#2ecc71">②</span> &nbsp;Go to <a href="/register" style="color:#2ecc71">Register</a> — enter the <strong style="color:#fff">access code your instructor announced</strong>, fill in your details and choose a SAP username<br>
        <span style="color:#2ecc71">③</span> &nbsp;Download your personal <strong style="color:#fff">WireGuard VPN config</strong> from the registration confirmation page and import it into the WireGuard app<br>
        <span style="color:#2ecc71">④</span> &nbsp;Connect to the VPN, open SAP GUI or Fiori, and work through the levels — starting with <strong style="color:#fff">Level 0</strong><br>
        <span style="color:#2ecc71">⑤</span> &nbsp;Found a completion code? Submit it at <a href="/submit" style="color:#2ecc71">Submit Code</a> to claim your points and climb the leaderboard<br>
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid #2a2a3e;color:#aaa;font-size:0.9em">
          📖 &nbsp;<a href="/levels/0" style="color:#2ecc71;font-weight:bold">Click here to start with Level 0 →</a><br>
          Your instructor will also provide the SAP system address, client number, and any additional guidance.
        </div>
      </div>
    </div>

    <div id="lb-container">
      {% if rows %}
      <table id="lb-table">
        <tr>
          <th>#</th><th>Participant</th><th>SAP User</th><th>Score</th><th>Levels</th><th>Last Activity</th>
        </tr>
        {% for r in rows %}
        <tr class="rank-{{ loop.index if loop.index <= 3 else '' }}">
          <td>
            {% if loop.index == 1 %}🥇
            {% elif loop.index == 2 %}🥈
            {% elif loop.index == 3 %}🥉
            {% else %}{{ loop.index }}{% endif %}
          </td>
          <td><strong>{{ r.name }}</strong></td>
          <td style="color:#aaa;font-size:0.85em">{{ r.sap_username }}</td>
          <td><strong>{{ r.total }} pts</strong></td>
          <td>{{ r.levels_done }} / {{ total_levels }}</td>
          <td style="color:#666; font-size:0.85em">{{ r.last_submission or 'Just registered' }}</td>
        </tr>
        {% endfor %}
      </table>
      {% else %}
      <p id="lb-empty" style="text-align:center; color:#666; padding: 40px">No participants yet — be the first to register!</p>
      {% endif %}
    </div>

    <p class="refresh-note">Live &mdash; updated <span id="last-updated">just now</span></p>
  </div>

  <script>
    const TOTAL_LEVELS = {{ total_levels }};
    const MEDALS = ['🥇','🥈','🥉'];

    function esc(s) {
      return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    function renderTable(rows) {
      const container = document.getElementById('lb-container');
      if (!rows || rows.length === 0) {
        container.innerHTML = '<p style="text-align:center;color:#666;padding:40px">No participants yet — be the first to register!</p>';
        return;
      }
      let html = '<table id="lb-table"><tr><th>#</th><th>Participant</th><th>SAP User</th><th>Score</th><th>Levels</th><th>Last Activity</th></tr>';
      rows.forEach((r, i) => {
        const rank = i + 1;
        const rankClass = rank <= 3 ? 'rank-' + rank : '';
        const medal = rank <= 3 ? MEDALS[i] : rank;
        html += '<tr class="' + rankClass + '">'
          + '<td>' + medal + '</td>'
          + '<td><strong>' + esc(r.name) + '</strong></td>'
          + '<td style="color:#aaa;font-size:0.85em">' + esc(r.sap_username) + '</td>'
          + '<td><strong>' + r.total + ' pts</strong></td>'
          + '<td>' + r.levels_done + ' / ' + TOTAL_LEVELS + '</td>'
          + '<td style="color:#666;font-size:0.85em">' + esc(r.last_submission || 'Just registered') + '</td>'
          + '</tr>';
      });
      html += '</table>';
      container.innerHTML = html;
    }

    function updateTimestamp() {
      const el = document.getElementById('last-updated');
      if (el) el.textContent = new Date().toLocaleTimeString();
    }

    function poll() {
      fetch('/api/leaderboard')
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) {
          if (data) { renderTable(data.rows); updateTimestamp(); }
        })
        .catch(function() {});
    }

    setInterval(poll, 10000);
  </script>
</body>
</html>
"""


FLIP_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Really?</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #0d0d1a;
    color: #eee;
    font-family: 'Segoe UI', sans-serif;
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 1.2s cubic-bezier(.68,-0.55,.27,1.55);
  }
  body.flipped { transform: rotate(180deg); }
  .modal {
    background: #1a1a2e;
    border: 2px solid #e74c3c;
    border-radius: 16px;
    padding: 48px 56px;
    max-width: 520px;
    text-align: center;
    box-shadow: 0 0 60px rgba(231,76,60,0.4);
    animation: shake 0.5s ease 1.3s both;
  }
  @keyframes shake {
    0%,100%{transform:translateX(0)}
    20%{transform:translateX(-12px)}
    40%{transform:translateX(12px)}
    60%{transform:translateX(-8px)}
    80%{transform:translateX(8px)}
  }
  h1 { font-size: 2.4em; color: #e74c3c; margin-bottom: 16px; }
  p  { color: #aaa; font-size: 1.1em; line-height: 1.6; margin-bottom: 32px; }
  button {
    background: #2ecc71;
    color: #0d0d1a;
    border: none;
    padding: 14px 36px;
    border-radius: 8px;
    font-size: 1.1em;
    font-weight: bold;
    cursor: pointer;
    transition: background 0.2s;
  }
  button:hover { background: #27ae60; }
</style>
</head>
<body class="flipped" id="bd">
  <div class="modal">
    <h1>🙃 Joke's on you.</h1>
    <p>
      <strong style="color:#ffd700">{{ username }}</strong> is a SAP system account.<br><br>
      You tried it twice. The screen is now upside down.<br>
      This is what it feels like to be the server right now.
    </p>
    <button onclick="document.getElementById('bd').classList.remove('flipped'); setTimeout(()=>window.location='/register', 1400)">
      🫡 &nbsp;I will behave
    </button>
  </div>
</body>
</html>
"""

REGISTER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Register — DAC Workshop</title>""" + STYLE + """</head>
<body>
  <div class="header">
    <img src="/logo" class="logo" alt="Pathlock">
    <div class="header-text">
      <h1>Meridian AG — Join the Team</h1>
      <p>Register to get your personal SAP login and join the leaderboard</p>
    </div>
  </div>
  <div class="container">
    <div class="nav"><a href="/">🏆 Leaderboard</a><a href="/levels">📖 Levels</a><a href="/submit">🔑 Submit Code</a></div>
    {% if success %}
      <div class="msg ok" style="font-size:1.1em">
        <strong>✅ You're registered!</strong><br><br>

        <div style="background:#0f1f0f;border:1px solid #2ecc71;border-radius:8px;padding:16px 20px;margin-bottom:14px">
          <div style="font-size:0.8em;color:#aaa;margin-bottom:10px;text-transform:uppercase;letter-spacing:1px">Your SAP GUI connection details</div>
          <table style="background:transparent;width:100%;border-collapse:collapse">
            <tr>
              <td style="padding:6px 16px 6px 0;color:#aaa;white-space:nowrap;font-size:0.9em">Application Server</td>
              <td><strong style="color:#fff;font-size:1.1em">{{ sap_host }}</strong> <span style="color:#888;font-size:0.8em">← enter this in SAP GUI as the server address</span></td>
            </tr>
            <tr>
              <td style="padding:6px 16px 6px 0;color:#aaa;white-space:nowrap;font-size:0.9em">System Number</td>
              <td><strong style="color:#fff">{{ sap_sysnr }}</strong></td>
            </tr>
            <tr>
              <td style="padding:6px 16px 6px 0;color:#aaa;white-space:nowrap;font-size:0.9em">Client</td>
              <td><strong style="color:#fff">{{ sap_client }}</strong></td>
            </tr>
            <tr style="border-top:1px solid #1a3a1a">
              <td style="padding:10px 16px 6px 0;color:#aaa;white-space:nowrap;font-size:0.9em">Your Username</td>
              <td style="padding-top:10px"><strong style="font-size:1.3em;color:#ffd700;letter-spacing:1px">{{ sap_username }}</strong></td>
            </tr>
            <tr>
              <td style="padding:6px 16px 6px 0;color:#aaa;white-space:nowrap;font-size:0.9em">Temporary Password</td>
              <td>
                <strong id="pw-display" style="font-size:1.3em;color:#ffd700;letter-spacing:2px">{{ temp_password }}</strong>
              </td>
            </tr>
            {% if wg_ip %}
            <tr style="border-top:1px solid #1a3a1a">
              <td style="padding:10px 16px 6px 0;color:#aaa;white-space:nowrap;font-size:0.9em">Your VPN IP</td>
              <td style="padding-top:10px"><strong style="color:#2ecc71">{{ wg_ip }}</strong> <span style="color:#888;font-size:0.8em">(assigned to your WireGuard tunnel)</span></td>
            </tr>
            {% endif %}
          </table>
        </div>

        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px">
          <button onclick="copyCredentials()" id="copy-btn"
            style="background:#2a2a3e;color:#fff;border:1px solid #3a3a5e;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:0.9em">
            📋 Copy credentials
          </button>
          <button onclick="downloadCredentials()"
            style="background:#2a2a3e;color:#fff;border:1px solid #3a3a5e;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:0.9em">
            ⬇ Download as .txt
          </button>
        </div>

        <script>
          const CREDS = {
            host: "{{ sap_host }}",
            sysnr: "{{ sap_sysnr }}",
            client: "{{ sap_client }}",
            username: "{{ sap_username }}",
            password: "{{ temp_password }}",
            wg_ip: "{{ wg_ip or '' }}"
          };
          function credText() {
            return [
              "=== DAC Workshop — SAP Credentials ===",
              "",
              "SAP GUI Connection",
              "  Application Server : " + CREDS.host,
              "  System Number      : " + CREDS.sysnr,
              "  Client             : " + CREDS.client,
              "",
              "Login",
              "  Username           : " + CREDS.username,
              "  Temporary Password : " + CREDS.password,
              "",
              CREDS.wg_ip ? "VPN IP (WireGuard)   : " + CREDS.wg_ip : "",
              "",
              "NOTE: You will be prompted to change your password on first login.",
              "NOTE: First VPN connection may take up to a minute.",
            ].join("\\n");
          }
          function copyCredentials() {
            navigator.clipboard.writeText(credText()).then(function() {
              var btn = document.getElementById('copy-btn');
              btn.textContent = '✅ Copied!';
              setTimeout(function(){ btn.textContent = '📋 Copy credentials'; }, 2500);
            });
          }
          function downloadCredentials() {
            var blob = new Blob([credText()], {type: 'text/plain'});
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'sap-credentials-' + CREDS.username + '.txt';
            a.click();
          }
        </script>

        ⚠️ <strong>Write the password down now.</strong> It is shown only once and will prompt for a change on first login.
        {% if sap_warn %}
        <br><br>⚠️ <em style="color:#f39c12">{{ sap_warn }}</em>
        {% endif %}
      </div>

      {% if wg_conf %}
      <br>
      <div style="background:#1a1a2e;border:1px solid #2ecc71;border-radius:8px;padding:20px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <strong style="color:#2ecc71">📡 Your WireGuard VPN Config</strong>
          <a href="/download/{{ sap_username }}" class="btn" style="padding:6px 14px;font-size:0.85em">⬇ Download .conf</a>
        </div>
        <pre style="background:#0f0f1a;padding:16px;border-radius:6px;font-size:0.8em;overflow-x:auto;color:#aef;margin:0">{{ wg_conf }}</pre>
        <p style="color:#aaa;font-size:0.8em;margin-top:10px">
          Import this file into the WireGuard app on your laptop or phone.<br>
          Windows/Mac: <em>File → Import tunnel from file</em> &nbsp;|&nbsp;
          iOS/Android: scan QR from the WireGuard app on the server.<br>
          <span style="color:#f39c12">⏱ First connection may take up to a minute — the SAP system needs a moment to wake up after a new peer connects.</span>
        </p>
      </div>
      {% elif wg_warn %}
      <br><div class="msg err">⚠️ {{ wg_warn }}</div>
      {% endif %}

      <br><a href="/" class="btn">Go to Leaderboard →</a>
    {% else %}
      {% if msg %}<div class="msg {{ msg_type }}">{{ msg }}</div>{% endif %}
      <form method="POST">
        <h2 style="margin-top:0">Create your account</h2>
        <label>Full name <span style="color:#aaa;font-size:0.85em">(shown on leaderboard)</span></label>
        <input type="text" name="name" placeholder="e.g. Anna Müller" required value="{{ form_name or '' }}">
        <label>Email address <span style="color:#aaa;font-size:0.85em">(not shown publicly)</span></label>
        <input type="email" name="email" placeholder="you@example.com" required value="{{ form_email or '' }}">
        <label>SAP username <span style="color:#aaa;font-size:0.85em">(max 12 chars, letters/digits only — this becomes your SAP login)</span></label>
        <input type="text" name="sap_username" placeholder="e.g. AMUELLER" maxlength="12"
               pattern="[A-Za-z0-9_]+" title="Letters, digits and underscore only"
               required value="{{ form_sap or '' }}" style="text-transform:uppercase;letter-spacing:1px">
        <label>Company <span style="color:#aaa;font-size:0.85em">(optional)</span></label>
        <input type="text" name="company" placeholder="e.g. Contoso AG" value="{{ form_company or '' }}">
        <button type="submit" class="btn">Register & create SAP user →</button>
        {% if not sap_available %}
        <p style="color:#f39c12;margin-top:16px;font-size:0.85em">
          ⚠️ SAP auto-provisioning is offline — your account will be created on the leaderboard
          but your instructor will set up your SAP login manually.
        </p>
        {% endif %}
      </form>
    {% endif %}
  </div>
</body>
</html>
"""

SUBMIT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Submit Code</title>""" + STYLE + """</head>
<body>
  <div class="header">
    <img src="/logo" class="logo" alt="Pathlock">
    <div class="header-text">
      <h1>Submit Completion Code</h1>
      <p>Enter the code you found in SAP / Pathlock to claim your points</p>
    </div>
  </div>
  <div class="container">
    <div class="nav"><a href="/">🏆 Leaderboard</a><a href="/levels">📖 Levels</a><a href="/register">📝 Register</a></div>
    {% if msg %}<div class="msg {{ msg_type }}">{{ msg }}</div>{% endif %}
    <form method="POST">
      <h2 style="margin-top:0">Level Completion</h2>
      <label>Your SAP username</label>
      <input type="text" name="name" required placeholder="e.g. AMUELLER" style="text-transform:uppercase;letter-spacing:1px">
      <label>Level</label>
      <select name="level">
        {% for lvl, info in levels.items() %}
        <option value="{{ lvl }}">{{ lvl }} — {{ info.title }}</option>
        {% endfor %}
      </select>
      <label>Completion code</label>
      <input type="text" name="code" required placeholder="Enter the code from SAP/Pathlock">
      <button type="submit" class="btn">Submit →</button>
    </form>
  </div>
</body>
</html>
"""

ACCESS_CODE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Register — DAC Workshop</title>""" + STYLE + """</head>
<body>
  <div class="header">
    <img src="/logo" class="logo" alt="Pathlock">
    <div class="header-text">
      <h1>Meridian AG — Join the Team</h1>
      <p>Workshop participant registration</p>
    </div>
  </div>
  <div class="container">
    <div class="nav"><a href="/">🏆 Leaderboard</a><a href="/register">📝 Register</a></div>
    {% if error %}<div class="msg err">{{ error }}</div>{% endif %}
    <form method="POST">
      <h2 style="margin-top:0">🔐 Enter access code</h2>
      <p style="color:#aaa;margin-top:0">Your instructor shared an access code at the start of the session.</p>
      <label>Access code</label>
      <input type="password" name="access_code" placeholder="Enter code" required autofocus>
      <button type="submit" class="btn">Continue →</button>
    </form>
  </div>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    rows = get_leaderboard()
    codes = load_codes()
    return render_template_string(LEADERBOARD_TEMPLATE,
        rows=rows,
        total_levels=len(codes))

@app.route("/api/leaderboard")
def api_leaderboard():
    rows = get_leaderboard()
    codes = load_codes()
    return jsonify({
        "total_levels": len(codes),
        "rows": [dict(r) for r in rows],
    })

@app.route("/register", methods=["GET", "POST"])
def register():
    ip = request.remote_addr or "unknown"

    # ---- Step 1: access code gate ------------------------------------------
    # If REGISTER_CODE is set, the user must first POST the correct code.
    # We store a simple session token in a cookie once the code is verified.
    # Reuses the module-level _has_access_cookie() / _access_token() helpers.

    # POST with only access_code field → validate the gate
    if request.method == "POST" and "access_code" in request.form and "name" not in request.form:
        entered = request.form.get("access_code", "").strip()
        if REGISTER_CODE and hmac.compare_digest(
                hashlib.sha256(entered.encode()).hexdigest(),
                _access_token()):
            # Correct — set cookie and show the registration form
            resp = Response(render_template_string(REGISTER_TEMPLATE,
                success=False, msg=None, msg_type="ok", sap_available=SAP_AVAILABLE,
                form_name="", form_email="", form_sap="", form_company=""))
            resp.set_cookie(_ACCESS_COOKIE, _access_token(),
                max_age=86400, httponly=True, samesite="Lax")
            return resp
        return render_template_string(ACCESS_CODE_TEMPLATE,
            error="Incorrect access code. Check with your instructor.")

    # GET or unauthed → show gate or form depending on cookie
    if request.method == "GET":
        if not _has_access_cookie():
            return render_template_string(ACCESS_CODE_TEMPLATE, error=None)
        return render_template_string(REGISTER_TEMPLATE,
            success=False, msg=None, msg_type="ok", sap_available=SAP_AVAILABLE,
            form_name="", form_email="", form_sap="", form_company="")

    # ---- Step 2: actual registration POST ----------------------------------
    if not _has_access_cookie():
        return render_template_string(ACCESS_CODE_TEMPLATE,
            error="Session expired — please enter the access code again.")

    # Rate limiting
    if not _check_rate_limit(ip):
        return render_template_string(REGISTER_TEMPLATE,
            success=False,
            msg="Too many registration attempts from your IP. Please wait a while.",
            msg_type="err", sap_available=SAP_AVAILABLE,
            form_name="", form_email="", form_sap="", form_company="")

    # ---- Sanitize inputs ---------------------------------------------------
    raw_fields = {
        "name":         request.form.get("name", ""),
        "email":        request.form.get("email", ""),
        "sap_username": request.form.get("sap_username", ""),
        "company":      request.form.get("company", ""),
    }
    name         = _sanitize_text(raw_fields["name"], 80)
    email        = _sanitize_text(raw_fields["email"].lower(), 120)
    sap_username = _sanitize_text(raw_fields["sap_username"].upper(), 12)
    company      = _sanitize_text(raw_fields["company"], 80)

    # ---- Shenanigans check — runs on raw input before sanitization ---------
    funny = _detect_shenanigans(raw_fields)
    if funny:
        app.logger.warning("Shenanigans detected from %s: %s", ip, raw_fields)
        # Count SAP-default-user attempts via cookie — flip the screen on 2nd try
        sap_default_cookie = "sap_naughty"
        prior_attempts = int(request.cookies.get(sap_default_cookie, "0"))
        sap_defaults = {"SAP*","DDIC","DEVELOPER","SAPCPIC","TMSADM","EARLYWATCH",
                        "RFCUSER","SOLMAN_BTC","SM_INTERN","SAPSYS","SAPJSF","SAPABC"}
        is_sap_default = raw_fields.get("sap_username","").strip().upper() in sap_defaults
        if is_sap_default and prior_attempts >= 1:
            resp = Response(render_template_string(FLIP_TEMPLATE,
                username=raw_fields.get("sap_username","").strip().upper()))
            resp.set_cookie(sap_default_cookie, "0", max_age=3600, httponly=True)
            return resp
        resp = Response(render_template_string(REGISTER_TEMPLATE,
            success=False, msg=funny, msg_type="err", sap_available=SAP_AVAILABLE,
            form_name="", form_email="", form_sap="", form_company=""))
        if is_sap_default:
            resp.set_cookie(sap_default_cookie, str(prior_attempts + 1), max_age=3600, httponly=True)
        return resp

    # ---- Validation --------------------------------------------------------
    def err(msg):
        return render_template_string(REGISTER_TEMPLATE,
            success=False, msg=msg, msg_type="err", sap_available=SAP_AVAILABLE,
            form_name=name, form_email=email, form_sap=sap_username, form_company=company)

    if not name:
        return err("Full name is required.")
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return err("A valid email address is required.")
    if not sap_username:
        return err("SAP username is required.")
    if len(sap_username) < 3:
        return err("SAP username must be at least 3 characters.")
    if len(sap_username) > 12:
        return err("SAP username must be at most 12 characters.")
    if not re.match(r'^[A-Z0-9_]+$', sap_username):
        return err("SAP username may only contain letters, digits and underscore.")

    # ---- Check duplicates --------------------------------------------------
    db = get_db()
    if db.execute("SELECT 1 FROM participants WHERE email=?", (email,)).fetchone():
        db.close()
        return err("That email address is already registered.")
    if db.execute("SELECT 1 FROM participants WHERE sap_username=?", (sap_username,)).fetchone():
        db.close()
        return err(f"SAP username '{sap_username}' is already taken — choose another.")

    # ---- Check SAP live ----------------------------------------------------
    if SAP_AVAILABLE and user_exists(sap_username):
        db.close()
        return err(f"SAP user '{sap_username}' already exists on the system — choose another username.")

    # ---- Create SAP user ---------------------------------------------------
    sap_ok, temp_password, sap_error = create_workshop_user(
        sap_username=sap_username,
        first_name=name.split()[0] if name.split() else name,
        last_name=" ".join(name.split()[1:]) if len(name.split()) > 1 else "",
        email=email,
    )

    sap_warn = None
    if not sap_ok:
        sap_warn = f"SAP user could not be created automatically: {sap_error}. Your instructor will create it manually."
        temp_password = "(see instructor)"

    # ---- Create WireGuard peer ---------------------------------------------
    wg_ok, wg_ip, wg_conf, wg_error = create_customer_peer(display_name=name)

    wg_warn = None
    if not wg_ok:
        wg_warn = f"VPN config could not be created automatically: {wg_error}. Your instructor will provide your WireGuard config."
        wg_ip = None
        wg_conf = None

    # ---- Save to DB --------------------------------------------------------
    try:
        db.execute(
            "INSERT INTO participants (name, email, sap_username, company, sap_created, wg_ip, wg_conf) VALUES (?,?,?,?,?,?,?)",
            (name, email, sap_username, company, 1 if sap_ok else 0, wg_ip, wg_conf))
        db.commit()
    except sqlite3.IntegrityError as exc:
        db.close()
        return err(f"Registration failed: {exc}")
    db.close()

    return render_template_string(REGISTER_TEMPLATE,
        success=True,
        sap_username=sap_username,
        temp_password=temp_password,
        sap_warn=sap_warn,
        sap_host=SAP_HOST,
        sap_sysnr=SAP_SYSNR,
        sap_client=SAP_CLIENT,
        wg_ip=wg_ip,
        wg_conf=wg_conf,
        wg_warn=wg_warn,
        sap_available=SAP_AVAILABLE)

@app.route("/download/<sap_username>")
def download_wg_conf(sap_username):
    """Serve the WireGuard .conf for a registered participant."""
    db = get_db()
    row = db.execute(
        "SELECT wg_conf, name FROM participants WHERE sap_username=?",
        (sap_username.upper(),)).fetchone()
    db.close()
    if not row or not row["wg_conf"]:
        return "No WireGuard config found for this user.", 404
    filename = f"{sap_username.upper()}_vpn.conf"
    return Response(
        row["wg_conf"],
        mimetype="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.route("/submit", methods=["GET", "POST"])
def submit():
    msg, msg_type = None, "ok"
    codes = load_codes()
    if request.method == "POST":
        sap_username = request.form.get("name", "").strip().upper()
        level = request.form.get("level", "").strip()
        code  = request.form.get("code", "").strip().upper()

        # Check participant exists
        db = get_db()
        participant = db.execute("SELECT * FROM participants WHERE sap_username=?", (sap_username,)).fetchone()
        if not participant:
            msg, msg_type = f"SAP username '{sap_username}' not found. Please register first.", "err"
            db.close()
            return render_template_string(SUBMIT_TEMPLATE, msg=msg, msg_type=msg_type, levels=codes)

        if participant["locked"]:
            msg, msg_type = "Your account has been locked by the instructor. Please raise your hand.", "err"
            db.close()
            return render_template_string(SUBMIT_TEMPLATE, msg=msg, msg_type=msg_type, levels=codes)

        # Check not already submitted correctly
        already = db.execute(
            "SELECT * FROM submissions WHERE participant=? AND level=? AND correct=1",
            (sap_username, level)).fetchone()
        if already:
            msg, msg_type = f"You already completed {level}! No double points.", "err"
            db.close()
            return render_template_string(SUBMIT_TEMPLATE, msg=msg, msg_type=msg_type, levels=codes)

        # Validate code
        correct_code = codes.get(level, {}).get("code", "").upper()
        base_points  = codes.get(level, {}).get("points", 100)
        correct = (code == correct_code)

        if correct:
            completions = get_level_completions()
            position = (completions.get(level, 0)) + 1
            bonus = SPEED_BONUS.get(position, 0)
            total_pts = base_points + bonus
            bonus_msg = f" +{bonus} speed bonus! 🚀" if bonus else ""
            msg = f"✅ Correct! +{base_points} points{bonus_msg} for {level}."
        else:
            total_pts = -WRONG_PENALTY
            msg, msg_type = f"❌ Wrong code. -{WRONG_PENALTY} points. Try again.", "err"

        db.execute(
            "INSERT INTO submissions (participant, level, code, correct, points) VALUES (?,?,?,?,?)",
            (sap_username, level, code, 1 if correct else 0, total_pts))
        db.commit()
        db.close()

    return render_template_string(SUBMIT_TEMPLATE, msg=msg, msg_type=msg_type, levels=codes)

@app.route("/admin")
def admin():
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    db = get_db()
    subs = db.execute("SELECT * FROM submissions ORDER BY submitted_at DESC LIMIT 100").fetchall()
    parts = db.execute("SELECT * FROM participants ORDER BY registered_at DESC").fetchall()
    db.close()
    codes = load_codes()
    td = "style='padding:4px 10px'"
    th = "style='text-align:left;padding:4px 10px;color:#aaa'"
    out = f"<h2>Participants</h2><table style='border-collapse:collapse;width:100%'><tr><th {th}>Username</th><th {th}>Name</th><th {th}>Email</th><th {th}>SAP</th><th {th}>VPN IP</th><th {th}>Registered</th><th></th></tr>"
    for p in parts:
        sap_icon = "&#x2705;" if p["sap_created"] else "manual"
        wg_icon  = p["wg_ip"] if p["wg_ip"] else "no VPN"
        uname = p["sap_username"]
        is_locked = p["locked"]
        kicked_at = p["kicked_at"]
        row_style = "border-top:1px solid #333;background:#2a0a0a" if is_locked else "border-top:1px solid #333"
        if kicked_at:
            status_badge = f"<span style='color:#f39c12;font-weight:bold'>&#x26A1; KICKED</span> <span style='color:#888;font-size:0.8em'>({kicked_at[:16]})</span>"
        elif is_locked:
            status_badge = "<span style='color:#e74c3c;font-weight:bold'>&#x1F512; LOCKED</span>"
        else:
            status_badge = "<span style='color:#2ecc71'>active</span>"
        lock_btn = (
            f"<form method='POST' action='/admin/unlock/{uname}' style='display:inline'>"
            f"<button style='background:#27ae60;color:#fff;border:none;padding:2px 8px;border-radius:4px;cursor:pointer;margin-right:3px'>Unlock</button></form>"
        ) if is_locked else (
            f"<form method='POST' action='/admin/lock/{uname}' style='display:inline'>"
            f"<button style='background:#e67e22;color:#fff;border:none;padding:2px 8px;border-radius:4px;cursor:pointer;margin-right:3px'>Lock</button></form>"
        )
        out += (
            f"<tr style='{row_style}'>"
            f"<td {td}><strong>{uname}</strong></td>"
            f"<td {td}>{p['name']}</td>"
            f"<td {td} style='color:#aaa'>{p['email']}</td>"
            f"<td {td}>{sap_icon} {status_badge}</td>"
            f"<td {td}>{wg_icon}</td>"
            f"<td {td} style='color:#aaa'>{p['registered_at']}</td>"
            f"<td {td} style='white-space:nowrap'>"
            f"{lock_btn}"
            f"<form method='POST' action='/admin/kick/{uname}' style='display:inline'>"
            f"<button style='background:#8e44ad;color:#fff;border:none;padding:2px 8px;border-radius:4px;cursor:pointer;margin-right:3px' title='Expire their session cookie — forces re-auth'>Kick</button></form>"
            f"<form method='POST' action='/admin/delete/{uname}' style='display:inline'>"
            f"<button onclick=\"return confirm('Delete {uname} and remove WireGuard peer? This cannot be undone.');\" "
            f"style='background:#c0392b;color:#fff;border:none;padding:2px 8px;border-radius:4px;cursor:pointer'>Delete</button>"
            f"</form></td></tr>"
        )
    out += "</table><h2>Recent Submissions</h2><pre>"
    for s in subs:
        status = "OK" if s["correct"] else "WRONG"
        out += f"[{status}] {s['participant']} | {s['level']} | {s['code']} | {s['points']}pts | {s['submitted_at']}\n"
    out += "</pre><h2>Active Codes</h2><pre>"
    for lvl, info in codes.items():
        out += f"{lvl}: {info['code']} ({info['points']} pts)\n"
    out += "</pre><br><form method='POST' action='/admin/reset' onsubmit=\"return confirm('Reset ALL data? This also removes all WireGuard peers.');\" ><button style='background:#c0392b;color:#fff;border:none;padding:8px 20px;border-radius:4px;cursor:pointer;font-size:1em'>Reset Everything</button></form>" 
    return f"<html><body style='font-family:monospace;background:#111;color:#eee;padding:20px'>{out}</body></html>"

@app.route("/admin/delete/<sap_username>", methods=["POST"])
def admin_delete_user(sap_username):
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    uname = sap_username.upper()
    db = get_db()
    row = db.execute("SELECT wg_ip FROM participants WHERE sap_username=?", (uname,)).fetchone()

    # 1. Delete SAP user (kills sessions + BAPI_USER_DELETE)
    sap_ok, sap_err = delete_sap_user(uname)
    if not sap_ok:
        app.logger.warning("SAP user deletion failed for %s: %s", uname, sap_err)

    # 2. Remove WireGuard peer
    wg_ok, wg_err = True, ""
    if row and row["wg_ip"]:
        wg_ok, wg_err = remove_customer_peer(row["wg_ip"])
        if not wg_ok:
            app.logger.warning("WG peer removal failed for %s: %s", uname, wg_err)

    # 3. Remove from leaderboard DB (always — no inconsistent states)
    db.execute("DELETE FROM submissions WHERE participant=?", (uname,))
    db.execute("DELETE FROM participants WHERE sap_username=?", (uname,))
    db.commit()
    db.close()
    app.logger.warning("Admin deleted user %s (SAP:%s WG:%s)",
                       uname, "ok" if sap_ok else sap_err,
                       "ok" if wg_ok else (wg_err if row and row["wg_ip"] else "no-peer"))
    return redirect("/admin")

@app.route("/admin/lock/<sap_username>", methods=["POST"])
def admin_lock_user(sap_username):
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    uname = sap_username.upper()
    # Lock in leaderboard DB
    db = get_db()
    db.execute("UPDATE participants SET locked=1 WHERE sap_username=?", (uname,))
    db.commit()
    db.close()
    # Lock in SAP via BAPI_USER_CHANGE
    ok, err = lock_sap_user(uname)
    if not ok:
        app.logger.warning("SAP lock failed for %s (leaderboard lock still applied): %s", uname, err)
    app.logger.warning("Admin locked user %s", uname)
    return redirect("/admin")


@app.route("/admin/unlock/<sap_username>", methods=["POST"])
def admin_unlock_user(sap_username):
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    uname = sap_username.upper()
    db = get_db()
    db.execute("UPDATE participants SET locked=0, kicked_at=NULL WHERE sap_username=?", (uname,))
    db.commit()
    db.close()
    # Unlock in SAP
    ok, err = unlock_sap_user(uname)
    if not ok:
        app.logger.warning("SAP unlock failed for %s: %s", uname, err)
    return redirect("/admin")


@app.route("/admin/kick/<sap_username>", methods=["POST"])
def admin_kick_user(sap_username):
    """
    Kill active SAP sessions (TH_DELETE_USER) + lock the SAP user (BAPI_USER_CHANGE)
    + lock in leaderboard DB with a kicked_at timestamp.
    """
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    uname = sap_username.upper()
    from datetime import datetime
    db = get_db()
    db.execute(
        "UPDATE participants SET locked=1, kicked_at=? WHERE sap_username=?",
        (datetime.utcnow().isoformat(timespec="seconds"), uname))
    db.commit()
    db.close()
    # Terminate active SAP sessions
    ok, err = kick_sap_user(uname)
    if not ok:
        app.logger.warning("SAP session kill failed for %s: %s", uname, err)
    # Lock the SAP account so they can't log back in
    ok, err = lock_sap_user(uname)
    if not ok:
        app.logger.warning("SAP lock after kick failed for %s: %s", uname, err)
    app.logger.warning("Admin kicked user %s", uname)
    return redirect("/admin")


@app.route("/admin/reset", methods=["POST"])
def reset():
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    db = get_db()
    parts = db.execute("SELECT wg_ip FROM participants WHERE wg_ip IS NOT NULL").fetchall()
    for p in parts:
        ok, err = remove_customer_peer(p["wg_ip"])
        if not ok:
            app.logger.warning("WG peer removal failed for %s during reset: %s", p["wg_ip"], err)
    db.execute("DELETE FROM submissions")
    db.execute("DELETE FROM participants")
    db.commit()
    db.close()
    return redirect("/admin")

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print("DAC Workshop Leaderboard running on http://0.0.0.0:9000")
    app.run(host="0.0.0.0", port=9000, debug=False)
