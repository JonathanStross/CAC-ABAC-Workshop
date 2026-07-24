# SAP Role Build Specification — DAC Workshop

**Meridian AG Audit Remediation — Pathlock DAC: Practitioner Level**
Last updated: 2026-06-08

---

## Overview

Four roles are needed. Build on **sap2** (only active SAP server — sap3/4/5 decommissioned July 2026).

| Role | Type | Assigned at | Purpose |
|---|---|---|---|
| `ZWORKSHOP` | Functional | Registration (auto) | Base authorizations for all 9 levels |
| `ZRANALYST` | Functional | L5 exercise (manual) | Intentionally overprivileged — target of L5 policy |
| `Z_CLEARANCE_TOPSECRET` | Shell (empty) | Pre-configured demo user | Clearance tier — sees all labels |
| `Z_CLEARANCE_INTERNAL` | Shell (empty) | Some participants | Clearance tier — sees Internal + Public |
| `Z_CLEARANCE_PUBLIC` | Shell (empty) | All participants (default) | Clearance tier — sees Public only |

> **Shell roles** contain zero authorization objects. They exist purely as an attribute
> value that `USER.ROLE` can match in a DAC policy condition.

---

## Role 1 — `ZWORKSHOP`

### Description
`DAC Workshop — base access for all exercise levels`

### Authorization Objects

#### 1. `S_TCODE` — Transaction Code Check

| Field | Values |
|---|---|
| `TCD` | `SE16` |
| | `SE16N` |
| | `FB01` |
| | `SU01` |
| | `/APPSDM/DC` |

> Note: `/N/APPSDM/ABAC` does not require `S_TCODE` — it is a namespace transaction
> controlled by Pathlock's own authorization. Do not add it here.

---

#### 2. `S_TABU_DIS` — Table Display via Generic Tools (SE16)

| Field | Values |
|---|---|
| `DICBERCLS` | `SS` |
| `ACTVT` | `03` (Display) |

> `SS` is the SAP-delivered authorization group covering the SFLIGHT demo tables
> (SCUSTOM, SBOOK, SCARR, SPFLI, SFLIGHT). Scoping to `SS` avoids giving
> access to production table groups.

---

#### 3. `S_TABU_NAM` — Table Access by Name (restrict to workshop tables only)

| Field | Values |
|---|---|
| `TABLE` | `SCUSTOM` |
| | `SBOOK` |
| | `SCARR` |
| `ACTVT` | `03` (Display) |

> **Important:** `S_TABU_NAM` is checked AFTER `S_TABU_DIS`. Both must permit the
> table. This double-scoping ensures participants can only browse the three exercise tables,
> not all `SS`-group tables like `SFLIGHT` or `SPFLI`.

---

#### 4. `F_BKPF_BUK` — Accounting Document: Authorization for Company Codes

| Field | Values |
|---|---|
| `ACTVT` | `01` (Create/Post) |
| `BUKRS` | `1000` |

> Needed for L5: participants run `FB01` to verify the TCode block fires.
> The block intercepts before posting — so this auth grants the attempt,
> Pathlock blocks the execution. Without this object, SAP itself rejects FB01
> before DAC even sees the request.

---

#### 5. `S_USER_GRP` — User Master Maintenance: Allowed User Groups (display only)

| Field | Values |
|---|---|
| `ACTVT` | `03` (Display) |
| `CLASS` | `*` |

> Needed for L5 Hint 2: participants open `SU01` to view their own role assignments
> and confirm `ZRANALYST` appears on their Roles tab.

---

#### 6. `S_ICF` — Authorization Check for ICF Services (Fiori/OData)

| Field | Values |
|---|---|
| `ICFNM` | `/sap/bc/ui2/flp` |
| `ICFMETH` | `*` |

> Needed for L8: participants access the Fiori Launchpad to open Manage Sales Orders
> and inspect the OData response in DevTools.

---

#### 7. `S_RFC` — Authorization Check for RFC Access (OData backend)

| Field | Values |
|---|---|
| `ACTVT` | `16` (Execute) |
| `RFC_NAME` | `SEPMRA_C_SO_SalesOrder` |
| | `SEPMRA_PROD_MAN` |
| `RFC_TYPE` | `FUGR` |

> Needed for L8 OData calls from the Fiori app.

---

#### 8. `S_DEVELOP` — ABAP Workbench (display — needed for `/N/APPSDM/ABAC`)

| Field | Values |
|---|---|
| `ACTVT` | `03` (Display) |
| `DEVCLASS` | `*` |
| `OBJNAME` | `*` |
| `OBJTYPE` | `*` |
| `P_GROUP` | `*` |

> Pathlock's ABAC transaction internally checks this object for display operations.
> Without it participants may see authorization errors when navigating the attribute lists.

---

### PFCG Steps — `ZWORKSHOP`

