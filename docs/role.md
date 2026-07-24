# ZWORKSHOP — Trainee Role Reference

**DAC: Practitioner Level — Meridian AG Workshop**
Last updated: 2026-06-08

> This document maps every workshop activity to the SAP authorization it requires.
> Use it to verify `ZWORKSHOP` covers all levels before the workshop starts.

---

## Quick Reference — All Auth Objects

| Auth Object | Field | Values | Needed for |
|---|---|---|---|
| `S_TCODE` | `TCD` | `SE16`, `SE16N`, `FB01`, `SU01`, `/APPSDM/DC` | All levels |
| `S_TABU_DIS` | `DICBERCLS` | `SS` | L0–L4, L7 |
| `S_TABU_DIS` | `ACTVT` | `03` (Display) | — |
| `S_TABU_NAM` | `TABLE` | `SCUSTOM`, `SBOOK`, `SCARR` | L0–L4, L7 |
| `S_TABU_NAM` | `ACTVT` | `03` (Display) | — |
| `F_BKPF_BUK` | `ACTVT` | `01` (Create) | L5 |
| `F_BKPF_BUK` | `BUKRS` | `1000` | L5 |
| `S_USER_GRP` | `ACTVT` | `03` (Display) | L5, L6 |
| `S_USER_GRP` | `CLASS` | `*` | — |
| `S_ICF` | `ICFNM` | `/sap/bc/ui2/flp` | L8 |
| `S_ICF` | `ICFMETH` | `*` | — |
| `S_RFC` | `ACTVT` | `16` (Execute) | L8 |
| `S_RFC` | `RFC_NAME` | `SEPMRA_C_SO_SalesOrder`, `SEPMRA_PROD_MAN` | L8 |
| `S_RFC` | `RFC_TYPE` | `FUGR` | — |
| `S_DEVELOP` | `ACTVT` | `03` (Display) | L1–L8 |
| `S_DEVELOP` | all other fields | `*` | — |

---

## Level-by-Level Breakdown

---

### L0 — Orientation

| Activity | TCode | Auth object required |
|---|---|---|
| Browse SCARR, SCUSTOM, SBOOK | `SE16N` | `S_TCODE(SE16N)` + `S_TABU_DIS(SS)` + `S_TABU_NAM(SCARR/SCUSTOM/SBOOK)` |
| Log in to SAP | — | Valid user account + initial password change |

**Tables accessed:** `SCARR`, `SCUSTOM`, `SBOOK`

---

### L1 — PII Masking

| Activity | TCode | Auth object required |
|---|---|---|
| Confirm EMAIL visible in SCUSTOM | `SE16` | `S_TCODE(SE16)` + `S_TABU_DIS(SS)` + `S_TABU_NAM(SCUSTOM)` |
| Open Pathlock ABAC, find DATA.S_EMAIL | `/N/APPSDM/ABAC` | Pathlock internal auth + `S_DEVELOP(03)` |
| Create masking policy | `/N/APPSDM/ABAC` | Pathlock DAC admin rights |

**Tables accessed:** `SCUSTOM`

---

### L2 — Contextual Access

| Activity | TCode | Auth object required |
|---|---|---|
| Browse SCUSTOM to verify masking effect | `SE16` | `S_TCODE(SE16)` + `S_TABU_DIS(SS)` + `S_TABU_NAM(SCUSTOM)` |
| Open USER.NETWORK attribute in DAC | `/N/APPSDM/ABAC` | Pathlock internal auth + `S_DEVELOP(03)` |
| Create network-based masking policy | `/N/APPSDM/ABAC` | Pathlock DAC admin rights |

**Tables accessed:** `SCUSTOM`

---

### L3 — TCode Block (Time-Based)

| Activity | TCode | Auth object required |
|---|---|---|
| Run SE16 — expect it to be blocked | `SE16` | `S_TCODE(SE16)` — Pathlock intercepts before SAP auth check |
| Open USER.TIME attribute in DAC | `/N/APPSDM/ABAC` | Pathlock internal auth + `S_DEVELOP(03)` |
| Create TCode block policy | `/N/APPSDM/ABAC` | Pathlock DAC admin rights |

> ⚠️ SAP's `S_TCODE` check fires before Pathlock's interception in some configurations.
> `SE16` must be in `ZWORKSHOP` so Pathlock sees the call before SAP rejects it.

**Tables accessed:** none (SE16 is blocked before table selection)

---

### L4 — Audit Feed

| Activity | TCode | Auth object required |
|---|---|---|
| Browse SCUSTOM + SBOOK to generate log events | `SE16` | `S_TCODE(SE16)` + `S_TABU_DIS(SS)` + `S_TABU_NAM(SCUSTOM/SBOOK)` |
| Enable logging on DATA.S_EMAIL, DATA.LOCCURAM | `/N/APPSDM/ABAC` | Pathlock internal auth + `S_DEVELOP(03)` |
| Read DAC Feed | `/N/APPSDM/ABAC` | Pathlock DAC admin rights |

