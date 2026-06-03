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

#### What participants do
1. Understand that the L1 policy is user-scoped — it does not prevent the same user from accessing data from an untrusted network, nor does it cover other users
2. Explore the pre-created User Attribute `USER.NETWORK` — confirm it resolves to the client source IP at session start
3. **Create a new SAP test user** and register it on the leaderboard (generates a new WireGuard peer → a different IP `10.8.0.y`)
4. Log in as the new user — observe EMAIL is fully visible (no policy covers this user yet)
5. Create a new masking policy with condition: `USER.NETWORK NOT IN 10.8.0.0/24`
   - Meaning: mask EMAIL for anyone connecting from *outside* the trusted corporate VPN range
6. Test scenario A: new user inside VPN (`10.8.0.y`) → EMAIL visible (trusted network)
7. Test scenario B: disconnect VPN → reconnect to SAP directly → EMAIL masked (`***`)
8. Discuss: all staff must use VPN — the system enforces it automatically, zero SAP role changes

#### Why this level exists
Introduces **contextual / environmental ABAC** — the key differentiator between static RBAC and dynamic ABAC. The same user gets *different data* depending on where they connect from. This requires zero SAP changes.

The "create a second user, get a new IP" exercise makes the network dimension concrete and testable in the room. Two sessions side by side — one masked, one not — based purely on network location is a high-impact customer demo moment.

**This level answers the question every customer asks:** *"We can't change SAP roles quickly enough. Can Pathlock protect us right now based on context?"* — Yes.

#### What needs to be pre-configured
- `USER.NETWORK` User Attribute created in DAC — resolves to client source IP at session start
- Description of `USER.NETWORK` attribute contains the L2 completion code (pre-enter before session)
- WireGuard allows multiple peers; a second registration produces a distinct `10.8.0.y` IP
- Trusted range defined: `10.8.0.0/24` (all WireGuard VPN peers)

#### ABAC concepts introduced
- Environmental / contextual attributes (`USER.NETWORK`)
- Network-based access policy (IP/subnet condition)
- Dynamic policy evaluation — same user, different context, different result
- The difference between identity-based and context-based control

#### Completion code
The `USER.NETWORK` Attribute ID — pre-entered in the description field of the `USER.NETWORK` attribute by the instructor before the session. Participants find it the same way they found the L1 code: Policy Information Point → User Attribute Master → open `USER.NETWORK` → read description.

#### Framework
GDPR Art. 32 — technical security measures | NIS2 Art. 21 — access control | ISO 27001 A.8.11

---

### Level 3 — F-03: Developers Have Real Passenger Data
**Points:** 100 | **Guidance:** Hints only | **Time:** 15 min

#### Audit finding
> *"Developer accounts have read access to production passenger data in SCUSTOM including real names, addresses and credit card references. Test scenarios are run against live PII. GDPR Art. 25 — privacy by design and by default."*

#### What participants do
1. Understand why masking is the wrong solution: developers need realistic-format data (correct length, valid structure) to test with — `***` breaks test code
2. Find the **scrambling** option in Pathlock DAC — a different enforcement type from Data Masking
3. Configure a scrambling policy for `SCUSTOM` name/address fields scoped to the `DEVELOPER` role
4. Verify: the same table now shows realistic but fictitious values — `MÜLLER, HANS` → `FISCHER, KARL`
5. Explain to the room: why is scrambling better than masking for dev environments?

#### Why this level exists
Teaches the distinction between **masking** (hide the value) and **scrambling** (replace with realistic fake). Masked data is useless for testing; real PII in dev is a GDPR violation. Scrambling solves both.

Also introduces **role-based** policy conditions (`USER.ROLE EQ DEVELOPER`) as contrast to L1's user-specific and L2's network-based conditions. By level 3, participants have seen three distinct ABAC condition types.

#### What needs to be pre-configured
- `USER.ROLE` User Attribute created in DAC — resolves to the SAP role of the logged-in user
- `DEVELOPER` role assigned to the demo user (or a dedicated test user)
- Scrambling configuration available and licensed on this DAC instance (verify before session)

#### ABAC concepts introduced
- Scrambling / pseudonymisation (vs masking)
- Role-based user attribute (`USER.ROLE`)
- Privacy by design (GDPR Art. 25)

#### Completion code
TBD — suggested: the first scrambled customer name in `SCUSTOM` row 1 after the policy activates. Instructor sets after confirming scrambling output on this instance.

#### Framework
GDPR Art. 25 — privacy by design | GDPR Art. 5(1)(e) — storage limitation

---

### Level 4 — F-04: Overprivileged Revenue Analyst
**Points:** 150 | **Guidance:** Independent | **Time:** 15 min

#### Audit finding
> *"User RANALYST holds a role granting read access to flight revenue data, booking records and passenger details across ALL airline codes — including carriers outside Meridian AG's own portfolio. Role cleanup is 9 months away. No compensating control exists. SOX Section 404 deficiency."*

