# Level 7 — Data Classification: Your Role Is Your Clearance

**Meridian AG Audit Remediation — DAC: Practitioner Level**

---

| | |
|---|---|
| 🎯 **Goal** | Discover how data classification + ABAC role conditions create a clearance-tier access model — without changing a single SAP authorization object |
| ⏱ **Time** | 15–20 minutes |
| 🏆 **Points** | 100 |
| 💡 **Difficulty** | 🟡 Hints |

---

## Background

The DPA audit finding #6 reads:

> *"No data classification exists — Pathlock cannot distinguish between SCARR (public reference data) and SCUSTOM (PII). There is no mechanism to enforce data-sensitivity-aware access. Data leaves the system without restriction or audit trail."*
> — *ISO 27001 A.8.3, ISO 27001 A.8.12, GDPR Art. 32*

You have already built policies that target specific users, networks, times, and roles. All of those conditions answer the question: **"who is accessing?"**

This level introduces a second axis: **"how sensitive is the data being accessed?"**

The answer comes from **Data Classification** — a labelling system that tags every SAP table with a sensitivity tier. Once labelled, the label becomes an ABAC attribute (`DATA.CLASS_LABEL`) that any policy can reference. You classify a table once. Every control that uses `DATA.CLASS_LABEL` applies automatically, forever — no table names hardcoded anywhere.

---

## The Clearance Model

Your SAP user has been assigned a **clearance role**. It contains zero authorization objects — it exists purely as a name that DAC can match:

| Role | Clearance tier | What you can see |
|---|---|---|
| `Z_CLEARANCE_PUBLIC` | Public | Only `Public` data — reference tables like SCARR |
| `Z_CLEARANCE_INTERNAL` | Internal | `Internal-Financial` + `Public` — financial records + reference |
| `Z_CLEARANCE_TOPSECRET` | Top Secret | Everything — `Restricted-PII` + `Internal-Financial` + `Public` |

> The roles are empty shells in SAP. Your SAP authorization profile is unchanged.
> The enforcement — what you see vs. what gets masked — is entirely driven by DAC policy
> matching `USER.ROLE` against `DATA.CLASS_LABEL`.

This is how real-world data classification schemes work under ISO 27001 A.8.3 and NATO-style clearance models: the label on the data meets the clearance on the user — access is granted or denied at that intersection.

---

## Step 1 — Find Your Clearance Role

| # | Action | What you see |
|---|---|---|
| 1 | Run `SU01` in SAP | User maintenance |
| 2 | Enter your SAP username → Execute (F8) | Your user master |
| 3 | Click the **Roles** tab | List of assigned roles |
| 4 | Find the role beginning with `Z_CLEARANCE_` | Your clearance tier |

> ⚠️ Write down your clearance role — you will need it in Step 3.

---

## Step 2 — Explore the Classification Table

| # | Action | What you see |
|---|---|---|
| 1 | Run transaction **`/APPSDM/DC`** | Data Classification main screen |
| 2 | Browse all classification entries | Tables mapped to sensitivity labels |

**Confirm these three entries:**

| Table | Classification | What it contains |
|---|---|---|
| `SCUSTOM` | `Restricted-PII` | Passenger names, addresses, phone, email, payment ref |
| `SBOOK` | `Internal-Financial` | Booking records, prices, payment amounts |
| `SCARR` | `Public` | Airline carrier names — public reference data |

> ⚠️ If any entry is missing or wrong — tell your instructor before continuing.

---

## Step 3 — Find the `DATA.CLASS_LABEL` Attribute

Classification labels need a bridge into the DAC policy engine.

| # | Action | What you see |
|---|---|---|
| 1 | Run **`/N/APPSDM/ABAC`** → **Functional Configuration** tab | Left tree |
| 2 | Expand **Policy Information Point** → **Data Attribute Master** | Attribute list |
| 3 | Find and open **`DATA.CLASS_LABEL`** | Attribute detail |
| 4 | Read the description carefully | Runtime: resolves to the label of the current table |

> At runtime, when a user opens `SCUSTOM` in SE16, `DATA.CLASS_LABEL` = `Restricted-PII`.
> When they open `SCARR`, it = `Public`. The policy engine sees this value live, every call.

---

## Step 4 — Find the Pre-Built Clearance Policies

The instructor has pre-configured two masking policies that enforce the clearance model. Locate them and understand their structure.

| # | Action | What you see |
|---|---|---|
| 1 | In **`/N/APPSDM/ABAC`** → **Functional Configuration** | Left tree |
| 2 | Open **Policy Administration Point** | All policies |
| 3 | Find **`MASK_CLASSIFICATION_PUBLIC`** and open it | Policy detail |
| 4 | Read the **Condition** and **Action** | — |
| 5 | Find **`MASK_CLASSIFICATION_INTERNAL`** and open it | Policy detail |
| 6 | Read the **Condition** and **Action** | — |

**You should see:**

| Policy | Condition | Action |
|---|---|---|
| `MASK_CLASSIFICATION_PUBLIC` | `USER.ROLE EQ Z_CLEARANCE_PUBLIC` AND `DATA.CLASS_LABEL NEQ Public` | Mask all fields |
| `MASK_CLASSIFICATION_INTERNAL` | `USER.ROLE EQ Z_CLEARANCE_INTERNAL` AND `DATA.CLASS_LABEL EQ Restricted-PII` | Mask all fields |

> No policy targets `Z_CLEARANCE_TOPSECRET` — absence of a matching condition means no
> enforcement. Top Secret users see everything unmasked by design.

---

## Step 5 — Test Your Clearance

