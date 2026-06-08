# DAC Workshop — Pathlock ABAC Interactive Class
**Status:** Active — Session ready for L0–L1, L2–L9 in prep  
**Target Duration:** Session 1: 2 hours (L0–L5) | Session 2: 1.5 hours (L6–L9) | Fast finishers: L10–L13  
**Last Updated:** 2026-06-03  
**Infrastructure:** Live — server `152.53.187.143`, SAP A4H, Pathlock DAC 2025 Q4

---

## Purpose of This Document

This document is the **expert briefing and preparation guide** for the workshop. It describes:
- What each level teaches and **why it matters** to a customer audience
- What needs to be **pre-configured in DAC** before the session
- What **SAP users, data, and attributes** need to exist
- What the **completion code** is and how participants find it
- The **compliance narrative** that frames each finding

Audience: Pathlock SEs, consultants and technical leads who will co-run or validate the session.

---

## Workshop Concept

A **narrative-driven, competitive, hands-on workshop** built around a realistic audit scenario. Participants play the role of a data security team at **Meridian AG** — a fictive international airline holding company — that has just received a **damning external audit report** from an external DPA-mandated auditor.

The demo data is **SFLIGHT** — SAP's built-in airline dataset — giving us realistic passenger PII, booking records, payment data and flight operations data to work with across all levels.

Participants race through levels, find **completion codes hidden inside SAP or Pathlock**, and submit them to a shared **live leaderboard** to score points. Fast finishers always have more levels. The leaderboard creates healthy competition and keeps energy high.

**The narrative arc:**
> *Day 1: The audit report lands. 9 findings. No current controls.*  
> *L0–L5: First responder mode — fix the critical findings.*  
> *L6–L9: Deep remediation — scalable, future-proof architecture.*  
> *L10–L13: Bonus — go beyond remediation, build a programme.*

---

## Infrastructure (Live)

| Component | Detail |
|---|---|
| **Server** | `152.53.187.143` (public), `10.8.0.1` (VPN gateway) |
| **SAP** | Container `abaptrial`, SID `A4H`, client `001`, instance `00` |
| **Pathlock DAC** | `/N/APPSDM/ABAC` — version 2025 Q4 |
| **Leaderboard** | `http://152.53.187.143:9000` — Flask/SQLite, Docker |
| **VPN** | WireGuard — each participant gets a unique peer config + IP (`10.8.0.x`) |
| **Admin** | `http://152.53.187.143:9000/admin` — jonathan.stross@pathlock.com |
| **Access gate** | Registration code: `Rotterdam` |

---

## SFLIGHT Data Model

| Table | Content | PII / Sensitive fields |
|---|---|---|
| `SCUSTOM` | Passenger master | `NAME`, `STREET`, `POSTCODE`, `TELEPHONE`, `EMAIL`, `LOCCURAM` (credit card) |
| `SBOOK` | Flight bookings | Customer ref, class, price, `LOCCURAM`, `FORCURAM` |
| `SFLIGHT` | Flight instances | `PAYMENTSUM`, `SEATSOCC`, `SEATSMAX` — revenue data |
| `SPFLI` | Flight schedule | Routes, departure times — operational |
| `SCARR` | Airline carriers | `CARRID`, `CARRNAME` — public reference, no PII |

**Why SFLIGHT is the right dataset:**
- Pre-loaded on every SAP ABAP trial system (`SAPBC_DATA_GENERATOR`)
- `SCUSTOM` mimics a customer/HR master — name, address, phone, email, payment reference
- Multi-carrier structure (`LH`, `AA`, `UA`, etc.) enables entity isolation scenarios
- Revenue data (`SFLIGHT.PAYMENTSUM`) enables SOX/finance access scenarios
- Operational data (`SPFLI`) enables least-privilege read scenarios

---

## Scoring & Leaderboard

| Action | Points |
|---|---|
| Level completion (correct code) | 100–200 pts (varies by level) |
| 1st to complete a level | +50 pts speed bonus |
| 2nd to complete | +25 pts |
| Wrong code attempt | −5 pts |

The leaderboard polls every 10 seconds and is visible on the main screen throughout the session.

---

## Session Structure

### Session 1 — "The Audit" (2 hours)
*Target audience: mixed technical/business, first PoC, partner workshop*

