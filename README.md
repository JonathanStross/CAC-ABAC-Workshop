# CAC ABAC Workshop
### *Pathlock DAC/ABAC — Interactive Audit Simulation*

> **"Meridian AG just failed their data access audit. You have 90 minutes to fix it."**

A hands-on competitive workshop teaching real-world Data Access Control (DAC) and Attribute-Based Access Control (ABAC) concepts using Pathlock and a live SAP ABAP system. Participants work through 14 escalating audit findings — from basic field masking to OData-layer Fiori controls — and earn points on a live leaderboard.

---

## What's in this repo

| Folder / File | Description |
|---|---|
| `PLANNING.md` | Full instructor guide — all 14 levels, scoring, narrative, compliance mapping |
| `handouts/student-exercise-sheet.md` | Student-facing handout — audit findings F-01 to F-05, credentials, reflection questions |
| `leaderboard/` | Flask leaderboard app (Docker) — live scoring, completion codes, admin panel |
| `abap/` | ABAP helper programs used in exercises |
| `policies/` | Example Pathlock policy exports |
| `screenshots/` | Reference screenshots for instructors |

---

## The Scenario

Participants join as external consultants called in to remediate a failed audit at **Meridian AG**, a fictional freight & logistics company running SAP. The DPA has issued a formal warning. Five critical findings must be closed before end of day.

The audit findings map to real compliance controls:

| Finding | Risk | Frameworks |
|---|---|---|
| F-01: Credit card data unmasked | 🔴 Critical | GDPR Art. 32, PCI-DSS |
| F-02: Salary data visible to all | 🟠 High | GDPR Art. 9, DSGVO §26 |
| F-03: No context-based access | 🟠 High | ISO 27001 A.5.15 |
| F-04: Overprivileged role, no SoD | 🔴 Critical | SOX 404, ISO 27001 A.5.3 |
| F-05: No download controls | 🟡 Medium | GDPR Art. 32 |
| F-07: Fiori OData masking bypass | 🔴 Critical | GDPR Art. 32 |

---

## Workshop Format

- **Duration:** 90 minutes (or split across two sessions)
- **Team size:** 1–3 participants per SAP login
- **Prerequisites:** Pathlock DAC access, SAP GUI or Fiori browser access
- **Levels:** 14 total (L0 guided → L13 red team / blue team)
- **Scoring:** 100–200 pts per level + speed bonuses, –5 per wrong attempt

Completion codes are real values found *inside* SAP or Pathlock — not guessable. Instructor sets them in `leaderboard/level_codes.json` before the session.

---

## Leaderboard

Self-hosted Flask app with live auto-refresh. See [`leaderboard/README.md`](leaderboard/README.md) for deployment instructions.

Quick start (Docker):
```bash
docker build -t cac-leaderboard ./leaderboard
docker run -d -p 9000:9000 -v leaderboard_data:/data cac-leaderboard
```

---

## Getting Started (Instructor)

1. Set completion codes in `leaderboard/level_codes.json`
2. Deploy the leaderboard (see above)
3. Print / share `handouts/student-exercise-sheet.md`
4. Walk participants through the scenario intro in `PLANNING.md → Workshop Flow`
5. Start the clock

---

## System Requirements

- SAP ABAP trial system with SFLIGHT + SEPMRA demo data loaded
- Pathlock DAC configured and connected to SAP
- WireGuard VPN access for participants (SAP ports only — no SSH)
- Leaderboard accessible via browser (no VPN required)

---

*Part of the [CAC OffGrid System](https://github.com/PathLockMigration/CAC-OffGridSystem) — a self-hosted SAP training environment.*
