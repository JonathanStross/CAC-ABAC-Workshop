# DAC Workshop — Interactive ABAC Class
**Status:** Planning / Pre-development  
**Target Duration:** Session 1: 2 hours (L0–L5) | Session 2: 1.5 hours (L6–L9) | Fast finishers: L10+  
**Author:** CAC Admin  
**Created:** 2026-06-01  

---

## Concept

A **narrative-driven, competitive, hands-on workshop** built around a realistic audit scenario. Participants play the role of a data security team at **Meridian AG** — a fictive international airline holding company — that has just received a **damning external audit report**.

The demo data is **SFLIGHT** — SAP's built-in airline dataset — giving us realistic passenger PII, booking records, payment data, and flight operations data to work with across all levels.

Participants race through levels, enter **completion codes** into a shared **leaderboard** to score points. Fast finishers always have more levels waiting. The leaderboard creates healthy competition and keeps the energy high throughout the session.

---

## SFLIGHT Data Model (used across all levels)

| Table | Content | PII / sensitive fields |
|---|---|---|
| `SCUSTOM` | Customer master | Name, address, phone, email, credit card number |
| `SBOOK` | Flight bookings | Customer ref, class, price, smoking preference |
| `SFLIGHT` | Flight instances | Price, seats occupied/free — revenue data |
| `SPFLI` | Flight schedule | Routes, times — operational data |
| `SCARR` | Airline carriers | Public reference data (no PII) |

**Why SFLIGHT is perfect:**
- Available on every SAP system via `SAPBC_DATA_GENERATOR`
- `SCUSTOM` has real PII-like fields: name, address, phone, email, `LOCCURAM` (credit card)
- `SBOOK` ties customers to bookings — relational PII
- Finance angle: `SFLIGHT.PAYMENTSUM`, revenue per route
- Operational angle: seat availability, overbooking — SOX-relevant

---

## The Leaderboard System

### Concept
Each level ends with a **completion code** — a value participants find or derive inside SAP/Pathlock as proof they solved the level correctly. They enter it at:

```
http://10.8.0.1:9000
```

The leaderboard app:
- Shows all registered participants and their level progress in real time
- Timestamps each code entry — faster = more points
- Bonus points for optional challenge levels
- Visible on a shared screen at the front of the room during the session

### Completion code design
Each code is something the participant must **find inside the system** — not guessable:
- A specific masked value pattern from a Pathlock audit log entry
- A count of rows returned by a specific SE16N query
- A policy ID generated when they save a DAC rule
- A hash or ticket number from a Pathlock finding

This means you can't just Google the answer — you have to actually do the work.

### Tech stack (to build)
- **Backend:** Python Flask or Node.js — runs as a Docker container on `10.8.0.1:9000`
- **Frontend:** Simple HTML/CSS leaderboard, auto-refreshes every 10 seconds
- **Storage:** SQLite (lightweight, no setup)
- **Routes:**
  - `GET /` — leaderboard display (public, shown on screen)
  - `GET /register` — participant registration form
  - `POST /submit` — code submission with validation
  - `GET /admin` — instructor view with all codes, reset button
- **Code validation:** Each level's valid code(s) stored in a config file — instructor can set them before the session

### Scoring
| Action | Points |
|---|---|
| Level completion (correct code) | 100 pts |
| Speed bonus (first to complete) | +50 pts |
| Second place | +25 pts |
| Optional challenge completed | +75 pts |
| Wrong code attempt | -5 pts (discourages guessing) |

---

## Session Structure

### Session 1 — "The Audit" (2 hours, L0–L5)
*Suitable for: first PoC, mixed technical/business audience*

| Time | Level | Finding | Guidance |
|---|---|---|---|
| 0:00–0:15 | Setup | VPN, SAP GUI, Pathlock, leaderboard registration | — |
| 0:15–0:25 | **L0** | Orientation — explore Meridian AG's SAP system | 🟢 Guided |
| 0:25–0:45 | **L1** | F-01: Passenger PII visible to all staff | 🟢 Guided |
| 0:45–1:05 | **L2** | F-02: Booking agents see payment data outside shifts | 🟡 Hints |
| 1:05–1:20 | **L3** | F-03: Dev team has real passenger data | 🟡 Hints |
| 1:20–1:35 | **L4** | F-04: Overprivileged revenue analyst role | 🔴 Independent |
| 1:35–2:00 | **L5** | F-05: Passenger list export + no classification | 🔴 Independent |

