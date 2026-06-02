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
from sap_user import create_workshop_user, user_exists, SAP_AVAILABLE
from wireguard_peer import create_customer_peer, WG_AVAILABLE

app = Flask(__name__)
DB = "/data/leaderboard.db"
CONFIG_FILE = "/data/level_codes.json"
LOGO_PATH = os.path.join(os.path.dirname(__file__), "pathlock-logo.svg")

# ---------------------------------------------------------------------------
# Security config — set via environment variables
# ---------------------------------------------------------------------------

# Access code required to reach the /register form.
# Set to any memorable word you'll announce at the start of the session.
# Example:  REGISTER_CODE=meridian2026
REGISTER_CODE    = os.environ.get("REGISTER_CODE", "").strip()

# HTTP Basic Auth password for /admin routes.
# Example:  ADMIN_PASSWORD=s3cr3t
ADMIN_PASSWORD   = os.environ.get("ADMIN_PASSWORD", "").strip()

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
    if auth and auth.username == "admin" and hmac.compare_digest(auth.password, ADMIN_PASSWORD):
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

# ---------------------------------------------------------------------------
# Static assets
# ---------------------------------------------------------------------------
@app.route("/logo")
def logo():
    return send_file(LOGO_PATH, mimetype="image/svg+xml")

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
  <meta http-equiv="refresh" content="10">
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
        <span style="color:#2ecc71">①</span> &nbsp;Install <a href="https://www.wireguard.com/install/" target="_blank" style="color:#2ecc71">WireGuard</a> on your laptop or phone if you haven't already<br>
        <span style="color:#2ecc71">②</span> &nbsp;Go to <a href="/register" style="color:#2ecc71">Register</a> — enter the <strong style="color:#fff">access code your instructor announced</strong>, fill in your details and choose a SAP username<br>
        <span style="color:#2ecc71">③</span> &nbsp;Download your personal <strong style="color:#fff">WireGuard VPN config</strong> from the registration confirmation page and import it into the WireGuard app<br>
        <span style="color:#2ecc71">④</span> &nbsp;Connect to the VPN, open SAP GUI or Fiori, and work through the levels — starting with <strong style="color:#fff">Level 0</strong><br>
        <span style="color:#2ecc71">⑤</span> &nbsp;Found a completion code? Submit it at <a href="/submit" style="color:#2ecc71">Submit Code</a> to claim your points and climb the leaderboard<br>
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid #2a2a3e;color:#aaa;font-size:0.9em">
          📖 &nbsp;Go to the <a href="https://github.com/JonathanStross/CAC-ABAC-Workshop" target="_blank" style="color:#7ec8e3">CAC-ABAC-Workshop GitHub repo</a>
          and start with <strong style="color:#fff">Level 0</strong>!<br>
          Your instructor will also provide the SAP system address, client number, and any additional guidance.
        </div>
      </div>
    </div>

    {% if rows %}
    <table>
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
    <p style="text-align:center; color:#666; padding: 40px">No participants yet — be the first to register!</p>
    {% endif %}

    <p class="refresh-note">Auto-refreshes every 10 seconds</p>
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
    <div class="nav"><a href="/">← Back to Leaderboard</a></div>
    {% if success %}
      <div class="msg ok" style="font-size:1.1em">
        <strong>✅ You're registered!</strong><br><br>
        <table style="background:transparent;width:auto">
          <tr><td style="padding:4px 16px 4px 0;color:#aaa">SAP System</td><td><strong>10.8.0.1:3200 &nbsp;|&nbsp; Client 001</strong></td></tr>
          <tr><td style="padding:4px 16px 4px 0;color:#aaa">Your username</td><td><strong style="font-size:1.2em;color:#ffd700">{{ sap_username }}</strong></td></tr>
          <tr><td style="padding:4px 16px 4px 0;color:#aaa">Temporary password</td><td><strong style="font-size:1.2em;color:#ffd700;letter-spacing:2px">{{ temp_password }}</strong></td></tr>
          {% if wg_ip %}
          <tr><td style="padding:4px 16px 4px 0;color:#aaa">VPN IP</td><td><strong style="color:#2ecc71">{{ wg_ip }}</strong></td></tr>
          {% endif %}
        </table>
        <br>⚠️ <strong>Write the password down now.</strong> It is shown only once and will prompt for a change on first login.
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
          iOS/Android: scan QR from the WireGuard app on the server.
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
    <div class="nav"><a href="/">← Back to Leaderboard</a></div>
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
    <div class="nav"><a href="/">← Back to Leaderboard</a></div>
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