| Time | Level | Audit Finding | Pathlock Concept | Guidance |
|---|---|---|---|---|
| 0:00–0:15 | Setup | — | VPN + SAP GUI setup | — |
| 0:15–0:25 | **L0** | None — orientation | Explore the system | Guided |
| 0:25–0:50 | **L1** | F-01: Passenger PII visible to all | First masking policy | Guided |
| 0:50–1:15 | **L2** | F-02: Access from unknown network | Network/IP-based context | Hints |
| 1:15–1:30 | **L3** | F-03: Dev team has real passenger data | Scrambling / pseudonymisation | Hints |
| 1:30–1:45 | **L4** | F-04: Overprivileged revenue analyst | Resource attribute scoping | Independent |
| 1:45–2:00 | **L5** | F-05: Export + no classification | Download block + data classification | Independent |

### Session 2 — "Deep Dive" (1.5 hours)
*Target audience: technical champions, architects, partner enablement*

| Time | Level | Theme | Guidance |
|---|---|---|---|
| 0:00–0:25 | **L6** | F-06: Cross-airline data leakage | Independent |
| 0:25–0:50 | **L7** | F-07: OData / Fiori — DevTools bypass | Independent |
| 0:50–1:10 | **L8** | F-08: No audit trail | Independent |
| 1:10–1:30 | **L9** | F-09: Classification-driven architecture | Independent |

### Fast Finisher Levels (always available)

| Level | Theme |
|---|---|
| **L10** | GDPR Art. 30 processing record |
| **L11** | Compliance multiplier — one policy, four frameworks |
| **L12** | Too powerful role — `MSCHMIDT` scenario |
| **L13** | Red team / Blue team race |

---

## Levels — Expert Detail

---

### Level 0 — Orientation: Welcome to Meridian AG
**Points:** 100 | **Guidance:** Fully guided | **Time:** 10 min

#### What participants do
Connect to the VPN, log into SAP, register on the leaderboard. Browse the SFLIGHT dataset using transaction `SE16`. Observe that all PII fields are fully visible with no controls. Find the login screen info text which contains the completion code.

#### Why this level exists
Sets context. Participants need to *see the problem* before they fix it. It also ensures everyone has a working environment before the competitive portion starts. The completion code (`42.`) is found in `SE61` → `LOGIN_SCREEN_INFO` — a detail only someone who actually explored the system would find.

#### What needs to be pre-configured
- `SE61` → `LOGIN_SCREEN_INFO` text must contain `42.` (enter before session)
- All SFLIGHT tables loaded with data (`SAPBC_DATA_GENERATOR`)
- Leaderboard live and accessible at `http://152.53.187.143:9000`
- WireGuard peer configs ready for distribution

#### ABAC concepts introduced
None — pure exploration.

#### Compliance narrative
> *"The auditor's first finding: no one at Meridian AG could tell us what data is in the system or who can access it. You have 10 minutes to answer both questions."*

#### Completion code
`42.` — found in the SAP login screen info text (`SE61` → `LOGIN_SCREEN_INFO`)

---

### Level 1 — F-01: Passenger PII Visible to All Staff
**Points:** 100 | **Guidance:** Fully guided | **Time:** 20–25 min

#### Audit finding
> *"All authenticated users can view the full email address of every passenger in table SCUSTOM without restriction. No masking or access control is applied at the field level. GDPR Art. 5(1)(c) — data minimisation violation."*

#### What participants do
Navigate Pathlock DAC (`/N/APPSDM/ABAC`) to:
1. Explore the pre-created Data Attribute `DATA.S_EMAIL` — read its Attribute ID and trace its technical mapping to SAP data element `S_EMAIL` in table `SCUSTOM`
2. Explore the pre-created User Attribute `USER.ID` — understand it resolves to the logged-in SAP username at runtime
3. Create a masking policy `MASK_EMAIL_<username>` under Policy Administration Point
4. Add a rule condition: `USER.ID EQ <their own username>` — policy scoped to themselves only
5. Add a Policy Enforcement Point: Data Masking → `DATA.S_EMAIL` mapped to their policy, action = Deny, active = yes
6. Log out and back in → verify `SE16` → `SCUSTOM` shows `***` in the EMAIL column
7. Ask a colleague to confirm their screen is unaffected — demonstrating scope