### Session 2 — "Deep Dive" (1.5 hours, L6–L9)
*Suitable for: technical champions, partner enablement, second session*

| Time | Level | Theme | Guidance |
|---|---|---|---|
| 0:00–0:25 | **L6** | F-06: Cross-airline data leakage (multi-entity ABAC) | 🔴 Independent |
| 0:25–0:50 | **L7** | F-07: Fiori/UI5 masking — data visible in browser DevTools | 🔴 Independent |
| 0:50–1:10 | **L8** | F-08: Audit trail gap — no evidence of who saw what | 🔴 Independent |
| 1:10–1:30 | **L9** | F-09: Classification-driven policy — future-proof framework | 🔴 Independent |

### Fast Finisher Levels (bonus, no time limit)
*Always available — keeps fast participants busy*

| Level | Theme |
|---|---|
| **L10** | Build a GDPR Art. 30 records-of-processing report from the Pathlock audit log |
| **L11** | Design a policy that satisfies 3 frameworks simultaneously — document the mapping |
| **L12** | The "too powerful role" deep dive — MSCHMIDT cost centre scenario |
| **L13** | Simulate a data breach: access as an attacker, then build the control that would have stopped it |

---

## Levels (Full Detail)

---

### Level 0 — Orientation: Welcome to Meridian AG
**Audit finding:** None — setup  
**Guidance:** 🟢 Fully guided  
**Data used:** `SCARR`, `SPFLI`, `SCUSTOM`

Meridian AG is a fictive airline holding. You've joined their IT security team the day the audit report landed. Your first task: understand what's actually in the system.

**Steps:**
1. Connect VPN, log into SAP GUI, log into Pathlock
2. Register on the leaderboard: `http://10.8.0.1:9000/register`
3. Open SE16N → browse `SCARR` (airlines), `SPFLI` (routes), `SCUSTOM` (passengers)
4. In `SCUSTOM`: note fields `NAME`, `STREET`, `POSTCODE`, `TELEPHONE`, `EMAIL`, `LOCCURAM` (credit card)
5. Observe: no masking. Everything visible.
6. In Pathlock: confirm no active DAC policies
7. **Completion code:** The number of rows in `SCUSTOM` (enter in SE16N, note the count)

---

### Level 1 — F-01: Passenger PII Visible to All Staff 🔴
**Guidance:** 🟢 Fully guided  
**Data:** `SCUSTOM` — `NAME`, `TELEPHONE`, `EMAIL`, `LOCCURAM`

> *"All staff with SE16N or customer transaction access can view full passenger PII including credit card numbers and contact details. No field-level restriction exists. GDPR Art. 5(1)(c) violation."*

**Steps (fully instructed):**
1. Pathlock DAC → new masking policy
2. Table: `SCUSTOM`, fields: `TELEPHONE`, `EMAIL`, `LOCCURAM`
3. Condition: `user.role != 'CUSTOMER_SERVICE_SENIOR'`
4. Mask type: partial mask (`****` last 4 digits for LOCCURAM, `j***@***.com` for email)
5. Activate → verify in SE16N as `DEMO_USER_A`
6. Check audit log — find the masked access event
7. **Completion code:** The masked value shown for `LOCCURAM` field (first 4 chars + asterisks pattern)

**ABAC:** `user.role` | **Framework:** GDPR Art. 5(1)(c), ISO 27001 A.8.11

---

### Level 2 — F-02: Booking Agents See Payment Data Outside Shifts 🟠
**Guidance:** 🟡 Hints only  
**Data:** `SBOOK` — `LOCCURAM`, `FORCURAM` (foreign currency amount)

> *"Booking agents can access passenger payment data and booking prices at any time, including nights and weekends from home networks. No time or location constraint exists. GDPR Art. 32."*

**Hints:**
- You need to combine `user.role` with `environment.time` — business hours = Mon–Fri 07:00–19:00
- Network condition: `environment.network` must match `10.8.0.0/24` (inside VPN)
- Think: is this a new policy or an extension of L1?
- Test by checking the policy log — does it show "context condition not met"?
- **Completion code:** The Pathlock policy ID of the rule you create (shown after saving)

