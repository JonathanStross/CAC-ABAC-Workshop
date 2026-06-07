# Level 5 — Block the Data Export

**Meridian AG Audit Remediation — Pathlock DAC/ABAC Workshop**

---

| | |
|---|---|
| 🎯 **Goal** | Configure a DAC policy that blocks sensitive data exports while allowing public data downloads |
| ⏱ **Time** | 15–20 minutes |
| 🏆 **Points** | 150 |
| 💡 **Difficulty** | 🟠 Independent |

---

## Background

The DPA audit finding #5 reads:

> *"Users can export SCUSTOM and SBOOK data to local Excel files via SE16. No data classification exists — Pathlock cannot distinguish between SCARR (public reference data) and SCUSTOM (PII). Data leaves the system without restriction or audit trail."*
> — *ISO 27001 A.8.12, GDPR Art. 32, PCI DSS Req. 3*

**Your task:** Configure a Pathlock DAC policy that:
- ❌ **Blocks** export of `SCUSTOM` (passenger PII) — classification: `Restricted-PII`
- ❌ **Blocks** export of `SBOOK` (booking/financial data) — classification: `Internal-Financial`
- ✅ **Allows** export of `SCARR` (carrier reference data) — classification: `Public`

The policy must fire based on **data classification** — not by hardcoding table names.
This is the scalable model: tag the data once, the controls follow automatically.

---

## Background — How the download block works

SAP GUI export actions are triggered by specific ok-codes:

| Ok-code | Triggered by |
|---|---|
| `%EX` | Export to local file |
| `%PC` | PC download |
| `&XXL` | Excel/spreadsheet export |

Pathlock intercepts these **before** the file is written:
1. Detects the ok-code (via `DATA.BUTTON_OK_CODE`)
2. Reads the classification of the active table (via `DATA.CLASS_LABEL`)
3. Evaluates the policy — blocks or allows

> This is **Data Blocking** — different from masking.
> Masking hides a value but lets the action proceed.
> Blocking **prevents the action entirely** — no data leaves the system.

---

## Step 1 — Confirm the Problem

First, verify that a download is currently possible.

| # | Action | What you see |
|---|---|---|
| 1 | Run `SE16` → table `SCUSTOM` → **Execute (F8)** | Passenger records with PII visible |
| 2 | Click **System → List → Save → Local File** (or press `%PC` / `Ctrl+Shift+F7`) | A file download dialog appears |
| 3 | Note: the download succeeds — no block ⚠️ | File saved to your desktop |

---

## Step 2 — Understand the Data Attributes

Three Data Attributes are pre-configured and make this level possible.
Go find them in `/N/APPSDM/ABAC`.

| # | Action | What you see |
|---|---|---|
| 1 | Run **`/N/APPSDM/ABAC`** → **Functional Configuration** tab | Left tree |
| 2 | Expand **Policy Information Point** → **Data Attribute Master** | Attribute list |
| 3 | Find and open each of these three attributes | |

| Attribute | What it captures at runtime |
|---|---|
| `DATA.BUTTON_OK_CODE` | The ok-code the user clicked (`%EX`, `%PC`, `&XXL`) |
| `DATA.TABLE_NAME` | The SAP table currently open in SE16 |
| `DATA.CLASS_LABEL` | The **classification label** of that table (the key one) |

> **The "aha":** `DATA.CLASS_LABEL` is what turns a table name into a business classification.
> The policy reads the label — not the table. Classify once, control everywhere.

---

## Step 3 — Check the Data Classification

Confirm that the tables are classified correctly in `/APPSDM/DC`.

| # | Action | What you see |
|---|---|---|
| 1 | Run **`/APPSDM/DC`** | Data Classification main screen |
| 2 | Find the classification entries for each table | |

| Table | Expected classification |
|---|---|
| `SCUSTOM` | `Restricted-PII` |
| `SBOOK` | `Internal-Financial` |
| `SCARR` | `Public` |

> ✅ If these are set correctly — the policy you configure in the next step will automatically
> block the right tables. No table names in the policy at all.

---

## Step 4 — Configure the Policy

The policy `BLOCK_DOWNLOAD_BY_CLASSIFICATION` has been created for you.
Find it, inspect it, make sure it is **active**, and confirm its rules.

| # | Action | What you see |
|---|---|---|
| 1 | In `/N/APPSDM/ABAC` → **Functional Configuration** tab | Left tree |
| 2 | Expand **Policy Administration Point** | Policy list |
| 3 | Find and open `BLOCK_DOWNLOAD_BY_CLASSIFICATION` | Policy detail screen |
| 4 | Check that the policy **Status is Active** | Green / Active indicator |
| 5 | Check that it is assigned to **Policy Enforcement Point → Data Restriction** | Enforcement type shown |

**Read the rule condition:**

The policy should fire when **both** of these are true:
- `DATA.BUTTON_OK_CODE` is one of: `%EX`, `%PC`, `&XXL`
- `DATA.CLASS_LABEL` is one of: `Restricted-PII`, `Internal-Financial`

> If the classification is `Public` — neither condition is fully met → **download allowed**.

---

## Step 5 — Test the Block

Now test all three cases from SE16.

| # | Table | Expected result | What you should see |
|---|---|---|---|
| 1 | `SCUSTOM` | ❌ **BLOCK** | Message: *"Pathlock ABAC: You don't have permission to download this data."* |
| 2 | `SBOOK` | ❌ **BLOCK** | Same block message |
| 3 | `SCARR` | ✅ **ALLOW** | Download dialog appears — file saved successfully |

**Test procedure for each table:**

| # | Action |
|---|---|
| 1 | Run `SE16` → enter table name → **Execute (F8)** |
| 2 | Attempt export: **System → List → Save → Local File** |
| 3 | Observe the result and record pass/fail |

> ⚠️ If `SCARR` is unexpectedly blocked — check whether a second policy
> `BLOCK_TABLE_DOWNLOAD` is accidentally **active**. If so, deactivate it.

---

## 🏆 Completion Code

Once all three tests pass — go back to `/N/APPSDM/ABAC` → **Functional Configuration** →
**Policy Administration Point** → open `BLOCK_DOWNLOAD_BY_CLASSIFICATION`.

**The completion code is the classification label that blocks SCUSTOM exports.**

> 💡 You found it in Step 3. It's one of the values in the `DATA.CLASS_LABEL` condition
> in this policy. Enter it on the leaderboard exactly as it appears.

---

## Troubleshooting

| Problem | Check |
|---|---|
| Sensitive table still downloads | Is `BLOCK_DOWNLOAD_BY_CLASSIFICATION` active and assigned to Data Restriction? |
| `SCARR` is blocked | Is `BLOCK_TABLE_DOWNLOAD` accidentally active? Deactivate it. |
| No block message appears | Ask your instructor — this is a system configuration issue, not your policy |
| Policy does not evaluate at all | Ask your instructor |

---

## What you learned

| Concept | Meaning |
|---|---|
| **Data Blocking** | Prevents the action — no data leaves the system (vs masking which hides values) |
| **Data Classification** | Labels that describe the sensitivity of data — `Restricted-PII`, `Internal-Financial`, `Public` |
| **Classification-driven policy** | One policy rule covers all classified tables — no per-table hardcoding needed |
| **`DATA.CLASS_LABEL`** | The runtime attribute that bridges classification → policy enforcement |

> *"The data leaving the building is the breach. We stopped it at the door."*