#### Why this level exists
The core skill: **create a masking policy**. By scoping it to their own user first, participants learn the `USER.ID` attribute and understand that DAC policies are precise — not blunt instruments. The "ask your neighbour" test makes the scoping concept visceral and memorable.

The step-by-step navigation through the DAC tree (Functional Config → Policy Information Point → Data Attribute Master / User Attribute Master → Policy Administration Point → Policy Enforcement Point) establishes the mental model used in every subsequent level.

#### What needs to be pre-configured
- `DATA.S_EMAIL` Data Attribute created in DAC:
  - Attribute ID: `DATA.S_EMAIL`
  - Technical Mapping (Technical Config tab → Data Attribute Config → Technical Mapping): `S_EMAIL`
- `USER.ID` User Attribute created in DAC
- Both visible to participants (read access sufficient)
- `SCUSTOM` table has email data loaded

#### ABAC concepts introduced
- Data Attribute (what to protect)
- User Attribute (who the policy applies to)
- Policy Administration Point (the rule)
- Policy Enforcement Point — Data Masking (the action)
- Rule condition (`USER.ID EQ value`)
- Session-based policy evaluation (must re-login)

#### Completion code
`DATA.S_EMAIL` — the Attribute ID of the data attribute they configured. Found by reading the Attribute ID field in Data Attribute Master. Submission question: *"What was the Attribute ID of the field you masked?"*

#### Framework
GDPR Art. 5(1)(c) — data minimisation | ISO 27001 A.8.11 — data masking

---

### Level 2 — F-02: Access from an Unknown Network Location
**Points:** 100 | **Guidance:** Hints only | **Time:** 20–25 min

#### Audit finding
> *"Booking agents can access passenger email data from any network location — including personal home networks and public Wi-Fi — without restriction. The control implemented in F-01 applies only to a specific named user. A network-aware policy is required. GDPR Art. 32 — technical measures must account for access context."*

#### Revised scenario (SAP is VPN-only — no direct access possible)

Since SAP is only reachable via WireGuard, each participant already has a unique `10.8.0.X` VPN IP. We use this to demonstrate contextual ABAC: create a policy scoped to **your own workstation IP**, then ask a lab partner on the same server (different IP) to test from theirs.

The `/levels/2` page includes a **live "Find Your Lab Partner" widget** — participants enter their SAP username and see all colleagues on the same SAP server with their VPN IPs. This drives real interaction in the room.

#### What participants do
1. Understand that the L1 policy is user-scoped only — no network enforcement
2. Open the Level 2 page on the leaderboard → use the **Find Lab Partner** widget to identify a colleague on the same SAP server with a different `10.8.0.Y` IP
3. Explore the pre-created `USER.NETWORK` User Attribute — read the **description field** (contains the completion code)
4. Create a new masking policy with condition: `USER.NETWORK NOT EQ 10.8.0.X` (their own IP)
   - Meaning: mask EMAIL for everyone whose VPN IP ≠ theirs — their own session is exempt
5. **Test A**: run `SE16 → SCUSTOM` from their own session → EMAIL **visible** (IP matches exception)
6. **Test B**: ask lab partner to log in with **their own** SAP credentials and run `SE16 → SCUSTOM` → EMAIL **masked** (`***`) — their IP ≠ the policy exception
7. Discuss: extending condition to `USER.NETWORK NOT IN 10.8.0.0/24` protects against all non-VPN access at scale

#### Why this level exists
Introduces **contextual / environmental ABAC** — the key differentiator between static RBAC and dynamic ABAC. Same table, same SAP role, different VPN IP → different result.

The lab-partner exercise makes the contrast immediately visible: both participants run the same transaction simultaneously and see different data. High-impact demo moment, zero credential sharing required.

**This level answers the question every customer asks:** *"Can Pathlock protect us based on context without changing SAP roles?"* — Yes.

#### Leaderboard feature
New API route: `GET /api/server-peers?sap_user=JSMITH`
Returns `{ server, peers: [{name, sap_username, wg_ip, sap_client}] }` for all participants on the same SAP server. Rendered as an interactive lookup widget on the `/levels/2` page.

#### What needs to be pre-configured
- `USER.NETWORK` User Attribute created in DAC — resolves to client source IP at session start
- **Completion code** pre-typed into the **description field** of `USER.NETWORK` before the session
- All participants on the same server share the same SAP instance — they can each see each other's policies