Run SE16 against all three tables and observe what your clearance tier permits:

| Table | Classification | Public sees | Internal sees | Top Secret sees |
|---|---|---|---|---|
| `SCARR` | `Public` | ✅ full data | ✅ full data | ✅ full data |
| `SBOOK` | `Internal-Financial` | `***` masked | ✅ full data | ✅ full data |
| `SCUSTOM` | `Restricted-PII` | `***` masked | `***` masked | ✅ full data |

> Run: `SE16` → table name → Execute (F8) → observe the result.
> Do all three tables. Confirm your tier behaves as the table above predicts.

---

## Step 6 — The Insight: One Classification, Infinite Policies

> **`DATA.CLASS_LABEL`** is the key insight of this level.

Imagine Meridian AG adds a new table tomorrow — `SPASSPORT` — containing passport numbers. The DBA classifies it as `Restricted-PII` in `/APPSDM/DC`.

**What changes in the DAC policies?** Nothing. Zero.

`MASK_CLASSIFICATION_PUBLIC` already blocks `DATA.CLASS_LABEL NEQ Public`.
`SPASSPORT` = `Restricted-PII` → not equal to `Public` → masked automatically.

This is the difference between **policy-based** and **rule-based** access control:
- Rule-based: add a new table → add a new rule → risk of forgetting.
- Policy-based: add a new table → classify it → all existing policies apply instantly.

---

## 🏆 Completion Code

**The completion code is the classification label assigned to `SCUSTOM` in `/APPSDM/DC`.**

Enter it on the leaderboard exactly as it appears — capital letters, hyphen included.

---

## What You Learned

| Concept | Meaning |
|---|---|
| **Data Classification** | Sensitivity labels on SAP tables — `Restricted-PII`, `Internal-Financial`, `Public` |
| **`DATA.CLASS_LABEL`** | Runtime attribute that carries the label into the policy engine |
| **Clearance role** | An empty SAP role used purely as a `USER.ROLE` value — no auth objects needed |
| **Clearance intersection** | Policy fires when the user's clearance tier meets the data's sensitivity label |
| **Tag once, control everywhere** | Classify a table once — all downstream policies apply automatically |

---

> **Level 8 builds directly on this:** you will use `DATA.CLASS_LABEL` to block
> data exports for `Restricted-PII` and `Internal-Financial` tables
> while allowing `Public` data through freely.


---

## Background

The DPA audit finding #5 reads:

> *"No data classification exists — Pathlock cannot distinguish between SCARR (public reference data) and SCUSTOM (PII). Data leaves the system without restriction or audit trail."*
> — *ISO 27001 A.8.3, ISO 27001 A.8.12, GDPR Art. 32*

Before any download block or export control can work, Pathlock needs to know **what kind of data each table contains**. That's what Data Classification does.

Classification is a label system:

| Label | Meaning |
|---|---|
| `Restricted-PII` | Personal data — names, addresses, payment info |
| `Internal-Financial` | Business-sensitive financial records |
| `Public` | Reference data — safe to export freely |

**Once tables are tagged, every policy that references `DATA.CLASS_LABEL` automatically applies to the right data — no table names hardcoded anywhere.**

---

## Step 1 — Open the Classification Configuration

| # | Action | What you see |
|---|---|---|
| 1 | Run transaction **`/APPSDM/DC`** | Data Classification main screen |
| 2 | Browse the classification entries | Table names mapped to labels |

**Confirm these three entries exist:**

| Table | Classification | What it contains |
|---|---|---|
| `SCUSTOM` | `Restricted-PII` | Passenger names, addresses, phone, email, payment ref |
| `SBOOK` | `Internal-Financial` | Booking records, prices, payment amounts |
| `SCARR` | `Public` | Airline carrier names — public reference data |

> ⚠️ If any of these are missing or wrong — tell your instructor before continuing.

---

## Step 2 — Find the Runtime Attribute

Classification labels don't automatically reach Pathlock policies — a **Data Attribute** bridges them.

| # | Action | What you see |
|---|---|---|
| 1 | Run **`/N/APPSDM/ABAC`** → **Functional Configuration** tab | Left tree |
| 2 | Expand **Policy Information Point** → **Data Attribute Master** | Attribute list |
| 3 | Find and open **`DATA.CLASS_LABEL`** | Attribute detail screen |
| 4 | Read the description — note what this attribute captures at runtime | — |

> **`DATA.CLASS_LABEL`** reads the classification label of the table currently open in SE16.
> At runtime, when a user is in `SCUSTOM`, its value is `Restricted-PII`.
> When they're in `SCARR`, its value is `Public`.

> **This is the key insight:** any policy that references `DATA.CLASS_LABEL` works for
> *all* classified tables — past, present and future. You classify once, the controls follow.

---

## 🏆 Completion Code

**The completion code is the classification label assigned to `SCUSTOM` in `/APPSDM/DC`.**

Enter it on the leaderboard exactly as it appears — capital letters, hyphen included.

---

## What you learned

| Concept | Meaning |
|---|---|
| **Data Classification** | Labels that describe data sensitivity — `Restricted-PII`, `Internal-Financial`, `Public` |
| **`DATA.CLASS_LABEL`** | Runtime attribute that makes the classification label available to any DAC policy |
| **Tag once, control everywhere** | Classify a table once — all downstream policies apply automatically |

> **Level 8 builds directly on this:** you'll use `DATA.CLASS_LABEL` to block exports of
> `Restricted-PII` and `Internal-Financial` data while allowing `Public` data through.

*Next: [Level 8 — Export Block →](/levels/8)*