@app.route("/register", methods=["GET", "POST"])
def register():
    ip = request.remote_addr or "unknown"

    # ---- Step 1: access code gate ------------------------------------------
    # If REGISTER_CODE is set, the user must first POST the correct code.
    # We store a simple session token in a cookie once the code is verified.
    ACCESS_COOKIE = "wb_access"

    def _access_granted() -> bool:
        if not REGISTER_CODE:
            return True   # no code configured — open registration
        token = request.cookies.get(ACCESS_COOKIE, "")
        expected = hashlib.sha256(REGISTER_CODE.encode()).hexdigest()
        return hmac.compare_digest(token, expected)

    # POST with only access_code field → validate the gate
    if request.method == "POST" and "access_code" in request.form and "name" not in request.form:
        entered = request.form.get("access_code", "").strip()
        if REGISTER_CODE and hmac.compare_digest(
                hashlib.sha256(entered.encode()).hexdigest(),
                hashlib.sha256(REGISTER_CODE.encode()).hexdigest()):
            # Correct — set cookie and show the registration form
            resp = Response(render_template_string(REGISTER_TEMPLATE,
                success=False, msg=None, msg_type="ok", sap_available=SAP_AVAILABLE,
                form_name="", form_email="", form_sap="", form_company=""))
            resp.set_cookie(ACCESS_COOKIE,
                hashlib.sha256(REGISTER_CODE.encode()).hexdigest(),
                max_age=3600, httponly=True, samesite="Lax")
            return resp
        return render_template_string(ACCESS_CODE_TEMPLATE,
            error="Incorrect access code. Check with your instructor.")

    # GET or unauthed → show gate or form depending on cookie
    if request.method == "GET":
        if not _access_granted():
            return render_template_string(ACCESS_CODE_TEMPLATE, error=None)
        return render_template_string(REGISTER_TEMPLATE,
            success=False, msg=None, msg_type="ok", sap_available=SAP_AVAILABLE,
            form_name="", form_email="", form_sap="", form_company="")

    # ---- Step 2: actual registration POST ----------------------------------
    if not _access_granted():
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
    name         = _sanitize_text(request.form.get("name", ""), 80)
    email        = _sanitize_text(request.form.get("email", "").lower(), 120)
    sap_username = _sanitize_text(request.form.get("sap_username", "").upper(), 12)
    company      = _sanitize_text(request.form.get("company", ""), 80)

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
    if len(sap_username) > 12:
        return err("SAP username must be 12 characters or fewer.")
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

@app.route("/api/leaderboard")
def api_leaderboard():
    rows = get_leaderboard()
    return jsonify([dict(r) for r in rows])

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
    out = "<h2>Participants</h2><pre>"
    for p in parts:
        sap_icon = "✅" if p["sap_created"] else "⚠️ manual"
        wg_icon  = f"🌐 {p['wg_ip']}" if p["wg_ip"] else "⚠️ no VPN"
        out += f"{p['sap_username']:12s}  {p['name']:30s}  {p['email']:35s}  SAP:{sap_icon}  WG:{wg_icon}  {p['registered_at']}\n"
    out += "</pre><h2>Recent Submissions</h2><pre>"
    for s in subs:
        status = "✅" if s["correct"] else "❌"
        out += f"{status} {s['participant']} | {s['level']} | {s['code']} | {s['points']}pts | {s['submitted_at']}\n"
    out += "</pre><h2>Active Codes</h2><pre>"
    for lvl, info in codes.items():
        out += f"{lvl}: {info['code']} ({info['points']} pts)\n"
    return f"<html><body style='font-family:monospace;background:#111;color:#eee;padding:20px'>{out}</body></html>"

@app.route("/admin/reset", methods=["POST"])
def reset():
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    db = get_db()
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
