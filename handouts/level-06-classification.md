# Level 5 — Data Classification: Tag the Data

**Meridian AG Audit Remediation — Pathlock DAC/ABAC Workshop**

---

| | |
|---|---|
| 🎯 **Goal** | Understand how Pathlock classifies SAP tables — and why classification is the foundation for all downstream controls |
| ⏱ **Time** | 10 minutes |
| 🏆 **Points** | 100 |
| 💡 **Difficulty** | 🟠 Independent |

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

> **Level 6 builds directly on this:** you'll use `DATA.CLASS_LABEL` to block exports of
> `Restricted-PII` and `Internal-Financial` data while allowing `Public` data through.
