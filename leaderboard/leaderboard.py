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

from flask import Flask, request, redirect, render_template_string, jsonify, Response, send_file, send_from_directory, abort, session
import sqlite3, hashlib, json, os, re, time, hmac, base64, secrets
from datetime import datetime
try:
    import markdown as _markdown_lib
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
from sap_user import create_workshop_user, user_exists, lock_sap_user, unlock_sap_user, kick_sap_user, delete_sap_user, reset_sap_password, SAP_AVAILABLE
from wireguard_peer import create_customer_peer, remove_customer_peer, WG_AVAILABLE

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
DB = "/data/leaderboard.db"
CONFIG_FILE = "/data/level_codes.json"
LOGO_PATH = os.path.join(os.path.dirname(__file__), "pathlock-logo.svg")
# Level guide .md files — lives one directory above the leaderboard/ folder
HANDOUTS_DIR = os.path.join(os.path.dirname(__file__), "..", "handouts")
# Screenshots embedded in level guides — git-tracked, updated via git pull
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "..", "screenshots")
# Downloadable files (policy templates, cheat sheets, etc.) — git-tracked
FILES_DIR = os.path.join(os.path.dirname(__file__), "..", "files")
# Video walkthroughs embedded in level guides — git-tracked
VIDEOS_DIR = os.path.join(os.path.dirname(__file__), "..", "videos")

# ---------------------------------------------------------------------------
# Security config — set via environment variables
# ---------------------------------------------------------------------------

# Access code required to reach the /register form.
# Set to any memorable word you'll announce at the start of the session.
# Example:  REGISTER_CODE=meridian2026
REGISTER_CODE    = os.environ.get("REGISTER_CODE", "").strip()

# ---------------------------------------------------------------------------
# Auth helpers — session-based login
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    """SHA-256 hash with a fixed pepper. Not bcrypt but good enough for a workshop."""
    pepper = os.environ.get("SECRET_KEY", "workshop-pepper")
    return hashlib.sha256((pepper + password).encode()).hexdigest()

def _current_user():
    """Return the logged-in user row (participant first, then pending_reg), or None."""
    email = session.get("user_email")
    if not email:
        return None, None
    db = get_db()
    p = db.execute("SELECT * FROM participants WHERE email=?", (email,)).fetchone()
    if p:
        db.close()
        return "enrolled", p
    pr = db.execute("SELECT * FROM pending_registrations WHERE email=?", (email,)).fetchone()
    db.close()
    if pr:
        return pr["status"], pr  # status: pending | approved | rejected
    return None, None

def _is_logged_in() -> bool:
    return "user_email" in session

def _is_enrolled() -> bool:
    """True only if the user has completed enrollment (has a participant row)."""
    email = session.get("user_email")
    if not email:
        return False
    db = get_db()
    row = db.execute("SELECT 1 FROM participants WHERE email=?", (email,)).fetchone()
    db.close()
    return row is not None

# Keep for backward compat — old code uses _has_access_cookie()
def _has_access_cookie() -> bool:
    return _is_enrolled()

# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# SAP server — single system (sap2)
# ---------------------------------------------------------------------------
# sap3/4/5 were decommissioned July 2026. Only sap2 remains active.
# SAP_HOST is the WireGuard VPN address shown to participants (always 10.8.0.1).
# SAP2_HOST is used for backend RFC connections from the leaderboard.
SAP_SERVERS: dict[str, dict] = {
    "sap2": {"host": os.environ.get("SAP2_HOST", "159.195.81.132"), "sysnr": "00"},
}
# All participants are assigned to sap2. Multiple clients allow parallel sessions.
SLOT_SERVERS = list(SAP_SERVERS.keys())           # ['sap2']
SLOT_CLIENTS = ["100", "200", "300", "400", "500"]

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

@app.route("/screenshots/<path:filename>")
def screenshot(filename):
    """Serve screenshot images embedded in level guides."""
    safe = os.path.realpath(os.path.join(SCREENSHOTS_DIR, filename))
    if not safe.startswith(os.path.realpath(SCREENSHOTS_DIR)):
        abort(403)
    return send_from_directory(os.path.realpath(SCREENSHOTS_DIR), filename)

@app.route("/files/<path:filename>")
def download_file(filename):
    """Serve downloadable workshop files (policy templates, cheat sheets, etc.)."""
    safe = os.path.realpath(os.path.join(FILES_DIR, filename))
    if not safe.startswith(os.path.realpath(FILES_DIR)):
        abort(403)
    return send_from_directory(os.path.realpath(FILES_DIR), filename, as_attachment=True)

@app.route("/videos/<path:filename>")
def serve_video(filename):
    """Serve MP4 video walkthroughs embedded in level guides."""
    safe = os.path.realpath(os.path.join(VIDEOS_DIR, filename))
    if not safe.startswith(os.path.realpath(VIDEOS_DIR)):
        abort(403)
    return send_from_directory(os.path.realpath(VIDEOS_DIR), filename)

# ---------------------------------------------------------------------------
# Level guide renderer — markdown files from the handouts/ directory
# ---------------------------------------------------------------------------
LEVEL_FILES = {
    0:  "level-00-briefing.md",
    1:  "level-01-orientation.md",
    2:  "level-02-pii-masking.md",
    3:  "level-03-contextual-access.md",
    4:  "level-04-tcode-block.md",
    5:  "level-05-audit-feed.md",
    6:  "level-06-overprivileged-role.md",
    7:  "level-07-classification.md",
    8:  "level-08-export-block.md",
    9:  "level-09-fiori-masking.md",
}

# Levels not yet released — greyed out on index, joke page if accessed by URL
LOCKED_LEVELS = {6, 7, 8, 9}

LEVEL_STYLE = """
<style>
  *,*::before,*::after{box-sizing:border-box}
  body{font-family:'Segoe UI',system-ui,sans-serif;background:#0f0f1a;color:#e0e0e0;margin:0;padding:0}
  /* topbar */
  .topbar{position:sticky;top:0;z-index:100;background:#12121f;border-bottom:1px solid #1e1e35;
    display:flex;align-items:center;padding:0 32px;height:58px;gap:24px;
    box-shadow:0 2px 12px rgba(0,0,0,.45)}
  .topbar .brand{display:flex;align-items:center;gap:14px;text-decoration:none;flex-shrink:0}
  .topbar .brand img{height:30px;width:auto}
  .topbar .brand-divider{width:1px;height:22px;background:#2a2a45;margin:0 2px}
  .topbar .brand-label{font-size:0.82em;font-weight:600;color:#aaa;letter-spacing:.04em;white-space:nowrap}
  .topbar nav{display:flex;align-items:center;gap:4px;margin-left:auto}
  .topbar nav a{color:#bbb;text-decoration:none;padding:6px 14px;border-radius:5px;
    font-size:0.88em;font-weight:500;transition:background .15s,color .15s;white-space:nowrap}
  .topbar nav a:hover{background:#1e1e35;color:#fff}
  .topbar nav a.active{background:#c8102e;color:#fff}
  /* page header */
  .page-header{background:linear-gradient(135deg,#16162a 0%,#1a1a35 100%);
    border-bottom:2px solid #c8102e;padding:28px 40px}
  .page-header h1{margin:0 0 4px;color:#fff;font-size:1.5em;font-weight:700}
  .page-header p{margin:0;color:#888;font-size:0.88em}
  /* content */
  .container{max-width:820px;margin:30px auto;padding:0 24px 60px}
  .level-badge{display:inline-block;background:#c8102e;color:#fff;border-radius:4px;
    padding:3px 10px;font-size:0.8em;font-weight:bold;margin-right:8px;vertical-align:middle}
  h1{color:#fff;border-bottom:1px solid #2a2a3e;padding-bottom:10px;margin-top:28px}
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
  blockquote{border-left:3px solid #c8102e;margin:16px 0;padding:10px 16px;
    background:#1a1a2e;color:#aaa;border-radius:0 6px 6px 0}
  blockquote p{margin:0;color:#ccc}
  hr{border:none;border-top:1px solid #2a2a3e;margin:28px 0}
  .hint-box{background:#1a2a1a;border:1px solid #2ecc71;border-radius:6px;padding:14px 18px;margin:16px 0}
  .warn-box{background:#2a1a0a;border:1px solid #f39c12;border-radius:6px;padding:14px 18px;margin:16px 0}
  .level-nav{display:flex;justify-content:space-between;margin-top:40px;
    padding-top:20px;border-top:1px solid #2a2a3e}
  .level-nav a{background:#1a1a2e;border:1px solid #3a3a5e;padding:10px 18px;
    border-radius:6px;color:#aaa;text-decoration:none;font-size:0.9em}
  .level-nav a:hover{background:#2a2a3e;color:#fff}
  details summary{cursor:pointer;color:#2ecc71;font-weight:600;padding:6px 0}
  details[open] summary{color:#27ae60}
  img{max-width:100%;height:auto;border-radius:6px;margin:12px 0;display:block}
  img+em{display:block;color:#666;font-size:0.82em;margin-top:-6px;margin-bottom:16px}
</style>
"""

# ---------------------------------------------------------------------------
# Level 3 — "Find Your Lab Partner" widget
# Injected into the /levels/3 page; fetches /api/server-peers at runtime.
# ---------------------------------------------------------------------------
_L2_PEERS_WIDGET = """
<div style="margin-top:2.5em;padding:1.5em;background:#0d1a0d;border:1px solid #2ecc71;border-radius:8px">
  <h3 style="color:#2ecc71;margin-top:0">&#x1F91D; Find Your Lab Partner</h3>
  <p style="color:#ccc">Find a colleague on the <strong>same SAP server</strong> as you — they will have a different VPN IP because they use a different WireGuard config.
  Enter your SAP username to see your own IP and who is on your server:</p>
  <p style="color:#aaa;font-size:0.9em">&#x1F4CB; <strong>How the demo works:</strong>
  Walk over to your partner&apos;s laptop. From <em>their</em> machine — which has their VPN IP — log into SAP with
  <strong>your own credentials</strong> (your username, your password, your client number).
  Navigate to <code>SE16 &rarr; SCUSTOM</code> and look at the <code>STREET</code> column:
  the masking fires because the source IP is your partner&apos;s, not yours.
  Same user, same role, same data — different machine, different result. Log out immediately after.<br><br>
  <strong>No partner available?</strong> Enter your own IP as the exception &mdash; you will see the data unmasked since your IP matches.
  Then swap the condition to a different IP and re-test: the masking will fire. That gives you both the positive and the negative test on your own.</p>
  <div style="display:flex;gap:0.5em;margin-bottom:1em">
    <input id="peers-input" type="text" placeholder="Your SAP username &#x2014; e.g. JSMITH"
           style="flex:1;padding:0.65em 0.8em;background:#0a0a1a;color:#fff;border:1px solid #444;
                  border-radius:4px;font-family:monospace;font-size:1em;text-transform:uppercase"
           autocomplete="off" spellcheck="false" />
    <button onclick="findPeers()"
            style="padding:0.65em 1.4em;background:#2ecc71;color:#000;border:none;border-radius:4px;
                   cursor:pointer;font-weight:bold;font-size:1em">Find</button>
  </div>
  <div id="peers-result"></div>
</div>
<script>
document.getElementById('peers-input').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') findPeers();
  this.value = this.value.toUpperCase();
});
function findPeers() {
  var username = document.getElementById('peers-input').value.trim().toUpperCase();
  if (!username) return;
  var out = document.getElementById('peers-result');
  out.innerHTML = '<p style="color:#888;font-size:0.9em">Looking up&#x2026;</p>';
  fetch('/api/server-peers?sap_user=' + encodeURIComponent(username))
    .then(function(r) {
      if (!r.ok) throw new Error(r.status === 404
        ? 'Username not found &#x2014; check your SAP username.'
        : 'Server error ' + r.status);
      return r.json();
    })
    .then(function(data) {
      var html = '<p style="color:#aaa;font-size:0.9em">Server: <strong style="color:#fff">'
               + data.server + '</strong> &nbsp;&middot;&nbsp; '
               + data.peers.length + ' participant(s)</p>';
      html += '<table style="width:100%;border-collapse:collapse;font-size:0.9em">';
      html += '<tr>'
            + '<th style="text-align:left;padding:6px 10px;background:#1a2a1a;color:#aaa;border-bottom:1px solid #2a2a3e;font-weight:normal">Name</th>'
            + '<th style="text-align:left;padding:6px 10px;background:#1a2a1a;color:#aaa;border-bottom:1px solid #2a2a3e;font-weight:normal">SAP User</th>'
            + '<th style="text-align:left;padding:6px 10px;background:#1a2a1a;color:#aaa;border-bottom:1px solid #2a2a3e;font-weight:normal">VPN IP</th>'
            + '<th style="text-align:left;padding:6px 10px;background:#1a2a1a;color:#aaa;border-bottom:1px solid #2a2a3e;font-weight:normal">SAP Client</th></tr>';
      data.peers.forEach(function(p) {
        var isMe  = (p.sap_username === username);
        var rowBg = isMe ? 'background:#0a1e0a' : '';
        var badge = isMe ? ' <span style="color:#2ecc71;font-size:0.75em">&#x25C4; you</span>' : '';
        html += '<tr style="' + rowBg + '">'
              + '<td style="padding:7px 10px;border-bottom:1px solid #1e1e2e">' + p.name + badge + '</td>'
              + '<td style="padding:7px 10px;border-bottom:1px solid #1e1e2e;font-family:monospace;color:#e8c07d">' + p.sap_username + '</td>'
              + '<td style="padding:7px 10px;border-bottom:1px solid #1e1e2e;font-family:monospace;color:#2ecc71">' + (p.wg_ip || '&mdash;') + '</td>'
              + '<td style="padding:7px 10px;border-bottom:1px solid #1e1e2e;color:#aaa">' + (p.sap_client || '&mdash;') + '</td>'
              + '</tr>';
      });
      html += '</table>';
      if (data.peers.length > 1) {
        html += '<p style="margin-top:0.8em;color:#aaa;font-size:0.85em">'
              + '&#x1F4A1; Pick any colleague from this list — share your <strong style="color:#fff">client number</strong>'
              + ' with them and ask them to log into SAP on your client. They will see the masking; you will not.</p>';
      } else {
        html += '<p style="margin-top:0.8em;color:#f39c12;font-size:0.85em">'
              + '&#x26A0;&#xFE0F; You&apos;re the only one on your server so far. '
              + 'Ask your instructor to play the role of lab partner, or use your own IP — see the <em>No partner available?</em> note in Step 7.</p>';
      }
      out.innerHTML = html;
    })
    .catch(function(err) {
      out.innerHTML = '<p style="color:#e74c3c">' + err.message + '</p>';
    });
}
</script>
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
        if n in LOCKED_LEVELS:
            link = f"<span style='color:#444'>{key} — {title} <em style='font-size:0.8em'>(not yet available)</em></span>"
            pts_str = f"<span style='color:#333'>{pts} pts</span>"
        elif avail:
            link = f"<a href='/levels/{n}' style='color:#2ecc71'>{key} — {title}</a>"
            pts_str = f"<span style='color:#aaa'>{pts} pts</span>"
        else:
            link = f"<span style='color:#555'>{key} — {title} <em style='font-size:0.8em'>(coming soon)</em></span>"
            pts_str = f"<span style='color:#aaa'>{pts} pts</span>"
        rows += f"<tr><td>{link}</td><td>{pts_str}</td></tr>"
    return f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>Level Guides — DAC: Practitioner Level</title>{LEVEL_STYLE}</head>
<body>
  {_topbar('/levels')}
  <div class='page-header'><h1>Level Guides</h1><p>Meridian AG Audit Remediation &nbsp;·&nbsp; DAC: Practitioner Level</p></div>
  <div class='container'>
    <h2 style='color:#fff;margin-top:24px'>All Levels</h2>
    <table><tr><th>Level</th><th>Points</th></tr>{rows}</table>
  </div>
</body></html>"""

