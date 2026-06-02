# CAC ABAC Workshop
### *Pathlock DAC/ABAC — Interactive Audit Simulation*

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
