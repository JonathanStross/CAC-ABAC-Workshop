# CAC ABAC Workshop
### *Pathlock DAC/ABAC — Interactive Audit Simulation*

---

> **"Meridian AG just failed their data access audit.**
> **You have 90 minutes to fix it."**

You're not here to watch slides.
You're a consultant called in on short notice. The DPA is breathing down Meridian AG's neck. Five critical audit findings. One live SAP system. A leaderboard the whole room can see.

**Find the evidence. Apply the controls. Submit the codes. Win.**

---

## 🚀 Getting started — do this first

**Step 1 — Install the required software on your laptop**

| Software | Purpose | Download |
|---|---|---|
| **WireGuard** | VPN — required to reach the SAP system | [wireguard.com/install](https://www.wireguard.com/install/) |
| **SAP GUI** | SAP desktop client | [SAP Support](https://support.sap.com/en/product/connectors/sapgui.html) |
| **Chrome or Edge** | Required for SAP Fiori / UI5 levels | Pre-installed on most systems |

**Step 2 — Register**
Go to the leaderboard URL your instructor has put on the screen.
Hit **Register**, enter the access code your instructor announces, fill in your name and pick a SAP username (3–12 characters, letters and digits only).
You'll get your SAP credentials + a personal WireGuard VPN config — **write the password down, it's shown only once.**

**Step 3 — Connect to the VPN**
Open WireGuard, import the `.conf` file you downloaded, and activate the tunnel.
The first connection may take up to a minute — this is normal.

**Step 4 — Open Level 0**
Your instructor will give you the URL for the level guides — they are served directly from the leaderboard server.
Start with **Level 0 — Orientation** and follow the steps.

**Step 5 — Submit your codes**
Each level has a completion code hidden inside SAP or Pathlock — find it, submit it at `/submit`, and watch your name climb the leaderboard.

---

## 🗺 What's in this repo

| Path | Contents |
|---|---|
| `PLANNING.md` | Full instructor guide — all 14 levels, scoring, narrative, compliance mapping |
| `handouts/level-00-orientation.md` | Level 0 guide — connect to VPN + SAP GUI (step-by-step) |
| `handouts/student-exercise-sheet.md` | Audit brief — findings F-01 to F-05, context, reflection questions |
| `leaderboard/` | Flask app — leaderboard, registration, level guide renderer |

> **Level guides live in this repo but are served by the Flask app** at `/levels/0`, `/levels/1` etc.
> Updating a guide = `git push` + `git pull` on the server. No redeploy needed.

---

## 🏢 The scenario

You've been brought in as an external access control consultant at **Meridian AG**, a fictive airline holding company running SAP. Their last DPA audit was a disaster. The findings are still open. Your job: close them — using Pathlock DAC — before end of day.

| Finding | Risk | Compliance |
|---|---|---|
| F-01: Passenger PII unmasked for all staff | 🔴 Critical | GDPR Art. 5(1)(c), PCI-DSS |
| F-02: Payment data accessible outside shifts | 🟠 High | GDPR Art. 32, ISO 27001 A.5.15 |
| F-03: Developers have real passenger data | 🟠 High | GDPR Art. 25 |
| F-04: Overprivileged revenue analyst role | 🔴 Critical | SOX 404, ISO 27001 A.5.3 |
| F-05: Mass export — no classification or block | 🟡 Medium | GDPR Art. 32, ISO 27001 A.8.12 |
| F-07: Fiori OData masking bypass via DevTools | 🔴 Critical | GDPR Art. 32 |

---

## 🎯 How scoring works

| Action | Points |
|---|---|
| Level completion (correct code) | 100–200 pts depending on level |
| Speed bonus — 1st to complete a level | +50 pts |
| Speed bonus — 2nd | +25 pts |
| Speed bonus — 3rd | +10 pts |
| Wrong code submission | −5 pts |

Codes are real values found inside SAP or Pathlock — they cannot be guessed.

---

## 🛠 Instructor setup checklist

Before each session:

1. **Level codes** — set in `/opt/cac-workshop/leaderboard/level_codes.json` on the server (or edit via `/admin`)
2. **SAP role** — create `Z_DAC_WORKSHOP_PARTICIPANT` in PFCG with SE16N + Fiori authorisations
3. **SFLIGHT data** — run `SAPBC_DATA_GENERATOR` in SE38 if `SCUSTOM` / `SBOOK` tables are empty
4. **Environment file** — confirm `/opt/cac-workshop/leaderboard/.env` has:
   - `REGISTER_CODE` — the access code you'll announce at the start
   - `ADMIN_USER` / `ADMIN_PASSWORD` — for the `/admin` panel
   - `SAP_HOST`, `SAP_SYSNR`, `SAP_CLIENT`, `SAP_USER`, `SAP_PASSWORD`
5. **Announce** — registration URL + access code at the start of the session
6. **Intro** — walk through the Meridian AG narrative (~5 min) using `PLANNING.md` as your script

---

## 🖥 Server architecture

The workshop runs entirely on a single server:

| Service | Port | Notes |
|---|---|---|
| Leaderboard + level guides | `9000` | Flask app in Docker |
| SAP ABAP Trial | `3200`, `50000` | Reachable over VPN only (`10.8.0.1`) |
| WireGuard VPN | `51820/UDP` | Entry point for all participants |

Participants connect via WireGuard → assigned IP in `10.8.0.10–254` → reach SAP at `10.8.0.1`.

---

## 📁 Repo structure

```
dac-workshop/
├── PLANNING.md                   ← Instructor guide — full level detail + compliance mapping
├── README.md                     ← This file
├── handouts/
│   ├── level-00-orientation.md   ← Level 0 (served at /levels/0)
│   ├── level-01-pii-masking.md   ← Level 1 (coming)
│   └── student-exercise-sheet.md ← Print handout / audit brief
└── leaderboard/
    ├── leaderboard.py            ← Flask app (leaderboard + level renderer)
    ├── sap_user.py               ← SAP RFC integration (pyrfc)
    ├── wireguard_peer.py         ← WireGuard peer management (SSH)
    ├── level_codes.json          ← Completion codes — set before each session
    ├── Dockerfile
    └── docker-compose.yml
```

---

*Part of the [CAC OffGrid System](https://github.com/PathLockMigration/CAC-OffGridSystem) — a self-hosted SAP workshop environment.*

---

> **"Meridian AG just failed their data access audit.**
> **You have 90 minutes to fix it."**

You're not here to watch slides.
You're a consultant called in on short notice. The DPA is breathing down Meridian AG's neck. Five critical audit findings. One live SAP system. A leaderboard that the whole room can see.

**Find the evidence. Apply the controls. Submit the codes. Win.**

---

## 🚀 Getting started — do this first

**Step 1 — Install WireGuard**
Download it from [wireguard.com/install](https://www.wireguard.com/install/) for your OS (Windows, macOS, iOS, Android — all supported).

**Step 2 — Register**
Go to the leaderboard URL your instructor has put on the screen.
Hit **Register**, enter the access code your instructor announces, fill in your name and pick a SAP username.
You'll get your SAP credentials + a personal VPN config file — **write the password down, it's shown once.**

**Step 3 — Connect to the VPN**
Open WireGuard, import the `.conf` file you downloaded, and activate the tunnel.
You now have access to the SAP system.

**Step 4 — Open Level 0**
Go to the [CAC-ABAC-Workshop GitHub repo](https://github.com/JonathanStross/CAC-ABAC-Workshop) and start with **Level 0**.
Your instructor will tell you which levels are in scope for today's session.

**Step 5 — Submit your codes**
Each level has a completion code hidden inside SAP or Pathlock — find it, submit it at `/submit`, and watch your name climb the board.

---

## 🗺 What's in this repo

| | |
|---|---|
| `PLANNING.md` | Full instructor guide — all 14 levels, scoring, narrative, compliance mapping |
| `handouts/student-exercise-sheet.md` | Your audit brief — findings F-01 to F-05, SAP credentials table, reflection questions |
| `leaderboard/` | The Flask leaderboard app (Docker) |

---

## 🏢 The scenario

You've been brought in as an external access control consultant at **Meridian AG**, a freight & logistics company running SAP. Their last DPA audit was a disaster. Five findings are still open. Your job is to close them — using Pathlock DAC — before end of day.

| Finding | Risk | Why it matters |
|---|---|---|
| F-01: Credit card data unmasked in reports | 🔴 Critical | GDPR Art. 32, PCI-DSS |
| F-02: Salary data visible to all HR users | 🟠 High | GDPR Art. 9, DSGVO §26 |
| F-03: No time- or location-based access restrictions | 🟠 High | ISO 27001 A.5.15 |
| F-04: Overprivileged role, no Segregation of Duties | 🔴 Critical | SOX 404, ISO 27001 A.5.3 |
| F-05: Mass download of sensitive data — no controls | 🟡 Medium | GDPR Art. 32 |
| F-07: Fiori OData masking bypass | 🔴 Critical | GDPR Art. 32 |

---

## 🎯 How scoring works

- Each level is worth **100–200 points** depending on difficulty
- Speed bonuses for finishing early
- **–5 points** per wrong code submission — think before you click
- Codes are real values found inside SAP or Pathlock — they can't be guessed

---

## 🛠 Instructor notes

Pre-session checklist:
1. Set completion codes in `leaderboard/level_codes.json` (or via the `/admin` panel)
2. Create role `Z_DAC_WORKSHOP_PARTICIPANT` in PFCG and assign the right authorisations
3. Set `REGISTER_CODE` and `ADMIN_PASSWORD` in `/opt/cac-workshop/leaderboard/.env`
4. Announce the registration URL and access code at the start
5. Walk through the Meridian AG scenario intro from `PLANNING.md` — ~5 minutes

See [`leaderboard/README.md`](leaderboard/README.md) for full deployment instructions.


---

*Part of the [CAC OffGrid System](https://github.com/PathLockMigration/CAC-OffGridSystem) — a self-hosted SAP training environment.*