@app.route("/levels/<int:level_num>")
def level_guide(level_num):
    if not _has_access_cookie():
        return redirect("/register")
    if level_num in LOCKED_LEVELS:
        return render_template_string("""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Nice try</title>""" + LEVEL_STYLE + """
<style>
  .locked{display:flex;flex-direction:column;align-items:center;justify-content:center;
          min-height:80vh;text-align:center;padding:40px}
  .locked .emoji{font-size:6rem;margin-bottom:24px;animation:bounce .6s ease infinite alternate}
  @keyframes bounce{from{transform:translateY(0)}to{transform:translateY(-14px)}}
  .locked h1{font-size:2.4rem;color:#c8102e;margin:0 0 16px}
  .locked p{color:#aaa;font-size:1.1rem;max-width:480px;margin:0 0 32px}
  .locked .sub{font-size:0.85rem;color:#444;margin-top:8px}
</style>
</head>
<body>
""" + _topbar("/levels") + """
  <div class="locked">
    <div class="emoji">🔒</div>
    <h1>The joke's on you.</h1>
    <p>This level hasn't been unlocked yet.<br>
       Finish the levels that <em>are</em> available first — your instructor will unlock this one when it's time.</p>
    <a href="/levels" class="btn">← Back to Levels</a>
    <p class="sub">Nice URL guessing though. That's the ABAC spirit.</p>
  </div>
</body>
</html>""")
    if level_num not in LEVEL_FILES:
        return "Level not found.", 404
    md_path = os.path.join(HANDOUTS_DIR, LEVEL_FILES[level_num])
    if not os.path.exists(md_path):
        return f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>Level {level_num}</title>{LEVEL_STYLE}</head>
<body>
  {_topbar('/levels')}
  <div class='page-header'><h1>Level {level_num}</h1><p>Guide coming soon</p></div>
  <div class='container'>
    <p style='color:#666;padding:40px 0;text-align:center'>This level guide hasn't been published yet. Check back soon.</p>
  </div>
</body></html>""", 404
    with open(md_path, encoding="utf-8") as f:
        md_text = f.read()
    if MARKDOWN_AVAILABLE:
        body_html = _markdown_lib.markdown(
            md_text, extensions=["tables", "fenced_code", "toc"])
    else:
        body_html = f"<pre style='white-space:pre-wrap'>{md_text}</pre>"
    # Convert any <img src="/videos/..."> tags (generated by markdown ![...]() syntax)
    # into proper <video> elements with controls and responsive styling.
    import re as _re
    def _img_to_video(m):
        src = m.group(1)
        alt = m.group(2)
        return (f'<video src="{src}" controls controlslist="nodownload" '
                f'style="max-width:100%;border-radius:6px;margin:12px 0;display:block">'
                f'</video>')
    body_html = _re.sub(
        r'<img\s+(?:[^>]*?\s)?src="(/videos/[^"]+)"(?:\s+alt="([^"]*)")?[^>]*?>',
        _img_to_video,
        body_html
    )
    prev_link = f"<a href='/levels/{level_num-1}'>← Level {level_num-1}</a>" if level_num > 0 else "<span></span>"
    next_link = f"<a href='/levels/{level_num+1}'>Level {level_num+1} →</a>" if (level_num+1) in LEVEL_FILES else "<span></span>"
    codes = load_codes()
    key = f"L{level_num}"
    title = codes.get(key, {}).get("title", f"Level {level_num}")
    extra_widget = _L2_PEERS_WIDGET if level_num == 3 else ""
    # Inject widget at placeholder position in the body (Step 1), not at the bottom
    if extra_widget and "<!-- PEERS_WIDGET -->" in body_html:
        body_html = body_html.replace("<!-- PEERS_WIDGET -->", extra_widget)
        extra_widget = ""
    return f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>L{level_num} — {title}</title>{LEVEL_STYLE}</head>
<body>
  {_topbar('/levels')}
  <div class='page-header'>
    <h1><span class='level-badge'>L{level_num}</span> {title}</h1>
    <p>Meridian AG Audit Remediation &nbsp;·&nbsp; DAC: Practitioner Level</p>
  </div>
  <div class='container'>
    {body_html}
    {extra_widget}
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
        -- Pending registrations — email only, awaiting admin approval
        CREATE TABLE IF NOT EXISTS pending_registrations (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            company       TEXT,
            message       TEXT,
            password_hash TEXT,
            submitted_at  TEXT DEFAULT (datetime('now')),
            status        TEXT DEFAULT 'pending'  -- pending | approved | rejected
        );

        -- Classes — each class has a unique enroll_code; participants enroll after approval
        CREATE TABLE IF NOT EXISTS classes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            description   TEXT,
            enroll_code   TEXT NOT NULL UNIQUE,
            active        INTEGER DEFAULT 1,
            created_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS participants (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            sap_username  TEXT NOT NULL UNIQUE,
            company       TEXT,
            password_hash TEXT,
            class_id      INTEGER REFERENCES classes(id),
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
        CREATE TABLE IF NOT EXISTS slots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            server      TEXT NOT NULL,
            sap_client  TEXT NOT NULL,
            assigned_to TEXT,
            assigned_at TEXT
        );
    """)
    # Migrate older DBs — add any missing columns
    existing = {row[1] for row in db.execute("PRAGMA table_info(participants)")}
    for col, typedef in [
        ("wg_ip",           "TEXT"),
        ("wg_conf",         "TEXT"),
        ("locked",          "INTEGER DEFAULT 0"),
        ("kicked_at",       "TEXT"),
        ("server",          "TEXT"),
        ("sap_client",      "TEXT"),
        ("waiver_accepted", "INTEGER DEFAULT 0"),
        ("class_id",        "INTEGER"),
        ("password_hash",   "TEXT"),
        ("temp_password",   "TEXT"),
        ("expires_at",      "TEXT"),
    ]:
        if col not in existing:
            db.execute(f"ALTER TABLE participants ADD COLUMN {col} {typedef}")
    # Migrate pending_registrations too
    pr_existing = {row[1] for row in db.execute("PRAGMA table_info(pending_registrations)")}
    if "password_hash" not in pr_existing:
        db.execute("ALTER TABLE pending_registrations ADD COLUMN password_hash TEXT")
    db.commit()
    _seed_slots(db)
    db.close()


def _seed_slots(db):
    """Populate the slots table on first run. No-op if already seeded."""
    count = db.execute("SELECT COUNT(*) FROM slots").fetchone()[0]
    if count > 0:
        return
    for cli in SLOT_CLIENTS:
        for srv in SLOT_SERVERS:
            db.execute("INSERT INTO slots (server, sap_client) VALUES (?, ?)", (srv, cli))
    db.commit()
    app.logger.info("Seeded %d slots (%s × %s)",
                    len(SLOT_SERVERS) * len(SLOT_CLIENTS),
                    SLOT_SERVERS, SLOT_CLIENTS)