```
1. SE80 / PFCG → Create role ZWORKSHOP
2. Description: DAC Workshop — base access for all exercise levels
3. Menu tab: Add transactions SE16, FB01, SU01, /APPSDM/DC
4. Authorizations tab → Change authorization data
5. Add objects manually (or let SAP propose from menu):
   - S_TCODE      (auto-proposed from menu)
   - S_TABU_DIS   DICBERCLS=SS, ACTVT=03
   - S_TABU_NAM   TABLE=SCUSTOM/SBOOK/SCARR, ACTVT=03
   - F_BKPF_BUK   ACTVT=01, BUKRS=1000
   - S_USER_GRP   ACTVT=03, CLASS=*
   - S_ICF        ICFNM=/sap/bc/ui2/flp, ICFMETH=*
   - S_RFC        ACTVT=16, RFC_NAME=SEPMRA_*, RFC_TYPE=FUGR
   - S_DEVELOP    ACTVT=03, all fields=*
6. Generate profile
7. Transport in own workbench request
```

---

## Role 2 — `ZRANALYST`

### Description
`Analyst role — intentionally overprivileged (L5 exercise target)`

### Authorization Objects

#### 1. `S_TCODE`

| Field | Values |
|---|---|
| `TCD` | `SE16` |
| | `FB01` |

#### 2. `S_TABU_DIS`

| Field | Values |
|---|---|
| `DICBERCLS` | `SS` |
| `ACTVT` | `03` |

#### 3. `S_TABU_NAM`

| Field | Values |
|---|---|
| `TABLE` | `SBOOK` |
| `ACTVT` | `03` |

#### 4. `F_BKPF_BUK`

| Field | Values |
|---|---|
| `ACTVT` | `01` |
| `BUKRS` | `1000` |

### Purpose in L5

This role is the **problem**. Participants are assigned it before L5 begins (or assign it themselves via SU01). The exercise is to observe the overprivilege (`LOCCURAM` visible, `FB01` accessible), then create a DAC policy that compensates without touching the role.

> The learning point: **zero role changes were made to fix two compliance findings.**

---

## Roles 3–5 — Clearance Shell Roles

### Description pattern
`DAC Workshop — clearance tier [level]`

### Authorization Objects
**None. Zero. Empty profile.**

The roles exist only as names that `USER.ROLE` can match.

| Role | Description | Assigned to |
|---|---|---|
| `Z_CLEARANCE_TOPSECRET` | DAC Workshop — Top Secret clearance (sees all data) | Instructor / 1 demo participant |
| `Z_CLEARANCE_INTERNAL` | DAC Workshop — Internal clearance (sees Internal + Public) | ~half the class |
| `Z_CLEARANCE_PUBLIC` | DAC Workshop — Public clearance (sees Public data only) | Other half |

### PFCG Steps — Shell Roles

```
For each of the three clearance roles:
1. PFCG → Create role
2. Add description
3. Authorizations tab → Generate profile immediately (empty)
4. DO NOT add any authorization objects
5. Transport in same request as ZWORKSHOP
```

---

## L6 DAC Policy — Clearance-Driven Classification Masking

These three policies are **pre-built** by the instructor before the workshop. Participants discover them in L6 and observe the effect.

### Policy: `MASK_CLASSIFICATION_PUBLIC`
| Setting | Value |
|---|---|
| Condition | `USER.ROLE EQ Z_CLEARANCE_PUBLIC` |
| AND | `DATA.CLASS_LABEL NEQ Public` |
| Action | Mask — all fields in current table |

→ Users with Public clearance see `***` in SCUSTOM and SBOOK, but see real data in SCARR.

### Policy: `MASK_CLASSIFICATION_INTERNAL`
| Setting | Value |
|---|---|
| Condition | `USER.ROLE EQ Z_CLEARANCE_INTERNAL` |
| AND | `DATA.CLASS_LABEL EQ Restricted-PII` |
| Action | Mask — all fields in current table |

→ Users with Internal clearance see SBOOK freely, but SCUSTOM is masked.

### Policy: `MASK_CLASSIFICATION_TOPSECRET`
No policy needed — `Z_CLEARANCE_TOPSECRET` holders see everything unmasked. The absence of a matching condition = no enforcement.

---

## Transport Request Order

Import on each server in this sequence:

```
1. K900885.YS9   — Roles transport (ZWORKSHOP + ZRANALYST + clearance shells)
2. K900455.D91   — Pathlock DAC workbench objects
3. K900461.D91   — Pathlock DAC frontend
4. K900435.D91   — Roles (frontend)
5. K900873.YS9   — Data Scrambling workbench
6. K900883.YS9   — Data Scrambling customizing
7. K900889.YS9   — Final patch
```

> After importing K900885, run **PFCG → Role → User Comparison** for each role
> to push the new profiles into the user master records.

---

## Pre-Session Checklist

- [ ] Build `ZWORKSHOP` on sap2
- [ ] Build `ZRANALYST` on sap2
- [ ] Build `Z_CLEARANCE_TOPSECRET`, `Z_CLEARANCE_INTERNAL`, `Z_CLEARANCE_PUBLIC` — transport
- [ ] Assign `ZWORKSHOP` + `Z_CLEARANCE_PUBLIC` to all auto-registered participants (leaderboard does this)
- [ ] Assign `Z_CLEARANCE_TOPSECRET` to instructor demo user manually
- [ ] Pre-build `MASK_CLASSIFICATION_PUBLIC` and `MASK_CLASSIFICATION_INTERNAL` policies in DAC
- [ ] Assign `ZRANALYST` to participants before L5 begins (or include in registration role set)
- [ ] Verify `/APPSDM/DC` classification entries: SCUSTOM=Restricted-PII, SBOOK=Internal-Financial, SCARR=Public