#### What participants do
No instructions given. They must independently:
1. Identify the right attribute to scope by: `SFLIGHT.CARRID` / `SBOOK.CARRID` — Meridian AG operates `LH` and `AA` only
2. Create a policy that restricts `RANALYST`'s view of `SFLIGHT` and `SBOOK` to only rows where `CARRID IN {LH, AA}`
3. Verify: row count of `SFLIGHT` visible to `RANALYST` drops after the policy is applied
4. Submit the post-restriction row count as the completion code

#### Why this level exists
First fully independent level. Tests whether participants can apply the ABAC pattern without scaffolding. The "role cleanup is 9 months away" framing is a real-world scenario — **ABAC as a compensating control** resonates strongly with customers mid-way through a GRC programme who can't wait for role engineering.

#### What needs to be pre-configured
- `RANALYST` user created in SAP with overprivileged role
- `SFLIGHT` and `SBOOK` loaded with data for multiple carriers including non-Meridian ones
- `DATA.CARRID` Data Attribute created in DAC — maps to `CARRID` field on `SFLIGHT`, `SBOOK`

#### ABAC concepts introduced
- Resource/data attributes (not just user attributes)
- Row-level filtering (not just field masking)
- ABAC as a compensating control for role issues

#### Completion code
Row count of `SFLIGHT` visible to `RANALYST` after the scoping policy is applied. Instructor records this number after pre-config.

#### Framework
SOX Section 404 — ITGC compensating controls | GDPR Art. 5(1)(c)

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

### Level 6 — F-06: Cross-Airline Data Leakage (Multi-Entity ABAC)
**Points:** 175 | **Guidance:** Independent | **Time:** 25 min

#### Audit finding
> *"Meridian AG operates as a holding for multiple airline brands. Staff from carrier LH can view booking and revenue data for carrier AA and vice versa. No entity isolation exists at the data layer. GDPR Art. 5(1)(c) — purpose limitation."*

#### What participants do
Design and implement an ABAC policy that enforces **entity isolation** using a dynamic attribute match:
- User attribute: `USER.EMPLOYER_CARRID` (the carrier the logged-in user works for)
- Data attribute: `DATA.CARRID` (the carrier field on `SFLIGHT` and `SBOOK`)
- Policy condition: `USER.EMPLOYER_CARRID EQ DATA.CARRID`

Verify: LH staff sees only LH rows. AA staff sees only AA rows.

#### Why this level exists
Introduces **data attribute vs user attribute matching** — the most powerful ABAC pattern. Instead of hardcoding values (`CARRID = LH`), the policy uses a *dynamic comparison* between a user property and a data property. This scales to any number of carriers without changing the policy.

This pattern directly addresses the multi-entity / group holding use case common in enterprise SAP installations.

#### What needs to be pre-configured
- `USER.EMPLOYER_CARRID` User Attribute created in DAC — resolved from SAP user master data
- `DATA.CARRID` Data Attribute created in DAC — maps to `CARRID` field on `SFLIGHT`, `SBOOK`
- Test users assigned different `EMPLOYER_CARRID` values

#### Completion code
Policy condition string as configured and saved in Pathlock — instructor records before session.

#### Framework
GDPR Art. 5(1)(c) — purpose limitation | ISO 27001 A.5.15 — access control

---

### Level 7 — F-07: Fiori / OData — CSS Mask Is Not a Data Control
**Points:** 175 | **Guidance:** Independent | **Time:** 25 min

#### Audit finding
> *"A junior consultant reviewed the Manage Sales Orders Fiori app and confirmed that sensitive fields appear masked in the UI. The finding was closed as remediated. The auditor re-opened it: browser DevTools shows the raw OData JSON response contains all unmasked values in plaintext. GDPR Art. 32 — technical measures must be effective at the data layer."*

#### Instructor staging
At the start of this level, the instructor steps out briefly. Participants must work through it with zero support — mirroring the real scenario where a junior team member closed the finding.

#### What participants do
1. Open the Fiori Sales Orders app — fields appear masked visually
2. Open browser DevTools → Network tab → filter for OData requests
3. Find the `$batch` or entity request → inspect the JSON response
4. Observe: `"NetAmount":"14850.00"` — real values in the HTTP response despite the UI mask
5. Configure Pathlock DAC to mask `NetAmount`, `GrossAmount`, `CustomerID` at the **OData response layer** (server-side, before JSON leaves the backend)
6. Verify: DevTools now shows `"NetAmount":"***"` — the protection is real

#### Why this level exists
Challenges the assumption that "it looks masked in the app" = "it is protected". CSS/JS masking is a display trick — the data is in the HTTP response and recoverable with basic developer tools. Pathlock masks at the **data layer**, not the display layer.

#### What needs to be pre-configured
- Fiori launchpad accessible: `http://152.53.187.143:50000/sap/bc/ui2/flp`
- `SEPMRA_C_SO_SalesOrder` OData service active (`/iwfnd/maint_service`)
- OData masking feature enabled in Pathlock for this service

#### Completion code
TBD — suggested: the name of the Pathlock response header injected on masked OData calls.

#### Framework
GDPR Art. 32 — technical security measures at data layer

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