**ABAC:** `user.role + environment.time + environment.network` | **Framework:** GDPR Art. 32, NIS2

---

### Level 3 — F-03: Developers Have Real Passenger Data 🟠
**Guidance:** 🟡 Hints only  
**Data:** `SCUSTOM`, `SBOOK` — all PII fields

> *"Developer accounts (`DEVELOPER` role) have read access to production passenger and booking data including names, addresses and credit card references. Test scenarios use real customer identities. GDPR Art. 25."*

**Hints:**
- Masking (`****`) breaks developer tests — they need realistic formats
- Look for the "scrambling" / "pseudonymization" option in Pathlock — not masking
- After scrambling: `MÜLLER, HANS` → `FISCHER, KARL` | IBAN-format card → different valid-format card
- Verify: run the same SE16N query as `DEVELOPER` — data looks real but isn't
- Why is scrambling better here than masking? Be ready to answer.
- **Completion code:** First 3 characters of the scrambled `NAME` value for `SCUSTOM` client `00000001`

**ABAC:** `user.role + data.classification` | **Framework:** GDPR Art. 25, Art. 5(1)(e)

---

### Level 4 — F-04: Overprivileged Revenue Analyst 🔴
**Guidance:** 🔴 Independent  
**Data:** `SFLIGHT` — `PAYMENTSUM`, `SEATSOCC`, `SEATSMAX` | `SBOOK` — all fields

> *"User `RANALYST` holds role `Z_REVENUE_ANALYST_ALL` granting read access to all flight revenue data, booking records and passenger details across all airline codes — including carriers outside Meridian AG's own portfolio. Role cleanup: 9 months. No compensating control. SOX Section 404 deficiency."*

**No instructions. You know what to do.**

Consider: what attribute limits `RANALYST` to only Meridian AG's own carriers? (hint: `SCARR.CARRID` — Meridian AG operates `LH`, `AA`).

**Completion code:** The number of `SFLIGHT` rows visible to `RANALYST` *after* your policy is applied (run count via SE16N)

**ABAC:** `user.role + user.airline_scope + resource.carrid` | **Framework:** SOX 404, GDPR Art. 5(1)(c)

---

### Level 5 — F-05: Passenger List Export + No Classification 🟡
**Guidance:** 🔴 Independent  
**Data:** All tables

> *"Users can export SCUSTOM and SBOOK data to local Excel files. No data classification exists — the system cannot distinguish between SCARR (public) and SCUSTOM (PII). Data leaves without audit trail. ISO 27001 A.8.12, GDPR Art. 32."*

**Part A:** Block downloads when context contains PII-classified data (ok-codes: `%EX`, `%PC`, `&XXL`)  
**Part B:** Classify `SCUSTOM` fields as `Restricted-PII`, `SBOOK` as `Internal-Financial`, `SCARR` as `Public`  
**Part C:** Update your L1–L4 policies to be classification-driven, not field-by-field

**Completion code:** The classification tag you assigned to `SCUSTOM.LOCCURAM` (exact string from Pathlock)

**ABAC:** Full | **Framework:** ISO 27001 A.8.12, GDPR Art. 32, PCI DSS Req. 3

---

### Level 6 — F-06: Cross-Airline Data Leakage (Multi-Entity) 🔴
**Guidance:** 🔴 Independent  
**Data:** `SFLIGHT`, `SBOOK` across multiple `CARRID` values

> *"Meridian AG operates as a holding for multiple airline brands. Staff from carrier `LH` can view booking and revenue data for carrier `AA` and vice versa. Employees should only see data for their own airline entity. GDPR Art. 5(1)(c) — purpose limitation."*

Design an ABAC policy that enforces **entity isolation** — `user.employer_carrid = resource.carrid`.

**Completion code:** Policy condition string you configured (exact syntax from Pathlock)

---

### Level 7 — F-07: Fiori/UI5 — Data Visible in Browser DevTools 🔴
**Guidance:** 🔴 Independent  
**Data:** `SEPMRA_C_SO` (Sales Orders) via OData service — Fiori Manage Sales Orders app