**Tables accessed:** `SCUSTOM`, `SBOOK`

---

### L5 — Overprivileged Role

| Activity | TCode | Auth object required |
|---|---|---|
| Browse SBOOK — observe LOCCURAM visible | `SE16` | `S_TCODE(SE16)` + `S_TABU_DIS(SS)` + `S_TABU_NAM(SBOOK)` |
| Attempt FB01 — expect Pathlock block | `FB01` | `S_TCODE(FB01)` + `F_BKPF_BUK(ACTVT=01, BUKRS=1000)` |
| View own role assignments | `SU01` | `S_TCODE(SU01)` + `S_USER_GRP(ACTVT=03)` |
| Build DAC policy with USER.ROLE condition | `/N/APPSDM/ABAC` | Pathlock DAC admin rights |

> `ZRANALYST` must be assigned to the trainee's user before this level begins.
> Without it, `USER.ROLE EQ ZRANALYST` never matches and the policy has no effect.

**Tables accessed:** `SBOOK`

---

### L6 — Data Classification / Clearance

| Activity | TCode | Auth object required |
|---|---|---|
| View own clearance role | `SU01` | `S_TCODE(SU01)` + `S_USER_GRP(ACTVT=03)` |
| Browse classification table | `/APPSDM/DC` | `S_TCODE(/APPSDM/DC)` |
| Find DATA.CLASS_LABEL attribute | `/N/APPSDM/ABAC` | Pathlock internal auth + `S_DEVELOP(03)` |
| Test clearance — SE16 all three tables | `SE16` | `S_TCODE(SE16)` + `S_TABU_DIS(SS)` + `S_TABU_NAM(SCUSTOM/SBOOK/SCARR)` |

**Tables accessed:** `SCUSTOM`, `SBOOK`, `SCARR`

---

### L7 — Export Block

| Activity | TCode | Auth object required |
|---|---|---|
| Attempt download from SCUSTOM — expect block | `SE16` | `S_TCODE(SE16)` + `S_TABU_DIS(SS)` + `S_TABU_NAM(SCUSTOM)` |
| Attempt download from SBOOK — expect block | `SE16` | `S_TABU_NAM(SBOOK)` |
| Attempt download from SCARR — expect success | `SE16` | `S_TABU_NAM(SCARR)` |
| Activate BLOCK_DOWNLOAD_BY_CLASSIFICATION policy | `/N/APPSDM/ABAC` | Pathlock DAC admin rights |

**Tables accessed:** `SCUSTOM`, `SBOOK`, `SCARR`

---

### L8 — Fiori / OData Masking

| Activity | TCode / URL | Auth object required |
|---|---|---|
| Open Fiori Launchpad in browser | `https://10.8.0.1:50001/sap/bc/ui2/flp` | `S_ICF(ICFNM=/sap/bc/ui2/flp)` |
| Open Manage Sales Orders app | Browser (OData) | `S_RFC(SEPMRA_C_SO_SalesOrder, FUGR)` |
| Inspect OData response in DevTools | Browser only | No SAP auth — browser capability |
| Configure OData masking in DAC | `/N/APPSDM/ABAC` | Pathlock DAC admin rights |

**Services accessed:** `SEPMRA_C_SO_SalesOrder` OData service

---

## Roles Summary

| Role | Auth objects | Assigned by |
|---|---|---|
| `ZWORKSHOP` | Full set above | Auto at registration |
| `ZRANALYST` | `SE16`+`FB01`+`SBOOK` display only | Before L5 (manual or scripted) |
| `Z_CLEARANCE_PUBLIC` | **None** (shell) | At registration — most participants |
| `Z_CLEARANCE_INTERNAL` | **None** (shell) | At registration — some participants |
| `Z_CLEARANCE_TOPSECRET` | **None** (shell) | Instructor / demo user only |

---

## Pre-Workshop Checklist

- [ ] `ZWORKSHOP` built on sap2
- [ ] `ZRANALYST` built on sap2
- [ ] All 3 clearance shell roles built and transported
- [ ] `ZWORKSHOP` + `Z_CLEARANCE_PUBLIC` assigned as default in registration flow
- [ ] `ZRANALYST` assigned to all participants before L5 (or add to registration default set)
- [ ] Verify SE16N works on SCARR, SCUSTOM, SBOOK for a test user
- [ ] Verify FB01 is reachable (SAP allows it, Pathlock blocks it in L5)
- [ ] Verify Fiori launchpad loads at `https://10.8.0.1:50001/sap/bc/ui2/flp`