#### ABAC concepts introduced
- Environmental / contextual attributes (`USER.NETWORK`)
- Workstation-locked access policy (per-IP condition)
- Dynamic policy evaluation — same user, different network context, different result
- Scaling from per-IP to subnet: `NOT IN 10.8.0.0/24`

#### Completion code
Pre-entered in the **description field** of the `USER.NETWORK` User Attribute in DAC before the session. Participants find it: Functional Configuration → Policy Information Point → User Attribute Master → open `USER.NETWORK` → read Description.

#### Framework
GDPR Art. 32 — technical security measures | NIS2 Art. 21 — access control | ISO 27001 A.8.11

---

### Level 3 — F-03: After-Hours Access to Sensitive Transactions
**Points:** 100 | **Guidance:** Hints only | **Time:** 15 min

#### Audit finding
> *"Booking agents and analysts can run sensitive transactions including SE16, FB01 and payment-related reports at any hour of the day — including nights, weekends and public holidays. No time-of-day control exists. SOX and PCI-DSS require that access to financial data is restricted to authorised business hours."*

#### What participants do
1. Explore the pre-created `USER.TIME` User Attribute — confirm it resolves to the current server time (HH:MM) at the moment the policy is evaluated
2. Create a **TCode Block** policy with condition: `USER.TIME NOT IN 08:00-18:00`
   - Action type: **Block TCode** (not Masking — a new action type)
   - TCode to block: `SE16` (they've been using it all workshop — dramatic effect)
3. Immediately test: run `SE16` — it is now blocked outside business hours (note: the workshop runs outside 08:00–18:00 UTC, so the block fires immediately)
4. **Find the completion code** — it is visible in the **blocked screen message** that Pathlock displays when the TCode is blocked
5. Remove or deactivate the policy so they can continue using `SE16` for later levels

#### Why this level exists
Introduces a completely different enforcement type — **TCode blocking** — distinct from field masking (L1/L2). Also introduces the `USER.TIME` temporal attribute, a third category of contextual ABAC (after identity-based L1 and network-based L2).

The drama is built in: the block fires immediately during the workshop since it runs outside 08:00–18:00. Participants block themselves and see the real Pathlock block screen.

**Key customer message:** *"You don't need SAP authorisation changes. Pathlock wraps around the transaction and enforces business hours independently of the role."*

#### What needs to be pre-configured
- `USER.TIME` User Attribute created in DAC — resolves to current time HH:MM at policy evaluation
- **Completion code** pre-typed into the **block message text** of the TCode Block action (the text shown when access is denied)
- No role changes needed — any standard workshop participant user triggers this

#### ABAC concepts introduced
- Temporal / time-based contextual attributes (`USER.TIME`)
- TCode blocking (vs field masking)
- Time-window conditions (`NOT IN 08:00-18:00`)
- Three ABAC condition types now seen: identity (L1), network (L2), time (L3)

#### Completion code
Pre-entered in the **block message** of the TCode Block action. Participants see it on screen the moment `SE16` is blocked.

#### Framework
SOX Section 404 — access control | PCI-DSS Req. 7 — restrict access by business need | ISO 27001 A.9.4

---

### Level 4 — F-04: Overprivileged Revenue Analyst
**Points:** 150 | **Guidance:** Independent | **Time:** 15 min

#### Audit finding
> *"The RANALYST role was cloned from an Accounts Receivable Clerk template 18 months ago and never cleaned up. It carries two privileges the role has no business justification for: read access to `SBOOK.LOCCURAM` (credit card reference — PCI-DSS violation) and access to TCode `FB01` (Post Financial Document — SOX Segregation of Duties violation). An analyst should only READ revenue data, never view payment instruments or post journal entries. Role remediation is 9 months away."*

#### What participants do
First fully independent level — minimal guidance. They must:
1. Confirm the problem: open `SBOOK` via `SE16` → see `LOCCURAM` (credit card reference) fully visible
2. Try running `FB01` — it opens (it shouldn't for an analyst)
3. Find the `USER.ROLE` User Attribute in DAC — read its description to get the completion code
4. Create a single policy with condition: `USER.ROLE EQ RANALYST`
5. Add two actions under the same condition:
   - Action 1: **Mask** `DATA.LOCCURAM` on `SBOOK` → credit card reference hidden
   - Action 2: **Block TCode** `FB01` → posting transaction blocked
6. Test both: `SBOOK.LOCCURAM` is now masked; `FB01` shows a block screen
7. Reflect: one policy, one condition, two enforcement types, zero SAP role changes

#### Why this level exists
First independent level. Teaches that **one ABAC condition can drive multiple enforcement actions simultaneously** — masking + TCode blocking together. Also introduces the `USER.ROLE` attribute.

The SoD framing (`FB01` = post financial documents) is immediately recognisable to any SAP audience. The PCI-DSS framing (`LOCCURAM` = credit card reference) adds a compliance dimension. Together they show ABAC as a **compensating control for role remediation backlogs** — a universal pain point.

#### What needs to be pre-configured
- `ZRANALYST` custom role created in SAP (`SU01`/`PFCG`) with access to `FB01`, `SE16`, `SBOOK`
- Role assigned to all workshop participant users (or a dedicated shared `RANALYST` user per server)
- `DATA.LOCCURAM` Data Attribute created in DAC — maps to `LOCCURAM` on `SBOOK`
- `USER.ROLE` User Attribute created in DAC — resolves to the participant's SAP role at login
- **Completion code** pre-entered in the description of `USER.ROLE` attribute

#### ABAC concepts introduced
- Role-based user attribute (`USER.ROLE`)
- Multiple actions from a single condition (masking + TCode block combined)
- ABAC as SoD compensating control
- PCI-DSS field-level control + SOX TCode-level control in one policy

#### Completion code
Pre-entered in the **description field** of the `USER.ROLE` User Attribute in DAC. Consistent mechanic with L1/L2/L3.

#### Framework
SOX Section 404 — SoD compensating controls | PCI-DSS Req. 3 — protect stored cardholder data | GDPR Art. 5(1)(c) — data minimisation

---

### Level 5 — F-05: Passenger List Export & No Data Classification
**Points:** 150 | **Guidance:** Independent | **Time:** 20 min

#### Audit finding
> *"Users can export SCUSTOM and SBOOK data to local Excel files via SE16. No data classification exists — Pathlock cannot distinguish between SCARR (public reference data) and SCUSTOM (PII). Data leaves the system without restriction or audit trail. ISO 27001 A.8.12, GDPR Art. 32, PCI DSS Req. 3."*

#### What participants do

**Part A — Block the download:**
1. Identify the SAP GUI ok-codes that trigger data exports
2. Configure a Pathlock DAC **Data Blocking** policy (Policy Enforcement Point → Data Blocking — distinct from Data Masking)
3. Scope the block: fire only when the current table is classified as `PII` or `Restricted`
4. Verify: attempting to export `SCUSTOM` is blocked; exporting `SCARR` (public data) still succeeds

**Part B — Classify the tables:**
1. Assign data classifications in Pathlock:
   - `SCUSTOM` → `Restricted-PII`
   - `SBOOK` → `Internal-Financial`
   - `SCARR` → `Public`
2. Confirm the download block fires automatically based on classification — no per-table rules needed

#### Why this level exists
**Data leaving the system is the most common real-world breach vector.** This level teaches:
1. **Data Blocking** — a different enforcement type from masking (prevents the action, not just hides the value)
2. **Data Classification** — the foundation for scalable, future-proof governance

The "classification drives the block" model is a strong product message: tag the data once, the controls follow automatically. The distinction between `SCARR` (allowed to export) and `SCUSTOM` (blocked) makes the logic immediately intuitive.

#### Technical detail — Download block

SAP GUI downloads are triggered by ok-codes:
- `%EX` — Export to local file
- `%PC` — PC download
- `&XXL` — Excel/spreadsheet export

Pathlock intercepts these at the DAC layer before SAP processes the action:
1. Detects the ok-code
2. Evaluates `data.classification` of the active screen context
3. Blocks if `classification IN (PII, Restricted)` AND `user.role != DATA_STEWARD`

The block fires before the file is written. No data leaves the system; user receives a policy-triggered denial message.

#### What needs to be pre-configured
- Data Classification feature enabled in Pathlock (confirm on this instance before session)
- Classification tags `Restricted-PII`, `Internal-Financial`, `Public` available
- Policy Enforcement Point → Data Blocking node accessible to participants

#### ABAC concepts introduced
- Data Blocking (vs Masking — prevents action vs hides value)
- Data Classification — table-level and field-level tags
- Classification-driven policies (policy fires based on tag, not explicit field list)
- Export/download control

#### Completion code
The exact classification tag assigned to `SCUSTOM.LOCCURAM` in Pathlock — instructor sets before session.

#### Framework
ISO 27001 A.8.12 — data leakage prevention | GDPR Art. 32 | PCI DSS v4.0 Req. 3

---

### Level 7 — F-07: Fiori / OData — CSS Mask Is Not a Data Control
**Points:** 175 | **Guidance:** Independent | **Time:** 25 min

#### Audit finding
> *"A junior consultant reviewed the Manage Sales Orders Fiori app and confirmed that sensitive fields appear masked in the UI. The finding was closed as remediated. The auditor re-opened it: browser DevTools shows the raw OData JSON response contains all unmasked values in plaintext. GDPR Art. 32 — technical measures must be effective at the data layer."*

#### Instructor staging
At the start of this level, the instructor steps out briefly. Participants must work through it with zero support — mirroring the real scenario where a junior team member closed the finding.

#### What participants do
1. Open the Fiori Launchpad → navigate to the **Manage Sales Orders** app
2. Confirm fields appear visually masked in the UI (a CSS-level mask is already applied)
3. Open browser **DevTools** (F12) → **Network** tab → reload the app
4. Filter requests for `odata` — find the `$batch` or entity set request
5. Inspect the JSON response body: `"NetAmount":"14850.00"` — real values visible despite UI mask
6. Screenshot the unmasked JSON as "proof the finding is still open"
7. Configure Pathlock DAC OData masking for the `SEPMRA_C_SO_SalesOrder` service — mask `NetAmount`, `GrossAmount`, `CustomerID` at the **server-side response layer**
8. Reload the app — verify DevTools now shows `"NetAmount":"***"` in the JSON response
9. **Find the completion code** in the Pathlock OData masking configuration screen

#### Why this level exists
Challenges the assumption that "it looks masked in the app" = "it is protected". CSS/JS masking is a display trick — the data is in the HTTP response and recoverable with basic developer tools. Pathlock masks at the **data layer**, not the display layer.

This is the most technically sophisticated level in Session 2. The DevTools moment — seeing real currency amounts in the JSON despite the UI showing `***` — is a recurring "aha" for both technical and business audiences.

#### What needs to be pre-configured
- Fiori launchpad accessible: `https://10.8.0.1:50001/sap/bc/ui2/flp` (via VPN)
- `SEPMRA_C_SO_SalesOrder` OData service active and registered in `/IWFND/MAINT_SERVICE`
- A CSS-level UI mask already applied to the app (to simulate the "false close" scenario)
- OData masking feature enabled in Pathlock for this service
- **Completion code** pre-entered in the description of the OData policy entry in Pathlock

#### Completion code
Pre-entered in the **description field of the OData masking policy** in Pathlock DAC. Participants find it when they navigate to the OData masking configuration screen.

#### Framework
GDPR Art. 32 — technical security measures at data layer | PCI-DSS Req. 3 — protect data in transit

---

### Level 8 — F-08: No Audit Trail
**Points:** 175 | **Guidance:** Independent | **Time:** 20 min

#### Audit finding
> *"When asked to provide evidence of who accessed passenger credit card data (SCUSTOM.LOCCURAM) in the last 30 days, Meridian AG could not answer. No access logging exists at the field level. GDPR Art. 30 — records of processing activities. SOX Section 404."*

#### What participants do
1. Enable Pathlock access logging for `SCUSTOM.LOCCURAM`
2. Generate 5 access events across different users
3. Navigate to the Pathlock audit log → filter by attribute/field
4. Export the log
5. Produce a one-paragraph "who saw what, when" summary suitable for an auditor

#### Why this level exists
The audit trail question is frequently the first thing a DPO or external auditor asks. Most SAP installations have no answer. Pathlock provides it automatically once logging is enabled — and the evidence is complete: user, timestamp, transaction, field, masked/unmasked flag.

#### What needs to be pre-configured
- Pathlock audit log feature enabled
- Demo users active with access to `SCUSTOM`

#### Completion code
Number of distinct users in the participant's audit log export.

#### Framework
GDPR Art. 30 — records of processing | SOX Section 404 | ISO 27001 A.8.15 — logging

---

### Level 9 — F-09: Future-Proof Classification Architecture
**Points:** 200 | **Guidance:** Independent | **Time:** 20 min

#### Audit finding
> *"All existing Pathlock policies are configured field-by-field. When Meridian AG onboards new SAP modules next year, every policy must be manually extended. As remediations go, this is a liability — not an asset. ISO 27001 A.8.3 — information classification."*

#### What participants do
Design and implement a 3-tier classification scheme:
- `Public` — `SCARR`, `SPFLI`
- `Internal-Financial` — `SFLIGHT`, `SBOOK`
- `Restricted-PII` — `SCUSTOM`, selected `SBOOK` fields

Then refactor all policies from L1–L6 to be classification-driven:
- Instead of "mask `DATA.S_EMAIL` when `USER.ID EQ X`" → "mask all `Restricted-PII` fields when `USER.CLEARANCE LT Restricted`"
- New tables automatically inherit the right controls when tagged

#### Why this level exists
The strategic capstone. Shows that Pathlock is not just a point tool but an **information governance architecture**. Classification-driven policy is the answer to "what happens when we add S/4HANA next year?"

#### What needs to be pre-configured
- Data Classification feature enabled
- Sufficient time for participants (best for Session 2 or fast finishers after L8)

#### Completion code
Total number of distinct classification tags active in the participant's Pathlock instance after this level.

#### Framework
ISO 27001 A.8.3 — information classification | GDPR Art. 25 — privacy by design

---

### Level 10 (Fast Finisher) — GDPR Art. 30 Processing Record
**Points:** 75

Build a Records of Processing Activities entry for "Passenger Booking Management" using the Pathlock audit log as evidence. Must include: purpose, legal basis, data categories, retention period, recipients, technical controls implemented.

**Why:** GDPR Art. 30 is one of the most commonly cited DPA audit gaps. This shows Pathlock data can directly feed ROPA documentation.

---

### Level 11 (Fast Finisher) — Compliance Multiplier
**Points:** 75

Take one policy built during the session. Map it to at least 4 compliance frameworks simultaneously (GDPR Art. 5 + ISO 27001 A.8.11 + SOX 404 + NIS2 Art. 21). Write the mapping as an audit response paragraph.

**Why:** "Configure once, tick multiple boxes" is the most efficient ROI message. This makes it personal and concrete.

---

### Level 12 (Fast Finisher) — The Too Powerful Role
**Points:** 75

User `MSCHMIDT` is a Finance Controller with role `Z_FI_ALL` — all company codes and cost centres. Role cleanup is blocked by the business. Use Pathlock DAC to restrict `MSCHMIDT`'s view to cost centre `1000` only, without touching the SAP role.

**Why:** The most common real-world scenario. ABAC as an immediate compensating control.

---

### Level 13 (Fast Finisher) — Red Team / Blue Team
**Points:** 100

Two participants. Attacker: `SAP_ALL` user, Pathlock disabled for their session. Defender: Pathlock config access. The attacker tries to exfiltrate `SCUSTOM.LOCCURAM`. The defender must stop them using DAC policies before the attacker succeeds.

**Why:** Competitive, high-energy finale. Makes the threat model real. The defender wins when the attacker's screen shows `***`.

---

## Pre-Session Preparation Checklist

### SAP System
- [ ] SFLIGHT data loaded (`SAPBC_DATA_GENERATOR`)
- [ ] `SE61` → `LOGIN_SCREEN_INFO` text contains `42.` (L0 code)
- [ ] SAP users created: `DEVELOPER`, `RANALYST`, `MSCHMIDT`, demo users per level
- [ ] Roles assigned: `DEVELOPER` role to dev user, overprivileged role to `RANALYST`
- [ ] Fiori launchpad accessible, `SEPMRA_C_SO` OData service active (L7)

### Pathlock DAC (`/N/APPSDM/ABAC`)
- [ ] **L1:** `DATA.S_EMAIL` Data Attribute created with Technical Mapping to SAP data element `S_EMAIL`
- [ ] **L1:** `USER.ID` User Attribute created
- [ ] **L2:** `USER.NETWORK` User Attribute created (resolves to client source IP)
- [ ] **L2:** Description of `USER.NETWORK` attribute contains the L2 completion code
- [ ] **L3:** `USER.ROLE` User Attribute created
- [ ] **L4:** `DATA.CARRID` Data Attribute created with `CARRID` field mapping
- [ ] **L5:** Data Classification feature enabled; download block capability confirmed
- [ ] **L6:** `USER.EMPLOYER_CARRID` User Attribute created
- [ ] **L7:** OData masking enabled for `SEPMRA_C_SO_SalesOrder`
- [ ] **L8:** Access logging enabled
- [ ] All participant workshop users assigned role `/APPSDM/POL_CHANGE`

### Leaderboard
- [ ] Server running at `http://152.53.187.143:9000`
- [ ] Level codes set in `/opt/cac-workshop/leaderboard/level_codes.json`
- [ ] Admin credentials confirmed
- [ ] Registration access code: `Rotterdam`
- [ ] WireGuard peer generation working (test with one registration)

### Participant Materials
- [ ] Level guides deployed (L0 and L1 complete, L2 in prep)
- [ ] Student exercise sheet updated
- [ ] VPN config distribution method confirmed

---

## Completion Codes Summary

| Level | Code | Found by |
|---|---|---|
| L0 | `42.` | `SE61` → `LOGIN_SCREEN_INFO` — SAP login screen text |
| L1 | `DATA.S_EMAIL` | Attribute ID field in Data Attribute Master |
| L2 | TBD | Description of `USER.NETWORK` attribute (pre-enter before session) |
| L3 | TBD | Scrambled value in `SCUSTOM` row 1 after policy activates |
| L4 | TBD | Row count of `SFLIGHT` visible to `RANALYST` after scoping |
| L5 | TBD | Classification tag assigned to `SCUSTOM.LOCCURAM` |
| L6 | TBD | Policy condition string as saved in Pathlock |
| L7 | TBD | Pathlock HTTP response header on masked OData calls |
| L8 | TBD | Distinct user count in audit log export |
| L9 | TBD | Number of active classification tags in instance |
| L10–L13 | TBD | Set before session |

---

## ABAC Attributes Required

| Attribute | Type | Used in | Resolves to |
|---|---|---|---|
| `USER.ID` | User | L1 | Logged-in SAP username |
| `USER.NETWORK` | User | L2 | Client source IP address at session start |
| `USER.ROLE` | User | L3 | SAP role of the logged-in user |
| `USER.EMPLOYER_CARRID` | User | L6 | Carrier code from user master |
| `DATA.S_EMAIL` | Data | L1 | SAP data element `S_EMAIL` on `SCUSTOM` |
| `DATA.CARRID` | Data | L4, L6 | `CARRID` field on `SFLIGHT`, `SBOOK`, `SCARR` |

---

## Compliance Framework Reference

| Framework | Key controls demonstrated |
|---|---|
| **GDPR** Art. 5(1)(c) | Data minimisation — L1, L4, L6 |
| **GDPR** Art. 25 | Privacy by design — L3, L9 |
| **GDPR** Art. 30 | Records of processing — L8, L10 |
| **GDPR** Art. 32 | Technical security measures — L2, L5, L7 |
| **ISO 27001** A.8.11 | Data masking — L1, L2 |
| **ISO 27001** A.8.12 | Data leakage prevention — L5 |
| **ISO 27001** A.8.3 | Information classification — L5, L9 |
| **SOX** Section 404 | ITGC compensating controls — L4, L8 |
| **NIS2** Art. 21 | Technical access control measures — L2 |
| **PCI DSS** Req. 3 | Protect stored cardholder data — L1, L5 |

---

## Key Messages Per Level (SE / instructor talking points)

| Level | Customer-facing message |
|---|---|
| L1 | *"One policy. One attribute. One field protected. This is how it starts."* |
| L2 | *"The same user gets different data depending on where they connect from. Zero SAP changes."* |
| L3 | *"Developers need real-format data to test. They do not need real data."* |
| L4 | *"You cannot clean up the role for 9 months. We fixed the risk in 15 minutes."* |
| L5 | *"The data leaving the building is the breach. We stopped it at the door."* |
| L6 | *"One policy covers all carriers. Add a new airline tomorrow — the control is already there."* |
| L7 | *"If it is in the HTTP response, it is not masked. Pathlock protects the data, not the display."* |
| L8 | *"The auditor asked who saw the credit card data last month. Now you have the answer."* |
| L9 | *"Tag the data once. Every policy follows automatically. This is what scalable governance looks like."* |