> **Scene:** *Mid-session, the instructor takes a call and steps out.*
> *"Sorry everyone — emergency, another client. Back in 20. You know what to do."*
>
> *The audit finding is already on the board: a junior consultant opened the Manage Sales Orders Fiori app and noticed that net amounts and customer IDs appear masked in the UI. He closed the ticket — job done. Except he didn't check the network tab.*
>
> *Open browser DevTools → Network → filter for OData. The raw JSON response from `SEPMRA_C_SO` contains every unmasked field in plain text. The mask was CSS only. GDPR Art. 32 — technical measures must be effective at the data layer, not the display layer.*

Configure Pathlock DAC to mask the sensitive fields (`NetAmount`, `CustomerID`) at the **OData response layer**.  
Prove it: the DevTools network response must show masked/omitted values, not the real ones.

**App URL:** `http://10.8.0.1:50000/sap/bc/ui2/flp?sap-client=001#SalesOrder-manage`  
**OData service:** `SEPMRA_C_SO_SalesOrder` (confirm via `/iwfnd/maint_service`)

**Completion code:** The HTTP response header name that Pathlock injects to mark a masked OData call

---

### Level 8 — F-08: No Audit Trail — Who Saw What? 🔴
**Guidance:** 🔴 Independent  
**Data:** Pathlock audit log

> *"The auditor asked: who accessed passenger credit card data in the last 30 days? Meridian AG could not answer. No audit trail of data access events exists. GDPR Art. 30 (records of processing), SOX Section 404."*

Configure Pathlock to log all access to `SCUSTOM.LOCCURAM`. Then:
1. Generate 5 access events as different users
2. Export the audit log filtered to this field
3. Produce a one-page "who saw what" summary that could be given to an auditor

**Completion code:** The number of distinct users in your audit log export

---

### Level 9 — F-09: Future-Proof Classification Framework 🔴
**Guidance:** 🔴 Independent  
**Data:** All tables

> *"All existing policies are field-by-field. When Meridian AG adds new SAP modules next year, every policy must be manually extended. There is no scalable classification-driven approach. ISO 27001 A.8.3 — information classification."*

Design a **3-tier classification scheme** (`Public` / `Internal` / `Restricted`) that:
- Covers all SFLIGHT tables
- Makes every existing policy classification-driven
- Means a new table only needs a classification tag — not a new policy

**Completion code:** Number of distinct classification tags active in your Pathlock instance after this level

---

### Level 10 (Fast Finisher) — GDPR Art. 30 Report
Build a processing activity record for "Passenger Booking Management" using Pathlock audit data. Must include: purpose, data categories, retention period, recipients, technical controls. Format: one A4 page.

### Level 11 (Fast Finisher) — Compliance Multiplier
Pick one policy you've built. Map it to at least 4 compliance frameworks simultaneously. Write the mapping as an audit response paragraph.

### Level 12 (Fast Finisher) — The Too Powerful Role
Deep dive: `MSCHMIDT` Finance Controller scenario. Cost centre scoping. See bonus scenario in this document.

### Level 13 (Fast Finisher) — Red Team / Blue Team
One participant acts as an attacker (`SAP_ALL` user, no Pathlock). Another configures Pathlock to stop them. The attacker tries to exfiltrate passenger credit card data. Race.

---

---

## Compliance Frameworks Reference

*Instructor picks the relevant ones based on customer industry.*

### Core frameworks (always relevant)

| Framework | Region | Key articles / controls | DAC/ABAC mapping |
|---|---|---|---|
| **GDPR** | EU | Art. 5(1)(c) minimisation, Art. 25 privacy by design, Art. 32 technical measures, Art. 83 penalties | Masking, scrambling, default-deny, audit log |
| **DSGVO** | Germany | Same as GDPR + §26 employee data | Same + stronger HR angle |
| **ISO 27001:2022** | Global | A.5.15 Access control, A.8.11 Data masking, A.8.12 Data leakage prevention | Direct control implementation |
| **SOX Section 404** | US / listed | ITGC — access evidence, segregation of duties | Audit log, compensating control for overprivileged roles |

### Industry-specific

| Framework | Sector | Key requirement | Demo angle |
|---|---|---|---|
| **HIPAA** | Healthcare (US) | Minimum necessary standard for PHI, audit controls | Mask patient/employee health data |
| **PCI DSS v4.0** | Payments (global) | Req. 3 protect stored data, Req. 7 least privilege | Mask PAN, CVV in SAP customer master |
| **DORA** | EU Finance | Art. 9 access control, operational resilience | Access control + full audit trail |
| **NIS2** | EU critical infra | Art. 21 access control as mandatory technical measure | ABAC as NIS2 technical control |