def _assign_slot(sap_username: str) -> tuple[str | None, str | None]:
    """
    Atomically claim the next free slot for *sap_username*.

    Uses BEGIN IMMEDIATE so concurrent registrations can't grab the same slot.

    Returns (server_alias, sap_client) or (None, None) when fully booked.
    """
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None   # manual transaction mode
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT id, server, sap_client FROM slots "
            "WHERE assigned_to IS NULL ORDER BY id LIMIT 1"
        ).fetchone()
        if not row:
            conn.execute("ROLLBACK")
            return None, None
        conn.execute(
            "UPDATE slots SET assigned_to=?, assigned_at=? WHERE id=?",
            (sap_username, datetime.utcnow().isoformat(timespec="seconds"), row["id"]),
        )
        conn.execute("COMMIT")
        return row["server"], row["sap_client"]
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()

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
  *, *::before, *::after { box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f0f1a; color: #e0e0e0; margin: 0; padding: 0; }

  /* ── Top bar ─────────────────────────────────────────────────── */
  .topbar {
    position: sticky; top: 0; z-index: 100;
    background: #12121f;
    border-bottom: 1px solid #1e1e35;
    display: flex; align-items: center;
    padding: 0 32px; height: 58px; gap: 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,.45);
  }
  .topbar .brand {
    display: flex; align-items: center; gap: 14px;
    text-decoration: none; flex-shrink: 0;
  }
  .topbar .brand img { height: 30px; width: auto; }
  .topbar .brand-divider {
    width: 1px; height: 22px; background: #2a2a45; margin: 0 2px;
  }
  .topbar .brand-label {
    font-size: 0.82em; font-weight: 600; color: #aaa;
    letter-spacing: .04em; white-space: nowrap;
  }
  .topbar nav {
    display: flex; align-items: center; gap: 4px;
    margin-left: auto;
  }
  .topbar nav a {
    color: #bbb; text-decoration: none;
    padding: 6px 14px; border-radius: 5px;
    font-size: 0.88em; font-weight: 500;
    transition: background .15s, color .15s;
    white-space: nowrap;
  }
  .topbar nav a:hover { background: #1e1e35; color: #fff; }
  .topbar nav a.active { background: #c8102e; color: #fff; }
  .topbar nav .nav-sep {
    width: 1px; height: 18px; background: #2a2a45; margin: 0 4px;
  }

  /* ── Page header (title block below topbar) ──────────────────── */
  .page-header {
    background: linear-gradient(135deg, #16162a 0%, #1a1a35 100%);
    border-bottom: 2px solid #c8102e;
    padding: 28px 40px;
  }
  .page-header h1 { margin: 0 0 4px; color: #fff; font-size: 1.5em; font-weight: 700; }
  .page-header p  { margin: 0; color: #888; font-size: 0.88em; }

  /* ── Content ─────────────────────────────────────────────────── */
  .container { max-width: 920px; margin: 30px auto; padding: 0 24px 60px; }
  table { width: 100%; border-collapse: collapse; background: #1a1a2e; border-radius: 8px; overflow: hidden; }
  th { background: #c8102e; color: white; padding: 12px 16px; text-align: left; font-size: 0.82em; text-transform: uppercase; letter-spacing: .05em; }
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
  input, select { width: 100%; padding: 10px; margin: 8px 0 16px; background: #0f0f1a; border: 1px solid #3a3a5e; color: #e0e0e0; border-radius: 4px; font-size: 1em; }
  input[type="checkbox"] { width: auto; padding: 0; margin: 3px 0 0; flex-shrink: 0; }
  .msg { padding: 12px 20px; border-radius: 6px; margin-bottom: 20px; }
  .msg.ok { background: #1a3a1a; border: 1px solid #2ecc71; color: #2ecc71; }
  .msg.err { background: #3a1a1a; border: 1px solid #c8102e; color: #ff6b6b; }
  .refresh-note { color: #666; font-size: 0.8em; text-align: right; margin-top: 10px; }
  .level-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; margin: 20px 0; }
  .level-cell { background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 6px; padding: 10px; text-align: center; font-size: 0.85em; }
  .level-cell.done { border-color: #2ecc71; color: #2ecc71; }
</style>
"""

# ---------------------------------------------------------------------------
# Shared topbar snippet — injected into every main page
# ---------------------------------------------------------------------------
def _topbar(active: str = "", authenticated: bool = True) -> str:
    """
    Build the topbar HTML.
    authenticated=True  → show enrolled nav (Leaderboard/Levels/Submit + Profile/Logout)
    authenticated=False → show public nav (Register/Sign in)
    Baked-in template calls always pass True (auth-gated pages); the home page
    passes the real value at request time.
    """
    try:
        logged_in = _is_logged_in()
    except RuntimeError:
        # Called outside request context (module-level template build)
        logged_in = authenticated

    always_links = [("/", "&#127968;", "Academy")]
    guest_links  = [("/register", "📝", "Register"), ("/login", "🔑", "Sign in")]
    user_links   = [("/profile", "👤", "My Profile"), ("/logout", "↩", "Sign out")]
    enrolled_links = [
        ("/leaderboard", "&#127942;", "Leaderboard"),
        ("/levels",      "📖",        "Levels"),
        ("/submit",      "✅",         "Submit"),
    ]

    links = always_links
    if authenticated:
        links += enrolled_links + user_links
    elif logged_in:
        links += user_links
    else:
        links += guest_links

    items = ""
    for href, icon, label in links:
        cls = ' class="active"' if active == href else ""
        items += f'<a href="{href}"{cls}>{icon}&nbsp; {label}</a>'
    return f"""
<div class="topbar">
  <a class="brand" href="/">
    <img src="/logo" alt="Pathlock">
    <span class="brand-divider"></span>
    <span class="brand-label">Academy</span>
  </a>
  <nav>{items}</nav>
</div>"""

HOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Pathlock Academy</title>
  """ + STYLE + """
  <style>
    .hero{background:linear-gradient(135deg,#0d0d1f 0%,#14142a 60%,#1a0a1a 100%);border-bottom:1px solid #1e1e35;padding:52px 40px 44px;text-align:center}
    .hero h1{font-size:2.1em;font-weight:800;color:#fff;margin:0 0 10px;letter-spacing:-.02em}
    .hero h1 span{color:#c8102e}
    .hero p{color:#999;font-size:1em;max-width:540px;margin:0 auto 24px;line-height:1.7}
    .hero .cta-note{display:inline-block;background:#1a1a2e;border:1px solid #2a2a45;border-radius:8px;padding:10px 22px;color:#aaa;font-size:0.85em;line-height:1.6}
    .hero .cta-note a{color:#c8102e;text-decoration:none;font-weight:600}
    .hero .cta-note a:hover{color:#e83050}
    .catalog{max-width:960px;margin:0 auto;padding:40px 24px 20px}
    .catalog-section{margin-bottom:36px}
    .catalog-section h2{font-size:0.75em;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#555;border-bottom:1px solid #1a1a2e;padding-bottom:10px;margin-bottom:14px}
    .catalog-section h2 span{color:#888;font-weight:400;margin-left:8px;text-transform:none;font-size:1.15em;letter-spacing:0}
    .course-row{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}
    .course-card{background:#13131f;border:1px solid #1a1a2e;border-radius:10px;padding:16px 16px 12px;position:relative;transition:border-color .2s,background .2s}
    a.course-card{text-decoration:none;display:block;cursor:pointer}
    a.course-card:hover{border-color:#c8102e;background:#180810}
    .course-card.locked{opacity:.62;cursor:default;filter:saturate(0)}
    .course-card .ct{font-size:0.68em;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#555;margin-bottom:5px}
    a.course-card .ct{color:#c8102e}
    .course-card .cn{font-size:0.92em;font-weight:600;color:#bbb;margin-bottom:3px}
    a.course-card .cn{color:#fff}
    .course-card .cs{font-size:0.76em;color:#666;line-height:1.5}
    a.course-card .cs{color:#999}
    .cbadge{position:absolute;top:10px;right:10px;font-size:0.65em;font-weight:700;padding:2px 7px;border-radius:4px;text-transform:uppercase;letter-spacing:.05em}
    .blive{background:#c8102e;color:#fff}
    .bsoon{background:#252538;color:#888}
    .lb-section{max-width:960px;margin:0 auto;padding:0 24px 60px;border-top:1px solid #1a1a2e}
    .lb-section h2{font-size:0.75em;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#555;padding:28px 0 16px;margin:0;border-bottom:1px solid #1a1a2e;margin-bottom:16px}
    .lb-section h2 span{color:#c8102e;font-size:1.15em}
  </style>
</head>
<body>
  {{ topbar | safe }}

  <div class="hero">
    <h1>Welcome to <span>Pathlock</span> Academy</h1>
    <p>Hands-on, certification-level training for the Pathlock security and compliance platform. Work through real SAP scenarios, earn points, and qualify for official certificates.</p>
    <div class="cta-note">
      New here? &nbsp;<a href="/register">Request access →</a>&nbsp; &nbsp;Already approved? &nbsp;<a href="/enroll">Enroll in your class →</a>
    </div>
  </div>

  <div class="catalog">

    <div class="catalog-section">
      <h2>DAC <span>Dynamic Access Control</span></h2>
      <div class="course-row">
        {% if authenticated %}
        <a class="course-card" href="/levels">
          <span class="cbadge blive">Live now</span>
          <div class="ct">DAC</div>
          <div class="cn">Practitioner</div>
          <div class="cs">Masking · TCode blocking · Audit feed · Export control · Fiori/OData</div>
        </a>
        {% else %}
        <div class="course-card locked">
          <span class="cbadge bsoon">Enroll to access</span>
          <div class="ct">DAC</div>
          <div class="cn">Practitioner</div>
          <div class="cs">Masking · TCode blocking · Audit feed · Export control · Fiori/OData</div>
        </div>
        {% endif %}
        <div class="course-card locked">
          <span class="cbadge bsoon">Coming soon</span>
          <div class="ct">DAC</div>
          <div class="cn">Professional</div>
          <div class="cs">Policy architecture · Multi-system rollout · Compliance automation</div>
        </div>
        <div class="course-card locked">
          <span class="cbadge bsoon">Coming soon</span>
          <div class="ct">DAC</div>
          <div class="cn">Master</div>
          <div class="cs">Enterprise ABAC design · GRC integration · Framework certification</div>
        </div>
      </div>
    </div>

    <div class="catalog-section">
      <h2>TD <span>Threat Detection</span></h2>
      <div class="course-row">
        <div class="course-card locked"><span class="cbadge bsoon">Coming soon</span><div class="ct">TD</div><div class="cn">Practitioner</div><div class="cs">Threat patterns · Alert configuration · Incident triage</div></div>
        <div class="course-card locked"><span class="cbadge bsoon">Coming soon</span><div class="ct">TD</div><div class="cn">Professional</div><div class="cs">Detection rules · SIEM integration · Threat intelligence</div></div>
        <div class="course-card locked"><span class="cbadge bsoon">Coming soon</span><div class="ct">TD</div><div class="cn">Master</div><div class="cs">Advanced threat hunting · Behavioural analytics · SOC design</div></div>
      </div>
    </div>

    <div class="catalog-section">
      <h2>TR <span>Threat Response</span></h2>
      <div class="course-row">
        <div class="course-card locked"><span class="cbadge bsoon">Coming soon</span><div class="ct">TR</div><div class="cn">Practitioner</div><div class="cs">Incident handling · Containment procedures · Evidence collection</div></div>
        <div class="course-card locked"><span class="cbadge bsoon">Coming soon</span><div class="ct">TR</div><div class="cn">Professional</div><div class="cs">Response playbooks · Forensics · SIEM-driven automation</div></div>
        <div class="course-card locked"><span class="cbadge bsoon">Coming soon</span><div class="ct">TR</div><div class="cn">Master</div><div class="cs">Crisis management · Post-incident review · Regulatory reporting</div></div>
      </div>
    </div>

    <div class="catalog-section">
      <h2>Other Tracks</h2>
      <div class="course-row">
        <div class="course-card locked"><span class="cbadge bsoon">Coming soon</span><div class="ct">Code Security</div><div class="cn">Practitioner</div><div class="cs">ABAP scanning · Vulnerability patterns</div></div>
        <div class="course-card locked"><span class="cbadge bsoon">Coming soon</span><div class="ct">Vulnerability Management</div><div class="cn">Practitioner</div><div class="cs">Patch analysis · Risk prioritisation</div></div>
        <div class="course-card locked"><span class="cbadge bsoon">Coming soon</span><div class="ct">Transport Control</div><div class="cn">Practitioner</div><div class="cs">Change gate policies · Transport risk scoring</div></div>
        <div class="course-card locked"><span class="cbadge bsoon">Coming soon</span><div class="ct">Application Profiler</div><div class="cn">Practitioner</div><div class="cs">Usage analytics · Licence optimisation</div></div>
        <div class="course-card locked"><span class="cbadge bsoon">Coming soon</span><div class="ct">Health Monitoring</div><div class="cn">Practitioner</div><div class="cs">System health · Alerting · SLA dashboards</div></div>
      </div>
    </div>

  </div>

</body>
</html>
"""


# ---------------------------------------------------------------------------
# Dedicated leaderboard page  (/leaderboard)
# ---------------------------------------------------------------------------
LEADERBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Leaderboard — DAC: Practitioner Level</title>
  """ + STYLE + """
</head>
<body>
  """ + _topbar("/leaderboard") + """
  <div class="page-header">
    <h1>Live Leaderboard</h1>
    <p>DAC: Practitioner Level &nbsp;·&nbsp; Pathlock Academy</p>
  </div>
  <div class="container">
    <div id="lb-container">
      {% if rows %}
      <table id="lb-table">
        <tr><th>#</th><th>Participant</th><th>SAP User</th><th>Score</th><th>Levels</th><th>Last Activity</th></tr>
        {% for r in rows %}
        <tr class="rank-{{ loop.index if loop.index <= 3 else '' }}">
          <td>{% if loop.index == 1 %}🥇{% elif loop.index == 2 %}🥈{% elif loop.index == 3 %}🥉{% else %}{{ loop.index }}{% endif %}</td>
          <td><strong>{{ r.name }}</strong></td>
          <td style="color:#aaa;font-size:0.85em">{{ r.sap_username }}</td>
          <td><strong>{{ r.total }} pts</strong></td>
          <td>{{ r.levels_done }} / {{ total_levels }}</td>
          <td style="color:#666;font-size:0.85em">{{ r.last_submission or 'Just registered' }}</td>
        </tr>
        {% endfor %}
      </table>
      {% else %}
      <p style="text-align:center;color:#555;padding:60px 40px">
        No participants yet —
        <a href="/register" style="color:#c8102e;text-decoration:none;font-weight:600">Register to be the first →</a>
      </p>
      {% endif %}
    </div>
    <p class="refresh-note">Live &mdash; updated <span id="last-updated">just now</span></p>
  </div>
  <script>
    const TOTAL_LEVELS = {{ total_levels }};
    const MEDALS = ['🥇','🥈','🥉'];
    function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
    function renderTable(rows){
      const c=document.getElementById('lb-container'); if(!c) return;
      if(!rows||rows.length===0){
        c.innerHTML='<p style="text-align:center;color:#555;padding:60px 40px">No participants yet — <a href="/register" style="color:#c8102e;text-decoration:none;font-weight:600">Register to be the first →</a></p>';
        return;
      }
      let h='<table id="lb-table"><tr><th>#</th><th>Participant</th><th>SAP User</th><th>Score</th><th>Levels</th><th>Last Activity</th></tr>';
      rows.forEach((r,i)=>{
        const rank=i+1,rc=rank<=3?'rank-'+rank:'',medal=rank<=3?MEDALS[i]:rank;
        h+='<tr class="'+rc+'"><td>'+medal+'</td><td><strong>'+esc(r.name)+'</strong></td>'
          +'<td style="color:#aaa;font-size:0.85em">'+esc(r.sap_username)+'</td>'
          +'<td><strong>'+r.total+' pts</strong></td>'
          +'<td>'+r.levels_done+' / '+TOTAL_LEVELS+'</td>'
          +'<td style="color:#666;font-size:0.85em">'+esc(r.last_submission||'Just registered')+'</td></tr>';
      });
      c.innerHTML=h+'</table>';
    }
    function updateTimestamp(){const e=document.getElementById('last-updated');if(e)e.textContent=new Date().toLocaleTimeString();}
    function poll(){fetch('/api/leaderboard').then(r=>r.ok?r.json():null).then(d=>{if(d){renderTable(d.rows);updateTimestamp();}}).catch(()=>{});}
    setInterval(poll,10000);
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
<head><meta charset="utf-8"><title>Register — DAC: Practitioner Level</title>""" + STYLE + """</head>
<body>
  """ + _topbar("/register") + """
  <div class="page-header">
    <h1>Meridian AG — Join the Team</h1>
    <p>Register to get your personal SAP login and join the leaderboard</p>
  </div>
  <div class="container">
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

        <div style="background:#1a1a2e;border:1px solid #c0392b;border-radius:8px;padding:20px;margin:20px 0">
          <h3 style="color:#e74c3c;margin-top:0;margin-bottom:12px">⚠️ Participant Agreement</h3>

          <p style="color:#ccc;font-size:0.88em;margin:0 0 10px"><strong>No screenshots or recordings.</strong> Photography, screen recording, and sharing of any system contents outside this session is strictly prohibited.</p>

          <p style="color:#ccc;font-size:0.88em;margin:0 0 10px"><strong>Responsible use of elevated privileges.</strong> You will receive broad SAP access (SAP_ALL). Any misuse, data exfiltration, or access beyond the scope of this workshop will result in <strong>immediate disqualification</strong> and may lead to <strong>legal action</strong>.</p>

          <p style="color:#ccc;font-size:0.88em;margin:0 0 10px"><strong>Shared system etiquette.</strong> The SAP environment is shared with other participants. Do not modify others' configurations, users, or data. Be mindful and respectful at all times.</p>

          <p style="color:#ccc;font-size:0.88em;margin:0 0 10px"><strong>Leaderboard visibility.</strong> Your display name will be shown publicly on the leaderboard. If you do not wish to share personally identifiable information, use a fictive name in the field above.</p>

          <p style="color:#ccc;font-size:0.88em;margin:0 0 18px"><strong>Data retention.</strong> Access will be revoked after this session and all data will be deleted immediately. If you would like prolonged access, reach out to <a href="mailto:jonathan.stross@pathlock.com" style="color:#c8102e">jonathan.stross@pathlock.com</a>.</p>

          <label style="display:flex;align-items:center;gap:10px;cursor:pointer;border-top:1px solid #333;padding-top:14px">
            <input type="checkbox" name="w_agree" required style="width:auto;padding:0;margin:0;flex-shrink:0;accent-color:#c8102e;width:16px;height:16px">
            <span style="color:#fff;font-size:0.9em;font-weight:600">I have read and agree to all of the above terms.</span>
          </label>
        </div>

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
<head><meta charset="utf-8"><title>Submit Code — DAC: Practitioner Level</title>""" + STYLE + """</head>
<body>
  """ + _topbar("/submit") + """
  <div class="page-header">
    <h1>Submit Completion Code</h1>
    <p>Enter the code you found in SAP / Pathlock to claim your points</p>
  </div>
  <div class="container">
    {% if msg %}<div class="msg {{ msg_type }}">{{ msg }}</div>{% endif %}
    <form method="POST">
      <h2 style="margin-top:0">Level Completion</h2>
      <label>Your SAP username</label>
      <input type="text" name="name" required placeholder="e.g. AMUELLER" style="text-transform:uppercase;letter-spacing:1px">
      <label>Level</label>
      <select name="level">
        {% for lvl, info in levels.items() %}
        {% set lvl_num = lvl[1:]|int %}
        {% if lvl_num in locked_levels %}
        <option value="{{ lvl }}" disabled style="color:#555">{{ lvl }} — {{ info.title }} (not yet available)</option>
        {% else %}
        <option value="{{ lvl }}">{{ lvl }} — {{ info.title }}</option>
        {% endif %}
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
<head><meta charset="utf-8"><title>Register — DAC: Practitioner Level</title>""" + STYLE + """</head>
<body>
  """ + _topbar("/register") + """
  <div class="page-header">
    <h1>Meridian AG — Join the Team</h1>
    <p>Enter your access code to register</p>
  </div>
  <div class="container">
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
    enrolled = _is_enrolled()
    logged_in = _is_logged_in()
    auth = enrolled  # enrolled users get full nav
    return render_template_string(HOME_TEMPLATE,
        authenticated=auth,
        topbar=_topbar("/", authenticated=auth))


@app.route("/leaderboard")
def leaderboard_page():
    if not _has_access_cookie():
        return redirect("/register")
    rows = get_leaderboard()
    codes = load_codes()
    return render_template_string(LEADERBOARD_TEMPLATE,
        rows=rows,
        total_levels=len(codes))


@app.route("/api/leaderboard")
def api_leaderboard():
    if not _has_access_cookie():
        return jsonify({"error": "unauthorized"}), 401
    rows = get_leaderboard()
    codes = load_codes()
    return jsonify({
        "total_levels": len(codes),
        "rows": [dict(r) for r in rows],
    })

@app.route("/api/server-peers")
def api_server_peers():
    """Return all participants on the same SAP server as the given sap_user.

    GET /api/server-peers?sap_user=JSMITH
    Response: { "server": "sap2", "peers": [{name, sap_username, wg_ip, sap_client}, ...] }

    Used by the Level 2 "Find Your Lab Partner" widget so participants can
    identify colleagues with a different VPN IP on the same physical server.
    """
    if not _has_access_cookie():
        return jsonify({"error": "unauthorized"}), 401
    sap_user = request.args.get("sap_user", "").upper().strip()
    if not sap_user:
        return jsonify({"error": "sap_user param required"}), 400
    db = get_db()
    row = db.execute(
        "SELECT server FROM participants WHERE sap_username=?", (sap_user,)
    ).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "not_found"}), 404
    server = row["server"]
    peers = db.execute(
        "SELECT name, sap_username, wg_ip, sap_client "
        "FROM participants WHERE server=? ORDER BY wg_ip",
        (server,),
    ).fetchall()
    db.close()
    return jsonify({
        "server": server or "unknown",
        "peers": [dict(p) for p in peers],
    })

# ---------------------------------------------------------------------------
# Step 1 — Self-registration (email only, no code needed)
# Creates a pending_registrations record; admin approves from admin panel.
# ---------------------------------------------------------------------------

REQUEST_TEMPLATE = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Request Access — Pathlock</title>
{{ style | safe }}
<style>
  .reg-box{max-width:540px;margin:80px auto;padding:40px;background:#12121f;border-radius:12px;border:1px solid #1e1e35}
  .reg-box h1{font-size:1.8rem;margin:0 0 8px;color:#fff}
  .reg-box .sub{color:#aaa;margin:0 0 32px;font-size:0.95rem}
  .field{margin-bottom:18px}
  .field label{display:block;color:#bbb;font-size:0.85rem;margin-bottom:6px;letter-spacing:.04em}
  .field input,.field textarea{width:100%;background:#0f0f1a;border:1px solid #2a2a45;border-radius:6px;
    padding:10px 14px;color:#fff;font-size:1rem;box-sizing:border-box}
  .field textarea{height:80px;resize:vertical}
  .field input:focus,.field textarea:focus{outline:none;border-color:#4f8ef7}
  .msg-err{background:#3a1a1a;border:1px solid #c0392b;color:#e74c3c;padding:12px 16px;border-radius:6px;margin-bottom:20px;font-size:0.9rem}
  .msg-ok{background:#0f2a1a;border:1px solid #27ae60;color:#2ecc71;padding:12px 16px;border-radius:6px;margin-bottom:20px;font-size:0.9rem}
  .submit-btn{width:100%;padding:12px;background:#c8102e;color:#fff;border:none;border-radius:6px;font-size:1rem;font-weight:600;cursor:pointer;margin-top:8px}
  .submit-btn:hover{background:#a00d24}
  .pending-box{text-align:center;padding:40px 20px}
  .pending-box .icon{font-size:4rem;margin-bottom:16px}
  .pending-box h2{color:#fff;margin:0 0 12px}
  .pending-box p{color:#aaa;max-width:420px;margin:0 auto}
</style>
</head>
<body>
{{ topbar | safe }}
<div class="reg-box">
  {% if submitted %}
    <div class="pending-box">
      <div class="icon">📬</div>
      <h2>Request received</h2>
      <p>Thanks <strong>{{ name }}</strong>. We've received your request and will review it shortly.<br><br>
         Once approved, come back and <a href="/enroll" style="color:#c8102e;font-weight:600">enroll in your class →</a> using the class code your instructor provides.</p>
    </div>
  {% else %}
    <h1>Request Access</h1>
    <p class="sub">Create your account. Your request will be reviewed by Pathlock before you can enroll.</p>
    {% if msg %}<div class="msg-{{ msg_type }}">{{ msg }}</div>{% endif %}
    <form method="POST">
      <div class="field"><label>Full name *</label>
        <input name="name" value="{{ form_name }}" required placeholder="Jane Smith"></div>
      <div class="field"><label>Work email *</label>
        <input name="email" type="email" value="{{ form_email }}" required placeholder="jane@company.com"></div>
      <div class="field"><label>Company</label>
        <input name="company" value="{{ form_company }}" placeholder="ACME Corp"></div>
      <div class="field"><label>Password *</label>
        <input name="password" type="password" required placeholder="Choose a password (min 8 characters)"></div>
      <div class="field"><label>Confirm password *</label>
        <input name="password2" type="password" required placeholder="Repeat your password"></div>
      <div class="field"><label>Why do you want access? (optional)</label>
        <textarea name="message" placeholder="e.g. attending the SAP security workshop on July 30th">{{ form_message }}</textarea></div>
      <button class="submit-btn" type="submit">Request Access →</button>
    </form>
    <p style="text-align:center;color:#555;font-size:0.85rem;margin-top:20px">Already have an account? <a href="/login" style="color:#888">Sign in →</a></p>
  {% endif %}
</div>
</body></html>
"""

@app.route("/register", methods=["GET", "POST"])
def register():
    """Step 1: create account + request access. Admin approves; user then enrolls."""
    if _is_logged_in():
        return redirect("/profile")
    ip = request.remote_addr or "unknown"

    if request.method == "GET":
        return render_template_string(REQUEST_TEMPLATE,
            style=STYLE, topbar=_topbar("/register", authenticated=False),
            submitted=False, msg=None, msg_type="ok",
            form_name="", form_email="", form_company="", form_message="")

    # POST — rate limit first
    if not _check_rate_limit(ip):
        return render_template_string(REQUEST_TEMPLATE,
            style=STYLE, topbar=_topbar("/register", authenticated=False),
            submitted=False, msg="Too many requests. Please wait a moment.", msg_type="err",
            form_name="", form_email="", form_company="", form_message="")

    name      = _sanitize_text(request.form.get("name", ""), 80)
    email     = _sanitize_text(request.form.get("email", "").lower(), 120)
    company   = _sanitize_text(request.form.get("company", ""), 80)
    message   = _sanitize_text(request.form.get("message", ""), 400)
    password  = request.form.get("password", "")
    password2 = request.form.get("password2", "")

    def err(msg):
        return render_template_string(REQUEST_TEMPLATE,
            style=STYLE, topbar=_topbar("/register", authenticated=False),
            submitted=False, msg=msg, msg_type="err",
            form_name=name, form_email=email, form_company=company, form_message=message)

    if not name:
        return err("Full name is required.")
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return err("A valid work email is required.")
    if not password or len(password) < 8:
        return err("Password must be at least 8 characters.")
    if password != password2:
        return err("Passwords do not match.")

    pw_hash = _hash_password(password)
    db = get_db()
    # Already fully registered as participant
    if db.execute("SELECT 1 FROM participants WHERE email=?", (email,)).fetchone():
        db.close()
        return err("That email is already enrolled. Sign in at /login.")
    # Already has a pending request
    existing = db.execute(
        "SELECT status FROM pending_registrations WHERE email=?", (email,)).fetchone()
    if existing:
        # Update password if they're re-submitting
        db.execute("UPDATE pending_registrations SET password_hash=? WHERE email=?", (pw_hash, email))
        db.commit()
        db.close()
        session["user_email"] = email
        if existing["status"] == "pending":
            return render_template_string(REQUEST_TEMPLATE,
                style=STYLE, topbar=_topbar("/register", authenticated=False),
                submitted=True, name=name)
        if existing["status"] == "approved":
            return redirect("/enroll")
        return err("Your previous request was not approved. Contact jonathan.stross@pathlock.com for help.")

    db.execute(
        "INSERT INTO pending_registrations (name, email, company, message, password_hash) VALUES (?,?,?,?,?)",
        (name, email, company, message, pw_hash))
    db.commit()
    db.close()
    app.logger.info("New access request from %s <%s>", name, email)
    session["user_email"] = email  # log them in immediately so they can check /profile

    return render_template_string(REQUEST_TEMPLATE,
        style=STYLE, topbar=_topbar("/register", authenticated=False),
        submitted=True, name=name)


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

LOGIN_TEMPLATE = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Sign In — Pathlock Academy</title>
{{ style | safe }}
<style>
  .auth-box{max-width:440px;margin:80px auto;padding:40px;background:#12121f;border-radius:12px;border:1px solid #1e1e35}
  .auth-box h1{font-size:1.8rem;margin:0 0 8px;color:#fff}
  .auth-box .sub{color:#aaa;margin:0 0 28px;font-size:0.95rem}
  .field{margin-bottom:18px}
  .field label{display:block;color:#bbb;font-size:0.85rem;margin-bottom:6px;letter-spacing:.04em}
  .field input{width:100%;background:#0f0f1a;border:1px solid #2a2a45;border-radius:6px;
    padding:10px 14px;color:#fff;font-size:1rem;box-sizing:border-box}
  .field input:focus{outline:none;border-color:#4f8ef7}
  .msg-err{background:#3a1a1a;border:1px solid #c0392b;color:#e74c3c;padding:12px 16px;border-radius:6px;margin-bottom:20px;font-size:0.9rem}
  .submit-btn{width:100%;padding:12px;background:#c8102e;color:#fff;border:none;border-radius:6px;font-size:1rem;font-weight:600;cursor:pointer;margin-top:8px}
  .submit-btn:hover{background:#a00d24}
  .links{text-align:center;margin-top:18px;font-size:0.85rem;color:#555}
  .links a{color:#888;text-decoration:none}
  .links a:hover{color:#bbb}
</style>
</head>
<body>
{{ topbar | safe }}
<div class="auth-box">
  <h1>Sign In</h1>
  <p class="sub">Use the email and password you set when you registered.</p>
  {% if msg %}<div class="msg-err">{{ msg }}</div>{% endif %}
  <form method="POST">
    <div class="field"><label>Email</label>
      <input name="email" type="email" value="{{ form_email }}" required autofocus placeholder="jane@company.com"></div>
    <div class="field"><label>Password</label>
      <input name="password" type="password" required placeholder="••••••••"></div>
    <button class="submit-btn" type="submit">Sign In →</button>
  </form>
  <div class="links">
    No account yet? <a href="/register">Request access</a> &nbsp;·&nbsp;
    Already approved? <a href="/enroll">Enroll in a class</a>
  </div>
</div>
</body></html>"""

@app.route("/login", methods=["GET", "POST"])
def login():
    if _is_logged_in():
        return redirect("/profile")
    if request.method == "GET":
        return render_template_string(LOGIN_TEMPLATE,
            style=STYLE, topbar=_topbar("/login", authenticated=False),
            msg=None, form_email="")
    email    = _sanitize_text(request.form.get("email", "").lower(), 120)
    password = request.form.get("password", "")

    def err(msg):
        return render_template_string(LOGIN_TEMPLATE,
            style=STYLE, topbar=_topbar("/login", authenticated=False),
            msg=msg, form_email=email)

    if not email or not password:
        return err("Email and password are required.")

    pw_hash = _hash_password(password)
    db = get_db()
    # Check enrolled participants first
    p = db.execute("SELECT * FROM participants WHERE email=? AND password_hash=?", (email, pw_hash)).fetchone()
    if p:
        db.close()
        session["user_email"] = email
        return redirect("/profile")
    # Check pending registrations
    pr = db.execute("SELECT * FROM pending_registrations WHERE email=? AND password_hash=?", (email, pw_hash)).fetchone()
    db.close()
    if pr:
        session["user_email"] = email
        return redirect("/profile")
    return err("Incorrect email or password.")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------------------------------------------------------------------
# Profile page
# ---------------------------------------------------------------------------

PROFILE_TEMPLATE = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>My Profile — Pathlock Academy</title>
{{ style | safe }}
<style>
  .profile-box{max-width:680px;margin:50px auto;padding:0 24px 60px}
  .profile-header{background:#12121f;border:1px solid #1e1e35;border-radius:12px;padding:28px 32px;margin-bottom:20px;display:flex;align-items:center;gap:20px}
  .profile-avatar{width:64px;height:64px;background:#c8102e;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.8rem;font-weight:700;color:#fff;flex-shrink:0}
  .profile-name{font-size:1.4rem;font-weight:700;color:#fff;margin:0 0 4px}
  .profile-email{color:#888;font-size:0.9rem;margin:0}
  .card{background:#12121f;border:1px solid #1e1e35;border-radius:10px;padding:22px 28px;margin-bottom:16px}
  .card h3{font-size:0.75rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#555;margin:0 0 16px}
  .row{display:flex;align-items:center;gap:12px;margin-bottom:10px}
  .row:last-child{margin-bottom:0}
  .lbl{color:#888;font-size:0.88rem;min-width:140px;flex-shrink:0}
  .val{color:#fff;font-size:0.88rem;font-weight:600}
  .mono{font-family:monospace;color:#ffd700}
  .badge-pending{background:#2a2210;border:1px solid #f39c12;color:#f39c12;padding:3px 10px;border-radius:4px;font-size:0.78rem;font-weight:700}
  .badge-approved{background:#0f2a1a;border:1px solid #27ae60;color:#2ecc71;padding:3px 10px;border-radius:4px;font-size:0.78rem;font-weight:700}
  .badge-rejected{background:#3a1a1a;border:1px solid #c0392b;color:#e74c3c;padding:3px 10px;border-radius:4px;font-size:0.78rem;font-weight:700}
  .badge-enrolled{background:#0a1e2a;border:1px solid #2980b9;color:#3498db;padding:3px 10px;border-radius:4px;font-size:0.78rem;font-weight:700}
  .badge-expired{background:#3a1a1a;border:1px solid #e74c3c;color:#e74c3c;padding:3px 10px;border-radius:4px;font-size:0.78rem;font-weight:700}
  .progress-bar-bg{background:#1a1a2e;border-radius:4px;height:10px;flex:1;overflow:hidden}
  .progress-bar-fill{background:#c8102e;height:100%;border-radius:4px;transition:width .4s}
  .cred-grid{display:grid;grid-template-columns:140px 1fr;gap:6px 16px;font-size:0.88rem;margin-top:4px}
  .cred-lbl{color:#666;font-size:0.75rem;text-transform:uppercase;letter-spacing:.06em;align-self:center}
  .cred-val{font-family:monospace;color:#ffd700;font-weight:600}
  .cred-val.plain{color:#e0e0e0;font-family:inherit}
  .btn{display:inline-block;background:#c8102e;color:#fff;padding:10px 22px;border-radius:6px;text-decoration:none;font-size:0.9rem;font-weight:600;margin-top:8px}
  .btn:hover{background:#a00d24}
  .btn.sec{background:#1e1e35;color:#aaa}
  .btn.sec:hover{background:#2a2a45;color:#fff}
  .btn.grn{background:#1a6632;color:#2ecc71}
  .btn.grn:hover{background:#145228}
  .info-msg{background:#1a1a2e;border:1px solid #2a2a45;border-radius:8px;padding:16px 20px;color:#aaa;font-size:0.88rem;line-height:1.7}
  .countdown{display:flex;gap:12px;margin-top:4px}
  .countdown-unit{background:#1a1a2e;border:1px solid #2a2a45;border-radius:8px;padding:10px 16px;text-align:center;min-width:60px}
  .countdown-num{font-size:1.6rem;font-weight:700;color:#fff;display:block;line-height:1}
  .countdown-label{font-size:0.7rem;color:#666;text-transform:uppercase;letter-spacing:.06em;margin-top:4px}
  .expired-warn{background:#2a0a0a;border:1px solid #e74c3c;border-radius:8px;padding:14px 18px;color:#e74c3c;font-size:0.88rem;margin-top:8px}
</style>
</head>
<body>
{{ topbar | safe }}
<div class="profile-box">
  <div class="profile-header">
    <div class="profile-avatar">{{ name[0].upper() if name else '?' }}</div>
    <div>
      <div class="profile-name">{{ name }}</div>
      <div class="profile-email">{{ email }}{% if company %} &nbsp;·&nbsp; {{ company }}{% endif %}</div>
    </div>
  </div>

  <!-- Access / Status card -->
  <div class="card">
    <h3>Access Status</h3>
    <div class="row">
      <span class="lbl">Pathlock Approval</span>
      {% if enrolled %}
        {% if expired %}<span class="badge-expired">⏰ Access Expired</span>
        {% else %}<span class="badge-enrolled">✓ Enrolled</span>{% endif %}
      {% elif approval_status == 'approved' %}
        <span class="badge-approved">✓ Approved — ready to enroll</span>
      {% elif approval_status == 'pending' %}
        <span class="badge-pending">⏳ Pending review</span>
      {% else %}
        <span class="badge-rejected">✗ Not approved</span>
      {% endif %}
    </div>
    {% if enrolled %}
    <div class="row"><span class="lbl">Class</span><span class="val">{{ class_name or '—' }}</span></div>
    <div class="row"><span class="lbl">SAP Username</span><span class="val mono">{{ sap_username }}</span></div>
    <div class="row"><span class="lbl">SAP Client</span><span class="val mono">{{ sap_client }}</span></div>
    <div class="row"><span class="lbl">SAP Host</span><span class="val mono">{{ sap_host }}:32{{ sap_sysnr.zfill(2) }}</span></div>
    {% endif %}
  </div>

  {% if enrolled %}
  <!-- Credentials card -->
  <div class="card">
    <h3>SAP Credentials &amp; VPN</h3>
    <div class="cred-grid">
      <span class="cred-lbl">SAP Username</span><span class="cred-val">{{ sap_username }}</span>
      <span class="cred-lbl">Initial Password</span><span class="cred-val">{{ temp_password }}</span>
      <span class="cred-lbl">System Nr</span><span class="cred-val">{{ sap_sysnr }}</span>
      <span class="cred-lbl">Client</span><span class="cred-val">{{ sap_client }}</span>
      <span class="cred-lbl">Host</span><span class="cred-val plain">{{ sap_host }}</span>
    </div>
    {% if wg_conf %}
    <div style="margin-top:18px">
      <a href="/download/{{ sap_username }}" class="btn grn">⬇ Download WireGuard Config</a>
      <span style="color:#666;font-size:0.8rem;margin-left:12px">Import this file into the WireGuard app to connect to the lab VPN.</span>
    </div>
    {% else %}
    <p style="color:#f39c12;font-size:0.85rem;margin-top:12px">⚠ VPN config not available — contact your instructor.</p>
    {% endif %}
  </div>

  <!-- Expiry / countdown card -->
  <div class="card">
    <h3>Access Expiry</h3>
    {% if expired %}
      <div class="expired-warn">⏰ Your access expired on {{ expires_at }} UTC. Contact your instructor to extend.</div>
    {% elif days_left is not none %}
      <p style="color:#aaa;font-size:0.85rem;margin:0 0 14px">Your SAP user and VPN will be automatically deprovisioned on <strong style="color:#fff">{{ expires_at }} UTC</strong></p>
      <div class="countdown">
        <div class="countdown-unit"><span class="countdown-num">{{ days_left }}</span><div class="countdown-label">days</div></div>
        <div class="countdown-unit"><span class="countdown-num">{{ hours_left }}</span><div class="countdown-label">hours</div></div>
      </div>
    {% else %}
      <p style="color:#666;font-size:0.85rem;margin:0">No expiry set — contact your instructor.</p>
    {% endif %}
  </div>

  <!-- Progress card -->
  <div class="card">
    <h3>Progress</h3>
    <div class="row"><span class="lbl">Levels completed</span><span class="val">{{ levels_done }} / {{ total_levels }}</span></div>
    <div class="row"><span class="lbl">Score</span><span class="val">{{ total_score }} pts</span></div>
    {% if total_levels > 0 %}
    <div class="row" style="gap:16px;margin-top:4px">
      <span class="lbl">Overall</span>
      <div class="progress-bar-bg"><div class="progress-bar-fill" style="width:{{ (levels_done / total_levels * 100)|int }}%"></div></div>
      <span style="color:#888;font-size:0.8rem;min-width:36px">{{ (levels_done / total_levels * 100)|int }}%</span>
    </div>
    {% endif %}
    <div style="margin-top:16px">
      <a href="/levels" class="btn">📖 Open Levels</a>
      <a href="/leaderboard" class="btn sec" style="margin-left:8px">🏆 Leaderboard</a>
    </div>
  </div>

  {% elif approval_status == 'approved' %}
  <div class="info-msg">
    ✅ Your access has been approved! Enter the class enrollment code your instructor gave you to get started.
    <br><br><a href="/enroll" class="btn" style="display:inline-block;margin-top:4px">Enroll in a class →</a>
  </div>
  {% else %}
  <div class="info-msg">
    ⏳ Your request is being reviewed by the Pathlock team. You'll be able to enroll once approved.<br>
    Questions? <a href="mailto:jonathan.stross@pathlock.com" style="color:#888">jonathan.stross@pathlock.com</a>
  </div>
  {% endif %}
</div>
</body></html>"""

@app.route("/profile")
def profile():
    if not _is_logged_in():
        return redirect("/login")
    status, user = _current_user()
    if not user:
        session.clear()
        return redirect("/login")

    db = get_db()
    codes = load_codes()
    total_levels = len(codes)

    if status == "enrolled":
        sap_username = user["sap_username"]
        sap_client   = user["sap_client"] or ""
        cls_row = db.execute("SELECT name FROM classes WHERE id=?", (user["class_id"],)).fetchone() if user["class_id"] else None
        class_name = cls_row["name"] if cls_row else ""
        levels_done = db.execute(
            "SELECT COUNT(DISTINCT level) FROM submissions WHERE participant=? AND correct=1",
            (sap_username,)).fetchone()[0]
        total_score = db.execute(
            "SELECT COALESCE(SUM(points),0) FROM submissions WHERE participant=? AND correct=1",
            (sap_username,)).fetchone()[0]
        db.close()

        # Expiry countdown
        expires_at = user["expires_at"] or ""
        days_left = None
        hours_left = None
        expired = False
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at)
                delta = exp_dt - datetime.utcnow()
                if delta.total_seconds() <= 0:
                    expired = True
                    days_left, hours_left = 0, 0
                else:
                    days_left  = delta.days
                    hours_left = delta.seconds // 3600
            except Exception:
                pass

        return render_template_string(PROFILE_TEMPLATE,
            style=STYLE, topbar=_topbar("/profile", authenticated=True),
            name=user["name"], email=user["email"], company=user["company"] or "",
            enrolled=True, approval_status="approved",
            sap_username=sap_username, sap_client=sap_client, class_name=class_name,
            temp_password=user["temp_password"] or "(see instructor)",
            sap_host=SAP_HOST, sap_sysnr=SAP_SYSNR,
            wg_conf=user["wg_conf"],
            expires_at=expires_at[:16].replace("T", " ") if expires_at else "",
            days_left=days_left, hours_left=hours_left, expired=expired,
            levels_done=levels_done, total_levels=total_levels, total_score=total_score)
    else:
        db.close()
        return render_template_string(PROFILE_TEMPLATE,
            style=STYLE, topbar=_topbar("/profile", authenticated=False),
            name=user["name"], email=user["email"], company=user["company"] or "",
            enrolled=False, approval_status=status,
            sap_username="", sap_client="", class_name="",
            temp_password="", sap_host="", sap_sysnr="", wg_conf=None,
            expires_at="", days_left=None, hours_left=None, expired=False,
            levels_done=0, total_levels=total_levels, total_score=0)


# ---------------------------------------------------------------------------
# Step 2 — Class enrollment (requires admin approval + class code)
# ---------------------------------------------------------------------------

ENROLL_TEMPLATE = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Enroll in a Class — Pathlock</title>
{{ style | safe }}
<style>
  .reg-box{max-width:540px;margin:80px auto;padding:40px;background:#12121f;border-radius:12px;border:1px solid #1e1e35}
  .reg-box h1{font-size:1.8rem;margin:0 0 8px;color:#fff}
  .reg-box .sub{color:#aaa;margin:0 0 32px;font-size:0.95rem}
  .field{margin-bottom:18px}
  .field label{display:block;color:#bbb;font-size:0.85rem;margin-bottom:6px;letter-spacing:.04em}
  .field input{width:100%;background:#0f0f1a;border:1px solid #2a2a45;border-radius:6px;
    padding:10px 14px;color:#fff;font-size:1rem;box-sizing:border-box}
  .field input:focus{outline:none;border-color:#4f8ef7}
  .field .hint{font-size:0.78rem;color:#666;margin-top:5px}
  .msg-err{background:#3a1a1a;border:1px solid #c0392b;color:#e74c3c;padding:12px 16px;border-radius:6px;margin-bottom:20px;font-size:0.9rem}
  .msg-ok{background:#0f2a1a;border:1px solid #27ae60;color:#2ecc71;padding:12px 16px;border-radius:6px;margin-bottom:20px;font-size:0.9rem}
  .submit-btn{width:100%;padding:12px;background:#c8102e;color:#fff;border:none;border-radius:6px;font-size:1rem;font-weight:600;cursor:pointer;margin-top:8px}
  .submit-btn:hover{background:#a00d24}
  .waiver{font-size:0.8rem;color:#666;margin-top:16px;line-height:1.5}
  .waiver a{color:#888}
  .success-box{text-align:center;padding:20px 0}
  .success-box .icon{font-size:3rem;margin-bottom:12px}
  .cred-block{background:#0f0f1a;border:1px solid #2a2a45;border-radius:8px;padding:16px;margin:16px 0;font-family:monospace;font-size:0.9rem;line-height:1.8}
  .cred-block .label{color:#aaa;font-size:0.75rem;text-transform:uppercase;letter-spacing:.08em}
  .cred-block .val{color:#ffd700;font-weight:bold}
</style>
</head>
<body>
{{ topbar | safe }}
<div class="reg-box">
  {% if success %}
    <div class="success-box">
      <div class="icon">🎉</div>
      <h1>You're in!</h1>
      <p style="color:#aaa;margin:0 0 20px">Enrolled in <strong style="color:#fff">{{ class_name }}</strong>.<br>
      Your SAP credentials and VPN config are below.</p>
      <div class="cred-block">
        <div class="label">SAP Username</div><div class="val">{{ sap_username }}</div>
        <div class="label">Temporary Password</div><div class="val">{{ temp_password }}</div>
        <div class="label">SAP Host</div><div class="val">{{ sap_host }}</div>
        <div class="label">System Nr</div><div class="val">{{ sap_sysnr }}</div>
        <div class="label">Client</div><div class="val">{{ sap_client }}</div>
      </div>
      {% if wg_conf %}
        <a href="/download/{{ sap_username }}" class="submit-btn" style="display:block;text-align:center;text-decoration:none;padding:12px;margin-top:8px">
          ⬇ Download WireGuard Config
        </a>
      {% endif %}
      {% if sap_warn %}<p style="color:#f39c12;font-size:0.85rem;margin-top:12px">⚠ {{ sap_warn }}</p>{% endif %}
      {% if wg_warn %}<p style="color:#f39c12;font-size:0.85rem">⚠ {{ wg_warn }}</p>{% endif %}
      <p style="color:#666;font-size:0.8rem;margin-top:16px">
        Access will be revoked after this session and data will be deleted immediately.<br>
        Contact <a href="mailto:jonathan.stross@pathlock.com" style="color:#888">jonathan.stross@pathlock.com</a> for prolonged access.
      </p>
    </div>
  {% else %}
    <h1>Enroll in a Class</h1>
    <p class="sub">Your request must be approved before you can enroll. Enter your SAP username and the class code your instructor provided.</p>
    {% if msg %}<div class="msg-{{ msg_type }}">{{ msg }}</div>{% endif %}
    <form method="POST">
      <div class="field"><label>Choose your SAP username *</label>
        <input name="sap_username" value="{{ form_sap }}" required placeholder="JSMITH" maxlength="12"
               style="text-transform:uppercase">
        <div class="hint">3–12 characters, letters/digits/underscore only. This becomes your login on the SAP system.</div></div>
      <div class="field"><label>Class enrollment code *</label>
        <input name="enroll_code" value="{{ form_code }}" required placeholder="provided by your instructor">
        <div class="hint">Each class has a unique code — ask your instructor if you don't have one.</div></div>
      <div style="margin-top:20px">
        <label style="display:flex;align-items:flex-start;gap:10px;cursor:pointer;color:#aaa;font-size:0.85rem">
          <input type="checkbox" name="w_agree" style="margin-top:2px;width:auto">
          I accept that this system is for training purposes only, my activity may be monitored, and access will be revoked after the session.
        </label>
      </div>
      <button class="submit-btn" type="submit">Enroll →</button>
    </form>
  {% endif %}
</div>
</body></html>
"""

@app.route("/enroll", methods=["GET", "POST"])
def enroll():
    """Step 2: approved users enroll in a specific class using the class code."""
    if not _is_logged_in():
        return redirect("/login")
    # If already enrolled, go straight to profile
    if _is_enrolled():
        return redirect("/profile")
    # If not yet approved, send to profile so they can see their status
    logged_email = session["user_email"]
    db_check = get_db()
    pr_check = db_check.execute(
        "SELECT status FROM pending_registrations WHERE email=?", (logged_email,)).fetchone()
    db_check.close()
    if not pr_check or pr_check["status"] != "approved":
        return redirect("/profile")

    ip = request.remote_addr or "unknown"
    logged_email = session["user_email"]

    if request.method == "GET":
        return render_template_string(ENROLL_TEMPLATE,
            style=STYLE, topbar=_topbar("/enroll", authenticated=False),
            success=False, msg=None, msg_type="ok",
            form_sap="", form_code="")

    if not _check_rate_limit(ip):
        return render_template_string(ENROLL_TEMPLATE,
            style=STYLE, topbar=_topbar("/enroll", authenticated=False),
            success=False, msg="Too many attempts. Please wait.", msg_type="err",
            form_sap="", form_code="")

    sap_username = _sanitize_text(request.form.get("sap_username", "").upper(), 12)
    enroll_code  = _sanitize_text(request.form.get("enroll_code", "").strip(), 80)

    def err(msg):
        return render_template_string(ENROLL_TEMPLATE,
            style=STYLE, topbar=_topbar("/enroll", authenticated=False),
            success=False, msg=msg, msg_type="err",
            form_sap=sap_username, form_code=enroll_code)

    if not sap_username or len(sap_username) < 3 or len(sap_username) > 12:
        return err("SAP username must be 3–12 characters.")
    if not re.match(r'^[A-Z0-9_]+$', sap_username):
        return err("SAP username may only contain letters, digits and underscore.")
    if not enroll_code:
        return err("Enrollment code is required.")
    if not request.form.get("w_agree"):
        return err("You must accept the participant agreement to enroll.")

    sap_defaults = {"SAP*","DDIC","DEVELOPER","SAPCPIC","TMSADM","EARLYWATCH",
                    "RFCUSER","SOLMAN_BTC","SM_INTERN","SAPSYS","SAPJSF","SAPABC"}
    if sap_username in sap_defaults:
        return err("That SAP username is a system default and cannot be used.")

    db = get_db()

    # Check approval status
    pending = db.execute(
        "SELECT * FROM pending_registrations WHERE email=?", (logged_email,)).fetchone()
    if not pending:
        db.close()
        return err("No access request found for your account. Please contact your instructor.")
    if pending["status"] == "pending":
        db.close()
        return err("Your request is still pending admin approval. Check your profile for status.")
    if pending["status"] == "rejected":
        db.close()
        return err("Your access request was not approved. Contact jonathan.stross@pathlock.com.")

    # Already enrolled
    if db.execute("SELECT 1 FROM participants WHERE email=?", (logged_email,)).fetchone():
        db.close()
        session["user_email"] = logged_email
        return redirect("/profile")
    if db.execute("SELECT 1 FROM participants WHERE sap_username=?", (sap_username,)).fetchone():
        db.close()
        return err(f"SAP username '{sap_username}' is already taken — choose another.")

    # Validate class code
    cls = db.execute(
        "SELECT * FROM classes WHERE enroll_code=? AND active=1", (enroll_code,)).fetchone()
    if not cls:
        db.close()
        return err("Invalid or inactive enrollment code. Check with your instructor.")

    # Assign slot
    server_alias, slot_client = _assign_slot(sap_username)
    if server_alias is None:
        db.close()
        return err("The workshop is fully booked. Contact your instructor.")

    srv_info = SAP_SERVERS.get(server_alias, {})
    slot_conn_params = {
        "host":   srv_info.get("host",  SAP_HOST),
        "sysnr":  srv_info.get("sysnr", SAP_SYSNR),
        "client": slot_client,
    }

    if SAP_AVAILABLE and user_exists(sap_username, conn_params=slot_conn_params):
        db.close()
        return err(f"SAP user '{sap_username}' already exists — choose a different username.")

    name = pending["name"]
    sap_ok, temp_password, sap_error = create_workshop_user(
        sap_username=sap_username,
        first_name=name.split()[0] if name.split() else name,
        last_name=" ".join(name.split()[1:]) if len(name.split()) > 1 else "",
        email=logged_email,
        conn_params=slot_conn_params,
    )
    sap_warn = None
    if not sap_ok:
        sap_warn = f"SAP user could not be created automatically: {sap_error}. Your instructor will create it manually."
        temp_password = "(see instructor)"

    wg_ok, wg_ip, wg_conf, wg_error = create_customer_peer(
        display_name=name,
        server_alias=server_alias,
    )
    wg_warn = None
    if not wg_ok:
        wg_warn = f"VPN config could not be created: {wg_error}. Your instructor will provide your WireGuard config."
        wg_ip = wg_conf = None

    from datetime import timedelta
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat(timespec="seconds")

    try:
        db.execute(
            "INSERT INTO participants "
            "(name, email, sap_username, company, password_hash, class_id, sap_created, wg_ip, wg_conf, server, sap_client, waiver_accepted, temp_password, expires_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,1,?,?)",
            (name, logged_email, sap_username, pending["company"], pending["password_hash"],
             cls["id"], 1 if sap_ok else 0, wg_ip, wg_conf, server_alias, slot_client,
             temp_password, expires_at))
        db.commit()
    except sqlite3.IntegrityError as exc:
        db.close()
        return err(f"Enrollment failed: {exc}")

    db.close()
    return render_template_string(ENROLL_TEMPLATE,
        style=STYLE, topbar=_topbar("/enroll", authenticated=True),
        success=True,
        class_name=cls["name"],
        sap_username=sap_username,
        temp_password=temp_password,
        sap_host=SAP_HOST,
        sap_sysnr=SAP_SYSNR,
        sap_client=slot_client,
        wg_conf=wg_conf,
        sap_warn=sap_warn,
        wg_warn=wg_warn,
        sap_available=SAP_AVAILABLE)



@app.route("/download/<sap_username>")
def download_wg_conf(sap_username):
    """Serve the WireGuard .conf for a registered participant."""
    if not _has_access_cookie():
        return redirect("/register")
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
    if not _has_access_cookie():
        return redirect("/register")
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
            return render_template_string(SUBMIT_TEMPLATE, msg=msg, msg_type=msg_type, levels=codes, locked_levels=LOCKED_LEVELS)

        if participant["locked"]:
            msg, msg_type = "Your account has been locked by the instructor. Please raise your hand.", "err"
            db.close()
            return render_template_string(SUBMIT_TEMPLATE, msg=msg, msg_type=msg_type, levels=codes, locked_levels=LOCKED_LEVELS)

        # Check not already submitted correctly
        already = db.execute(
            "SELECT * FROM submissions WHERE participant=? AND level=? AND correct=1",
            (sap_username, level)).fetchone()
        if already:
            db.close()
            return render_template_string("""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Nice try</title>""" + STYLE + """
<style>
  .caught{display:flex;flex-direction:column;align-items:center;justify-content:center;
          min-height:80vh;text-align:center;padding:40px}
  .caught .emoji{font-size:6rem;margin-bottom:24px;animation:shake .4s ease infinite alternate}
  @keyframes shake{from{transform:rotate(-6deg)}to{transform:rotate(6deg)}}
  .caught h1{font-size:2.4rem;color:#c8102e;margin:0 0 16px}
  .caught p{color:#aaa;font-size:1.1rem;max-width:480px;margin:0 0 32px}
  .caught .sub{font-size:0.85rem;color:#555;margin-top:8px}
</style>
</head>
<body>
""" + _topbar("/submit") + """
  <div class="caught">
    <div class="emoji">🕵️</div>
    <h1>The joke's on you.</h1>
    <p>You already completed <strong>""" + level + """</strong> and collected those points.<br>
       Stop trying to redeem the code multiple times — the system remembers everything.</p>
    <a href="/submit" class="btn">← Back to Submit</a>
    <p class="sub">Each code can only be redeemed once per participant. Nice try though.</p>
  </div>
</body>
</html>""")

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

    return render_template_string(SUBMIT_TEMPLATE, msg=msg, msg_type=msg_type, levels=codes, locked_levels=LOCKED_LEVELS)

# ---------------------------------------------------------------------------
# Admin — pending approvals
# ---------------------------------------------------------------------------

@app.route("/admin/approvals")
def admin_approvals():
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    db = get_db()
    pending = db.execute(
        "SELECT * FROM pending_registrations ORDER BY submitted_at DESC").fetchall()
    db.close()
    td = "style='padding:6px 12px;vertical-align:middle'"
    th = "style='text-align:left;padding:6px 12px;color:#aaa;white-space:nowrap'"
    rows = ""
    for p in pending:
        badge_color = {"pending": "#f39c12", "approved": "#2ecc71", "rejected": "#e74c3c"}.get(p["status"], "#aaa")
        badge = f"<span style='color:{badge_color};font-weight:bold'>{p['status'].upper()}</span>"
        actions = ""
        if p["status"] == "pending":
            actions = (
                f"<form method='POST' action='/admin/approvals/{p['id']}/approve' style='display:inline'>"
                f"<button style='background:#27ae60;color:#fff;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:0.85em;margin-right:4px'>✓ Approve</button></form>"
                f"<form method='POST' action='/admin/approvals/{p['id']}/reject' style='display:inline'>"
                f"<button style='background:#c0392b;color:#fff;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:0.85em'>✗ Reject</button></form>"
            )
        actions += (
            f"<form method='POST' action='/admin/approvals/{p['id']}/delete' style='display:inline'"
            f" onsubmit=\"return confirm('Delete {p['name']} permanently?')\">"
            f"<button style='background:#555;color:#fff;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:0.85em;margin-left:4px'>🗑 Delete</button></form>"
        )
        rows += (
            f"<tr style='border-top:1px solid #333'>"
            f"<td {td}>{p['name']}</td>"
            f"<td {td} style='color:#aaa;font-size:0.85em'>{p['email']}</td>"
            f"<td {td} style='color:#aaa;font-size:0.85em'>{p['company'] or '—'}</td>"
            f"<td {td} style='color:#aaa;font-size:0.8em;max-width:240px'>{p['message'] or '—'}</td>"
            f"<td {td}>{badge}</td>"
            f"<td {td} style='color:#aaa;font-size:0.8em'>{(p['submitted_at'] or '')[:16]}</td>"
            f"<td {td}>{actions}</td>"
            f"</tr>"
        )
    html = (
        f"<html><body style='font-family:monospace;background:#111;color:#eee;padding:20px'>"
        f"<p><a href='/admin' style='color:#4f8ef7'>← Back to Admin</a></p>"
        f"<h2>Access Requests ({len(pending)})</h2>"
        f"<table style='border-collapse:collapse;width:100%'>"
        f"<tr><th {th}>Name</th><th {th}>Email</th><th {th}>Company</th>"
        f"<th {th}>Message</th><th {th}>Status</th><th {th}>Submitted</th><th {th}>Actions</th></tr>"
        f"{rows}</table></body></html>"
    )
    return html

@app.route("/admin/approvals/<int:req_id>/approve", methods=["POST"])
def admin_approve(req_id):
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    db = get_db()
    db.execute("UPDATE pending_registrations SET status='approved' WHERE id=?", (req_id,))
    db.commit()
    db.close()
    return redirect("/admin/approvals")

@app.route("/admin/approvals/<int:req_id>/reject", methods=["POST"])
def admin_reject(req_id):
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    db = get_db()
    db.execute("UPDATE pending_registrations SET status='rejected' WHERE id=?", (req_id,))
    db.commit()
    db.close()
    return redirect("/admin/approvals")

@app.route("/admin/approvals/<int:req_id>/delete", methods=["POST"])
def admin_delete_request(req_id):
    """Permanently delete an access request (and the participant record if enrolled)."""
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    db = get_db()
    row = db.execute("SELECT email FROM pending_registrations WHERE id=?", (req_id,)).fetchone()
    if row:
        email = row["email"]
        # Also remove participant row + submissions if they enrolled
        p = db.execute("SELECT sap_username, wg_ip, server, sap_client FROM participants WHERE email=?", (email,)).fetchone()
        if p:
            uname = p["sap_username"]
            # Free slot
            db.execute("UPDATE slots SET assigned_to=NULL, assigned_at=NULL WHERE assigned_to=?", (uname,))
            db.execute("DELETE FROM submissions WHERE participant=?", (uname,))
            db.execute("DELETE FROM participants WHERE sap_username=?", (uname,))
            # Best-effort SAP + WG cleanup (fire and forget)
            try:
                conn_params = None
                if p["server"] and p["sap_client"] and p["server"] in SAP_SERVERS:
                    conn_params = {"host": SAP_SERVERS[p["server"]]["host"],
                                   "sysnr": SAP_SERVERS[p["server"]]["sysnr"],
                                   "client": p["sap_client"]}
                delete_sap_user(uname, conn_params=conn_params)
                if p["wg_ip"]:
                    remove_customer_peer(p["wg_ip"], server_alias=p["server"])
            except Exception as e:
                app.logger.warning("Cleanup error for %s: %s", uname, e)
        db.execute("DELETE FROM pending_registrations WHERE id=?", (req_id,))
        db.commit()
    db.close()
    return redirect("/admin/approvals")

# ---------------------------------------------------------------------------
# Admin — class management
# ---------------------------------------------------------------------------

@app.route("/admin/classes")
def admin_classes():
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    db = get_db()
    classes = db.execute("SELECT * FROM classes ORDER BY created_at DESC").fetchall()
    db.close()
    td = "style='padding:6px 12px;vertical-align:middle'"
    th = "style='text-align:left;padding:6px 12px;color:#aaa;white-space:nowrap'"
    rows = ""
    for c in classes:
        status = "<span style='color:#2ecc71'>active</span>" if c["active"] else "<span style='color:#555'>inactive</span>"
        toggle_label = "Deactivate" if c["active"] else "Activate"
        toggle_color = "#e67e22" if c["active"] else "#27ae60"
        rows += (
            f"<tr style='border-top:1px solid #333'>"
            f"<td {td}><strong style='color:#ffd700'>{c['name']}</strong></td>"
            f"<td {td} style='color:#aaa;font-size:0.85em'>{c['description'] or '—'}</td>"
            f"<td {td}><code style='background:#1a1a2e;padding:2px 8px;border-radius:4px;color:#4f8ef7'>{c['enroll_code']}</code></td>"
            f"<td {td}>{status}</td>"
            f"<td {td} style='color:#aaa;font-size:0.8em'>{(c['created_at'] or '')[:16]}</td>"
            f"<td {td}>"
            f"<form method='POST' action='/admin/classes/{c['id']}/toggle' style='display:inline'>"
            f"<button style='background:{toggle_color};color:#fff;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:0.85em'>{toggle_label}</button></form>"
            f"</td></tr>"
        )
    html = (
        f"<html><body style='font-family:monospace;background:#111;color:#eee;padding:20px'>"
        f"<p><a href='/admin' style='color:#4f8ef7'>← Back to Admin</a></p>"
        f"<h2>Classes</h2>"
        f"<form method='POST' action='/admin/classes/create' style='margin-bottom:24px'>"
        f"<input name='name' placeholder='Class name' required style='background:#1a1a2e;border:1px solid #333;color:#fff;padding:6px 10px;border-radius:4px;margin-right:8px'>"
        f"<input name='description' placeholder='Description (optional)' style='background:#1a1a2e;border:1px solid #333;color:#fff;padding:6px 10px;border-radius:4px;margin-right:8px;width:220px'>"
        f"<input name='enroll_code' placeholder='Enrollment code' required style='background:#1a1a2e;border:1px solid #333;color:#fff;padding:6px 10px;border-radius:4px;margin-right:8px'>"
        f"<button type='submit' style='background:#c8102e;color:#fff;border:none;padding:6px 16px;border-radius:4px;cursor:pointer'>Create Class</button>"
        f"</form>"
        f"<table style='border-collapse:collapse;width:100%'>"
        f"<tr><th {th}>Name</th><th {th}>Description</th><th {th}>Enroll Code</th>"
        f"<th {th}>Status</th><th {th}>Created</th><th {th}>Actions</th></tr>"
        f"{rows}</table></body></html>"
    )
    return html

@app.route("/admin/classes/create", methods=["POST"])
def admin_class_create():
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    name        = _sanitize_text(request.form.get("name", ""), 80)
    description = _sanitize_text(request.form.get("description", ""), 200)
    enroll_code = _sanitize_text(request.form.get("enroll_code", "").strip(), 80)
    if not name or not enroll_code:
        return "Name and enrollment code are required.", 400
    db = get_db()
    try:
        db.execute(
            "INSERT INTO classes (name, description, enroll_code) VALUES (?,?,?)",
            (name, description, enroll_code))
        db.commit()
    except sqlite3.IntegrityError:
        db.close()
        return "Enrollment code already exists — choose a unique code.", 400
    db.close()
    return redirect("/admin/classes")

@app.route("/admin/classes/<int:class_id>/toggle", methods=["POST"])
def admin_class_toggle(class_id):
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    db = get_db()
    db.execute("UPDATE classes SET active = 1 - active WHERE id=?", (class_id,))
    db.commit()
    db.close()
    return redirect("/admin/classes")

@app.route("/admin")
def admin():
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    db = get_db()
    subs = db.execute("SELECT * FROM submissions ORDER BY submitted_at DESC LIMIT 100").fetchall()
    parts = db.execute("SELECT * FROM participants ORDER BY registered_at DESC").fetchall()
    slots = db.execute("SELECT * FROM slots ORDER BY id").fetchall()
    pending_count = db.execute(
        "SELECT COUNT(*) FROM pending_registrations WHERE status='pending'").fetchone()[0]
    db.close()
    codes = load_codes()
    td = "style='padding:4px 10px;vertical-align:middle'"
    th = "style='text-align:left;padding:4px 10px;color:#aaa;white-space:nowrap'"
    out = (
        f"<h2>Participants ({len(parts)})</h2>"
        f"<table style='border-collapse:collapse;width:100%'>"
        f"<tr>"
        f"<th {th}>SAP Username</th>"
        f"<th {th}>VM</th>"
        f"<th {th}>Client</th>"
        f"<th {th}>Display Name</th>"
        f"<th {th}>Email</th>"
        f"<th {th}>VPN IP</th>"
        f"<th {th}>Status</th>"
        f"<th {th}>Expires</th>"
        f"<th {th}>Registered</th>"
        f"<th {th}>Actions</th>"
        f"<th {th}>Expiry</th>"
        f"</tr>"
    )
    for p in parts:
        uname     = p["sap_username"]
        is_locked = p["locked"]
        kicked_at = p["kicked_at"]
        vm_label  = (p["server"] or "—").upper()   # SAP2, SAP3 …
        client    = p["sap_client"] or "—"
        wg_ip     = p["wg_ip"] or "—"

        row_style = "border-top:1px solid #333;background:#2a0a0a" if is_locked else "border-top:1px solid #333"

        if kicked_at:
            status_badge = f"<span style='color:#f39c12;font-weight:bold'>⚡ KICKED</span>"
        elif is_locked:
            status_badge = "<span style='color:#e74c3c;font-weight:bold'>🔒 LOCKED</span>"
        else:
            status_badge = "<span style='color:#2ecc71'>active</span>"

        lock_btn = (
            f"<form method='POST' action='/admin/unlock/{uname}' style='display:inline'>"
            f"<button style='background:#27ae60;color:#fff;border:none;padding:2px 7px;border-radius:4px;cursor:pointer;font-size:0.8em;margin-right:2px'>Unlock</button></form>"
        ) if is_locked else (
            f"<form method='POST' action='/admin/lock/{uname}' style='display:inline'>"
            f"<button style='background:#e67e22;color:#fff;border:none;padding:2px 7px;border-radius:4px;cursor:pointer;font-size:0.8em;margin-right:2px'>Lock</button></form>"
        )

        expires_str = (p["expires_at"] or "")[:10]  # YYYY-MM-DD
        expire_color = ""
        if p["expires_at"]:
            try:
                from datetime import timedelta as _td
                exp_dt = datetime.fromisoformat(p["expires_at"])
                delta = exp_dt - datetime.utcnow()
                if delta.total_seconds() <= 0:
                    expire_color = "color:#e74c3c"
                elif delta.days <= 1:
                    expire_color = "color:#f39c12"
                else:
                    expire_color = "color:#2ecc71"
            except Exception:
                pass

        extend_form = (
            f"<form method='POST' action='/admin/extend/{uname}' style='display:inline;white-space:nowrap'>"
            f"<input type='date' name='expires_at' value='{expires_str}' "
            f"style='background:#1a1a2e;border:1px solid #333;color:#fff;padding:1px 4px;border-radius:3px;font-size:0.78em;width:108px'>"
            f"<button type='submit' name='mode' value='date' "
            f"style='background:#2980b9;color:#fff;border:none;padding:2px 6px;border-radius:3px;cursor:pointer;font-size:0.78em;margin-left:2px'>Set</button>"
            f"<button type='submit' name='mode' value='plus7' "
            f"style='background:#16a085;color:#fff;border:none;padding:2px 6px;border-radius:3px;cursor:pointer;font-size:0.78em;margin-left:2px'>+7d</button>"
            f"</form>"
        )

        out += (
            f"<tr style='{row_style}'>"
            f"<td {td}><strong style='color:#ffd700;letter-spacing:1px'>{uname}</strong></td>"
            f"<td {td}><strong>{vm_label}</strong></td>"
            f"<td {td}>{client}</td>"
            f"<td {td}>{p['name']}</td>"
            f"<td {td} style='color:#aaa;font-size:0.85em'>{p['email']}</td>"
            f"<td {td} style='color:#2ecc71;font-size:0.85em'>{wg_ip}</td>"
            f"<td {td}>{status_badge}</td>"
            f"<td {td} style='{expire_color};font-size:0.8em;white-space:nowrap'>{expires_str or '—'}</td>"
            f"<td {td} style='color:#aaa;font-size:0.8em;white-space:nowrap'>{(p['registered_at'] or '')[:16]}</td>"
            f"<td {td} style='white-space:nowrap'>"
            f"{lock_btn}"
            f"<form method='POST' action='/admin/kick/{uname}' style='display:inline'>"
            f"<button style='background:#8e44ad;color:#fff;border:none;padding:2px 7px;border-radius:4px;cursor:pointer;font-size:0.8em;margin-right:2px' title='Kill active sessions'>Kick</button></form>"
            f"<form method='POST' action='/admin/reset-pwd/{uname}' style='display:inline'>"
            f"<button style='background:#2980b9;color:#fff;border:none;padding:2px 7px;border-radius:4px;cursor:pointer;font-size:0.8em;margin-right:2px' title='Generate new SAP password'>Reset Pwd</button></form>"
            f"<form method='POST' action='/admin/delete/{uname}' style='display:inline'>"
            f"<button onclick=\"return confirm('Delete {uname}? Cannot be undone.');\" "
            f"style='background:#c0392b;color:#fff;border:none;padding:2px 7px;border-radius:4px;cursor:pointer;font-size:0.8em'>Delete</button>"
            f"</form></td>"
            f"<td {td}>{extend_form}</td>"
            f"</tr>"
        )
    out += "</table>"

    # ---- Slot occupancy grid -----------------------------------------------
    out += "<h2>Slot Occupancy</h2>"
    out += "<table style='border-collapse:collapse;margin-bottom:20px'>"
    out += f"<tr><th {th}>Client</th>"
    for srv in SLOT_SERVERS:
        out += f"<th {th}>{srv}</th>"
    out += "</tr>"
    # Build lookup: (server, sap_client) → assigned_to
    slot_map = {(s["server"], s["sap_client"]): s["assigned_to"] for s in slots}
    free_count = sum(1 for s in slots if s["assigned_to"] is None)
    for cli in SLOT_CLIENTS:
        out += f"<tr style='border-top:1px solid #333'><td {td}><strong>{cli}</strong></td>"
        for srv in SLOT_SERVERS:
            owner = slot_map.get((srv, cli))
            if owner:
                out += (f"<td {td} style='background:#1a3a1a;color:#2ecc71'>"
                        f"&#x2705; {owner}</td>")
            else:
                out += f"<td {td} style='color:#555'>free</td>"
        out += "</tr>"
    out += "</table>"
    out += f"<p style='color:#aaa;font-size:0.85em'>{free_count} / {len(slots)} slots free</p>"

    out += "<h2>Recent Submissions</h2><pre>"
    for s in subs:
        status = "OK" if s["correct"] else "WRONG"
        out += f"[{status}] {s['participant']} | {s['level']} | {s['code']} | {s['points']}pts | {s['submitted_at']}\n"
    out += "</pre><h2>Active Codes</h2><pre>"
    for lvl, info in codes.items():
        out += f"{lvl}: {info['code']} ({info['points']} pts)\n"
    out += "</pre><br><form method='POST' action='/admin/reset' onsubmit=\"return confirm('Reset ALL data? This also removes all WireGuard peers and frees all slots.');\" ><button style='background:#c0392b;color:#fff;border:none;padding:8px 20px;border-radius:4px;cursor:pointer;font-size:1em'>Reset Everything</button></form>"
    out += "<br><a href='/admin/create' style='display:inline-block;margin-top:10px;background:#2980b9;color:#fff;padding:8px 20px;border-radius:4px;text-decoration:none;font-size:1em'>➕ Manually create participant</a>"
    pending_badge = f" <span style='background:#c8102e;color:#fff;border-radius:10px;padding:1px 7px;font-size:0.85em'>{pending_count}</span>" if pending_count else ""
    out += f"<br><a href='/admin/approvals' style='display:inline-block;margin-top:10px;background:#e67e22;color:#fff;padding:8px 20px;border-radius:4px;text-decoration:none;font-size:1em'>📬 Access Requests{pending_badge}</a>"
    out += "<br><a href='/admin/classes' style='display:inline-block;margin-top:10px;background:#27ae60;color:#fff;padding:8px 20px;border-radius:4px;text-decoration:none;font-size:1em'>🎓 Manage Classes</a>"
    return f"<html><body style='font-family:monospace;background:#111;color:#eee;padding:20px'>{out}</body></html>"

@app.route("/admin/create", methods=["GET", "POST"])
def admin_create_user():
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err

    msg = ""
    result_block = ""

    if request.method == "POST":
        name         = _sanitize_text(request.form.get("name", ""), 80)
        email        = _sanitize_text(request.form.get("email", "").lower(), 120)
        sap_username = _sanitize_text(request.form.get("sap_username", "").upper(), 12)
        company      = _sanitize_text(request.form.get("company", ""), 80)

        if not name or not email or not sap_username:
            msg = "Name, email and SAP username are required."
        elif not re.match(r'^[A-Z0-9_]+$', sap_username):
            msg = "SAP username may only contain letters, digits and underscore."
        else:
            db = get_db()
            dup_email = db.execute("SELECT 1 FROM participants WHERE email=?", (email,)).fetchone()
            dup_sap   = db.execute("SELECT 1 FROM participants WHERE sap_username=?", (sap_username,)).fetchone()
            if dup_email:
                msg = f"Email {email} already registered."
            elif dup_sap:
                msg = f"SAP username {sap_username} already taken."
            else:
                server_alias, slot_client = _assign_slot(sap_username)
                if server_alias is None:
                    msg = "No slots remaining."
                else:
                    srv_info = SAP_SERVERS.get(server_alias, {})
                    slot_conn_params = {
                        "host":   srv_info.get("host",  SAP_HOST),
                        "sysnr":  srv_info.get("sysnr", SAP_SYSNR),
                        "client": slot_client,
                    }
                    sap_ok, temp_password, sap_error = create_workshop_user(
                        sap_username=sap_username,
                        first_name=name.split()[0] if name.split() else name,
                        last_name=" ".join(name.split()[1:]) if len(name.split()) > 1 else "",
                        email=email,
                        conn_params=slot_conn_params,
                    )
                    wg_ok, wg_ip, wg_conf, wg_error = create_customer_peer(
                        display_name=name, server_alias=server_alias)
                    try:
                        db.execute(
                            "INSERT INTO participants "
                            "(name, email, sap_username, company, sap_created, wg_ip, wg_conf, server, sap_client, waiver_accepted) "
                            "VALUES (?,?,?,?,?,?,?,?,?,1)",
                            (name, email, sap_username, company, 1 if sap_ok else 0,
                             wg_ip, wg_conf, server_alias, slot_client))
                        db.commit()
                    except sqlite3.IntegrityError as exc:
                        db.close()
                        msg = f"DB error: {exc}"
                        sap_ok = False
                    if sap_ok or not msg:
                        result_block = (
                            f"<div style='background:#0f1f0f;border:1px solid #2ecc71;padding:16px;border-radius:8px;margin-top:16px'>"
                            f"<strong style='color:#2ecc71'>✅ Created: {sap_username}</strong><br><br>"
                            f"Server: {server_alias} &nbsp;|&nbsp; Client: {slot_client} &nbsp;|&nbsp; VPN IP: {wg_ip or 'n/a'}<br>"
                            f"SAP Password: <strong style='color:#ffd700'>{temp_password or '(see SAP)'}</strong><br>"
                            f"{'⚠️ SAP error: ' + sap_error if not sap_ok else ''}"
                            f"{'<br>⚠️ WG error: ' + wg_error if not wg_ok else ''}"
                            f"</div>"
                        )
            db.close()

    form = f"""
    <html><body style='font-family:monospace;background:#111;color:#eee;padding:20px'>
    <h2>➕ Manually Create Participant</h2>
    <p style='color:#aaa'>Use this as a failsafe when a participant cannot self-register.<br>
    Waiver is recorded as accepted by the instructor on behalf of the participant.</p>
    {"<p style='color:#e74c3c'>" + msg + "</p>" if msg else ""}
    {result_block}
    <form method='POST' style='max-width:480px;margin-top:16px'>
      <label style='display:block;margin-bottom:4px;color:#aaa'>Full name</label>
      <input name='name' required style='width:100%;padding:8px;background:#222;color:#fff;border:1px solid #444;border-radius:4px;margin-bottom:12px'>
      <label style='display:block;margin-bottom:4px;color:#aaa'>Email</label>
      <input name='email' type='email' required style='width:100%;padding:8px;background:#222;color:#fff;border:1px solid #444;border-radius:4px;margin-bottom:12px'>
      <label style='display:block;margin-bottom:4px;color:#aaa'>SAP username (max 12 chars)</label>
      <input name='sap_username' required maxlength='12' style='width:100%;padding:8px;background:#222;color:#fff;border:1px solid #444;border-radius:4px;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px'>
      <label style='display:block;margin-bottom:4px;color:#aaa'>Company (optional)</label>
      <input name='company' style='width:100%;padding:8px;background:#222;color:#fff;border:1px solid #444;border-radius:4px;margin-bottom:16px'>
      <button type='submit' style='background:#2980b9;color:#fff;border:none;padding:10px 24px;border-radius:4px;cursor:pointer;font-size:1em'>Create participant →</button>
    </form>
    <br><a href='/admin' style='color:#aaa'>← Back to admin</a>
    </body></html>
    """
    return form


@app.route("/admin/reset-pwd/<sap_username>", methods=["POST"])
def admin_reset_password(sap_username):
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    uname = sap_username.upper()
    db = get_db()
    row = db.execute("SELECT name, server, sap_client FROM participants WHERE sap_username=?", (uname,)).fetchone()
    db.close()
    if not row:
        return f"<html><body style='font-family:monospace;background:#111;color:#eee;padding:20px'><p style='color:#e74c3c'>User {uname} not found.</p><a href='/admin' style='color:#aaa'>← Back</a></body></html>"

    conn_params = None
    if row["server"] and row["sap_client"] and row["server"] in SAP_SERVERS:
        conn_params = {
            "host":   SAP_SERVERS[row["server"]]["host"],
            "sysnr":  SAP_SERVERS[row["server"]]["sysnr"],
            "client": row["sap_client"],
        }

    ok, new_pwd, err = reset_sap_password(uname, conn_params=conn_params)
    vm = (row["server"] or "").upper()
    client = row["sap_client"] or "—"
    if ok:
        body = (
            f"<div style='background:#0f1f0f;border:1px solid #2ecc71;padding:16px;border-radius:8px;max-width:460px'>"
            f"<strong style='color:#2ecc71'>✅ Password reset — {uname}</strong><br><br>"
            f"VM: <strong>{vm}</strong> &nbsp;|&nbsp; Client: <strong>{client}</strong><br><br>"
            f"New password: <strong style='font-size:1.4em;color:#ffd700;letter-spacing:2px'>{new_pwd}</strong><br><br>"
            f"<span style='color:#aaa;font-size:0.85em'>The user will be prompted to change it on next login.</span>"
            f"</div>"
        )
    else:
        body = f"<p style='color:#e74c3c'>❌ Reset failed for {uname}: {err}</p>"

    return f"<html><body style='font-family:monospace;background:#111;color:#eee;padding:20px'>{body}<br><br><a href='/admin' style='color:#aaa'>← Back to admin</a></body></html>"


@app.route("/admin/delete/<sap_username>", methods=["POST"])
def admin_delete_user(sap_username):
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    uname = sap_username.upper()
    db = get_db()
    row = db.execute("SELECT wg_ip, server, sap_client FROM participants WHERE sap_username=?", (uname,)).fetchone()

    # Build per-participant SAP connection params
    p_server = row["server"] if row else None
    p_client = row["sap_client"] if row else None
    conn_params = None
    if p_server and p_client and p_server in SAP_SERVERS:
        conn_params = {
            "host":   SAP_SERVERS[p_server]["host"],
            "sysnr":  SAP_SERVERS[p_server]["sysnr"],
            "client": p_client,
        }

    # 1. Delete SAP user (kills sessions + BAPI_USER_DELETE)
    sap_ok, sap_err = delete_sap_user(uname, conn_params=conn_params)
    if not sap_ok:
        app.logger.warning("SAP user deletion failed for %s: %s", uname, sap_err)

    # 2. Remove WireGuard peer
    wg_ok, wg_err = True, ""
    if row and row["wg_ip"]:
        wg_ok, wg_err = remove_customer_peer(row["wg_ip"], server_alias=p_server)
        if not wg_ok:
            app.logger.warning("WG peer removal failed for %s: %s", uname, wg_err)

    # 3. Free the slot
    db.execute("UPDATE slots SET assigned_to=NULL, assigned_at=NULL WHERE assigned_to=?", (uname,))

    # 4. Remove from leaderboard DB (always — no inconsistent states)
    db.execute("DELETE FROM submissions WHERE participant=?", (uname,))
    db.execute("DELETE FROM participants WHERE sap_username=?", (uname,))
    db.commit()
    db.close()
    app.logger.warning("Admin deleted user %s (SAP:%s WG:%s)",
                       uname, "ok" if sap_ok else sap_err,
                       "ok" if wg_ok else (wg_err if row and row["wg_ip"] else "no-peer"))
    return redirect("/admin")

@app.route("/admin/extend/<sap_username>", methods=["POST"])
def admin_extend_user(sap_username):
    """Set or extend the expiry date for a participant."""
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    uname = sap_username.upper()
    mode  = request.form.get("mode", "date")  # "date" or "plus7"
    db = get_db()
    if mode == "plus7":
        # Add 7 days to current expiry (or from now if not set / expired)
        row = db.execute("SELECT expires_at FROM participants WHERE sap_username=?", (uname,)).fetchone()
        current = None
        if row and row["expires_at"]:
            try:
                dt = datetime.fromisoformat(row["expires_at"])
                if dt > datetime.utcnow():
                    current = dt
            except Exception:
                pass
        base = current or datetime.utcnow()
        from datetime import timedelta as _td
        new_expiry = (base + _td(days=7)).isoformat(timespec="seconds")
    else:
        raw = request.form.get("expires_at", "").strip()
        if not raw:
            db.close()
            return redirect("/admin")
        # Accept YYYY-MM-DD and turn it into end-of-day UTC
        try:
            new_expiry = datetime.strptime(raw, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59).isoformat(timespec="seconds")
        except ValueError:
            db.close()
            return "Invalid date format.", 400
    # If user was previously marked as deprovisioned (locked=99), reset so they're active again
    db.execute(
        "UPDATE participants SET expires_at=?, locked=CASE WHEN locked=99 THEN 0 ELSE locked END "
        "WHERE sap_username=?", (new_expiry, uname))
    db.commit()
    db.close()
    app.logger.info("Admin extended expiry for %s → %s", uname, new_expiry)
    return redirect("/admin")

@app.route("/admin/lock/<sap_username>", methods=["POST"])
def admin_lock_user(sap_username):
    auth_err = _require_admin_auth()
    if auth_err:
        return auth_err
    uname = sap_username.upper()
    db = get_db()
    db.execute("UPDATE participants SET locked=1 WHERE sap_username=?", (uname,))
    db.commit()
    row = db.execute("SELECT server, sap_client FROM participants WHERE sap_username=?", (uname,)).fetchone()
    db.close()
    conn_params = None
    if row and row["server"] and row["sap_client"] and row["server"] in SAP_SERVERS:
        conn_params = {"host": SAP_SERVERS[row["server"]]["host"],
                       "sysnr": SAP_SERVERS[row["server"]]["sysnr"],
                       "client": row["sap_client"]}
    ok, err = lock_sap_user(uname, conn_params=conn_params)
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
    row = db.execute("SELECT server, sap_client FROM participants WHERE sap_username=?", (uname,)).fetchone()
    db.close()
    conn_params = None
    if row and row["server"] and row["sap_client"] and row["server"] in SAP_SERVERS:
        conn_params = {"host": SAP_SERVERS[row["server"]]["host"],
                       "sysnr": SAP_SERVERS[row["server"]]["sysnr"],
                       "client": row["sap_client"]}
    ok, err = unlock_sap_user(uname, conn_params=conn_params)
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
    db = get_db()
    db.execute(
        "UPDATE participants SET locked=1, kicked_at=? WHERE sap_username=?",
        (datetime.utcnow().isoformat(timespec="seconds"), uname))
    db.commit()
    row = db.execute("SELECT server, sap_client FROM participants WHERE sap_username=?", (uname,)).fetchone()
    db.close()
    conn_params = None
    if row and row["server"] and row["sap_client"] and row["server"] in SAP_SERVERS:
        conn_params = {"host": SAP_SERVERS[row["server"]]["host"],
                       "sysnr": SAP_SERVERS[row["server"]]["sysnr"],
                       "client": row["sap_client"]}
    # Terminate active SAP sessions
    ok, err = kick_sap_user(uname, conn_params=conn_params)
    if not ok:
        app.logger.warning("SAP session kill failed for %s: %s", uname, err)
    # Lock the SAP account so they can't log back in
    ok, err = lock_sap_user(uname, conn_params=conn_params)
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
    parts = db.execute("SELECT wg_ip, server FROM participants WHERE wg_ip IS NOT NULL").fetchall()
    for p in parts:
        ok, err = remove_customer_peer(p["wg_ip"], server_alias=p["server"])
        if not ok:
            app.logger.warning("WG peer removal failed for %s during reset: %s", p["wg_ip"], err)
    db.execute("DELETE FROM submissions")
    db.execute("DELETE FROM participants")
    db.execute("UPDATE slots SET assigned_to=NULL, assigned_at=NULL")
    db.commit()
    db.close()
    return redirect("/admin")

# ---------------------------------------------------------------------------
# Auto-deprovision — sweep expired participants
# Runs at most once every 10 minutes (throttled via a simple timestamp file)
# ---------------------------------------------------------------------------
_last_expiry_sweep: float = 0.0

@app.before_request
def _sweep_expired_participants():
    global _last_expiry_sweep
    now = time.time()
    if now - _last_expiry_sweep < 600:   # max once per 10 min
        return
    _last_expiry_sweep = now
    try:
        db = get_db()
        expired = db.execute(
            "SELECT sap_username, wg_ip, server, sap_client FROM participants "
            "WHERE expires_at IS NOT NULL AND expires_at < datetime('now') AND locked != 99"
        ).fetchall()
        for p in expired:
            uname = p["sap_username"]
            app.logger.info("Auto-deprovisioning expired user %s", uname)
            # SAP
            conn_params = None
            if p["server"] and p["sap_client"] and p["server"] in SAP_SERVERS:
                conn_params = {"host": SAP_SERVERS[p["server"]]["host"],
                               "sysnr": SAP_SERVERS[p["server"]]["sysnr"],
                               "client": p["sap_client"]}
            try:
                delete_sap_user(uname, conn_params=conn_params)
            except Exception as e:
                app.logger.warning("SAP deprovision failed for %s: %s", uname, e)
            # WireGuard
            if p["wg_ip"]:
                try:
                    remove_customer_peer(p["wg_ip"], server_alias=p["server"])
                except Exception as e:
                    app.logger.warning("WG deprovision failed for %s: %s", uname, e)
            # DB — mark locked=99 (deprovisioned) and clear conf so profile shows expired
            db.execute(
                "UPDATE participants SET locked=99, wg_conf=NULL, temp_password=NULL WHERE sap_username=?",
                (uname,))
            db.execute("UPDATE slots SET assigned_to=NULL, assigned_at=NULL WHERE assigned_to=?", (uname,))
        if expired:
            db.commit()
        db.close()
    except Exception as e:
        app.logger.error("Expiry sweep error: %s", e)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print("DAC Workshop Leaderboard running on http://0.0.0.0:9000")
    app.run(host="0.0.0.0", port=9000, debug=False)