### German / DACH market

| Framework | Notes |
|---|---|
| **BDSG** (Bundesdatenschutzgesetz) | Supplements GDPR, stricter employee data rules — strong resonance in German HR demos |
| **BSI IT-Grundschutz** | Federal baseline — access control (ORP.4) and logging (DER.2) controls map directly |

### The "compliance multiplier" pitch

One Pathlock policy simultaneously satisfies multiple frameworks:

> A DAC rule that masks salary + IBAN + DOB for unauthorised roles covers:
> - GDPR Art. 5(1)(c) — minimisation ✅
> - ISO 27001 A.8.11 — data masking control ✅
> - SOX ITGC — access evidence ✅
> - DSGVO §26 — employee data protection ✅
> - NIS2 Art. 21 — technical access control ✅

**Configure once. Tick multiple audit boxes.**

---

- [ ] WireGuard VPN connected (`10.8.0.x`)
- [ ] SAP GUI installed (or Fiori via browser)
- [ ] Two demo users pre-created: `DEMO_USER_A`, `DEMO_USER_B`
- [ ] Demo dataset loaded (HR records with PII fields)
- [ ] Pathlock DAC policies pre-configured for levels 0–3 (levels 4–5 done live)
- [ ] Pathlock admin access for the instructor

---

## Demo Users to Create

| User | Role | Purpose |
|---|---|---|
| `DEMO_USER_A` | Basic / Clerk | Sees masked data |
| `DEMO_USER_B` | Manager | Sees unmasked data (within context) |
| `DEMO_ADMIN` | Pathlock Admin | Instructor account for live config |

---

## Data to Prepare

- HR master records with: Name, DOB, SSN/NI, IBAN, Salary, Cost Center
- Customer master with: Name, Address, Phone, Email, Credit limit
- Ideally loaded via `SAPBC_DATA_GENERATOR` or a custom Z-program

---

## Download Block — Technical Note

SAP GUI download is triggered by ok-codes such as:
- `%EX` — Export to local file
- `%PC` — Download  
- `&XXL` — Excel download

Pathlock intercepts these at the DAC layer. The block policy should be configured to:
1. Detect the ok-code
2. Check `data.classification` of the current screen context
3. Block if `classification = PII or Restricted` AND `user.role != data_steward`

---

## UI5 Masking — Technical Note (L7)

**App:** Manage Sales Orders (`SEPMRA_C_SO`) — standard Fiori app on the trial system  
**OData service:** `SEPMRA_C_SO_SalesOrder`  
**Sensitive fields:** `NetAmount`, `GrossAmount`, `CustomerID`

Pathlock DAC for Fiori masks at the **OData response layer**, not the UI layer:
- The backend filters/masks field values *before* sending JSON to the browser
- The browser never receives the real value — cannot be recovered via DevTools
- CSS/JS masking (the bad approach) hides the value in the DOM but the data is still in the HTTP response

**Demonstrate the vulnerability (before fix):**
1. Open the Fiori app — fields appear masked or blank visually
2. Open browser DevTools → Network → filter OData → click the `$batch` or entity request
3. In the Response tab: `"NetAmount":"14850.00"` — unmasked in plain JSON

**Demonstrate the fix (after Pathlock DAC config):**
1. Same steps — Response tab now shows `"NetAmount":"***"` or field absent entirely
2. This is the evidence you submit to the auditor

**Instructor note — "emergency call" framing:**  
At this point in the session, step out briefly. Students tackle L7 fully unsupported.  
This is intentional — it mirrors a real engagement where a junior consultant closes a finding without fully verifying it.

---

### Bonus Scenario — GDPR Data Minimisation in Default Views
**Goal:** Show how Pathlock enforces the GDPR **data minimisation principle** (Art. 5(1)(c)) by making masked/restricted views the *default* — not an afterthought.

**The regulatory angle:**
- GDPR Art. 5(1)(c): _"Personal data shall be adequate, relevant and limited to what is necessary in relation to the purposes for which they are processed"_
- Most SAP systems do the opposite: show everything by default, restrict only if someone complains
- Auditors and DPOs increasingly ask: _"How do you enforce minimisation technically, not just in policy documents?"_

**The Pathlock answer — "Secure by Default":**
- DAC flips the model: **masked is the default state**
- Access to unmasked data requires a justified ABAC attribute match (role + purpose + context)
- If no policy grants access → data stays masked, automatically
- This is provable to an auditor with a single screenshot + policy export

**Workshop exercise:**
1. Create a new user `DEMO_GDPR` with no special attributes
2. Open a transaction with personal data (name, DOB, email, IBAN)
3. Without any explicit deny rule — data is masked because no policy *grants* access
4. Show the Pathlock policy log: _"No matching grant policy → default mask applied"_
5. Add attribute `user.purpose = HR_PROCESSING` → fields unmask
6. Remove attribute → fields mask again instantly

**Key data categories to highlight (GDPR Art. 9 special categories):**
| Field | Classification | Default view |
|---|---|---|
| Date of birth | PII | `****` |
| National ID / SSN | PII – Special | `***-**-****` |
| Salary / Bank IBAN | Financial + PII | `****` |
| Health / disability | Special Category | Fully hidden |
| Email / Phone | PII | `j***@***.com` |

**Compliance talking points:**
- **Art. 25 — Privacy by Design:** DAC makes privacy the architectural default, not a bolt-on
- **Art. 32 — Security of processing:** Technical measure to prevent unauthorised access to personal data
- **Art. 30 — Records of processing:** Pathlock audit log = evidence of who accessed what, when
- **DSGVO (German GDPR):** Same principles, same demo — resonates strongly with German customers

**Key message for the customer:**
> _"With Pathlock, you don't configure minimisation — it's the default. You configure the exceptions."_

---

### Bonus Scenario — The "Too Powerful Role" Problem
**Goal:** Show ABAC/DAC as a mitigation when you *can't* or *won't* redesign a bloated SAP role.

**The real-world problem:**
- A user has a role like `Z_HR_ALL` or `SAP_ALL` — too broad, but politically or operationally untouchable
- Role cleanup would take 6–12 months, a re-auth project, or cross-department sign-off
- The business says: _"We can't remove the access, but we need to control what they actually see"_

**The Pathlock answer:**
- ABAC/DAC sits **on top of** SAP authorizations as a second enforcement layer
- The role still grants access to the transaction — but DAC masks, blocks, or scrambles the sensitive fields
- No role change, no basis project, no re-certification needed
- Policy is: _"User has Z_HR_ALL but is NOT in the HR department → mask salary, SSN, IBAN"_

**Workshop exercise:**
1. Log in as `DEMO_USER_A` — has a broad role, can open PA20
2. Without DAC: sees everything (salary, bank data, DOB)
3. Enable DAC policy: `role = Z_HR_ALL AND department != HR → mask PII fields`
4. Refresh — same role, same transaction, sensitive fields now masked
5. Show the audit log: access was attempted, data was protected

**ABAC attributes used:** `user.role + user.department + data.classification`

**Key message for the customer:**
> _"You don't have to fix your roles to fix your data risk. Pathlock gives you a fast lane."_

This is a **high-impact slide / demo moment** — maps directly to what most customers are actually living with.

---

## Open Items / To Build

- [ ] ABAP program to load demo HR/customer dataset
- [ ] Pathlock DAC policy export/import for each level (so session is reproducible)
- [ ] Student handout / exercise sheet (PDF or markdown)
- [ ] Instructor guide with talking points per level
- [ ] Reset script — wipe demo user state between sessions
- [ ] WireGuard customer configs for workshop attendees

---

## Folder Structure (planned)

```
dac-workshop/
├── PLANNING.md              ← this file
├── policies/                ← Pathlock DAC policy configs per level
│   ├── level0-basic-masking.json
│   ├── level1-role-masking.json
│   ├── level2-contextual.json
│   ├── level3-scrambling.json
│   ├── level4-classification.json
│   └── level5-complex.json
├── abap/                    ← ABAP programs
│   ├── ZDAC_LOAD_DEMO_DATA.abap
│   └── ZDAC_RESET_DEMO.abap
├── handouts/                ← Student-facing materials
│   ├── student-exercise-sheet.md
│   └── instructor-guide.md
└── screenshots/             ← Reference screenshots per level
```
