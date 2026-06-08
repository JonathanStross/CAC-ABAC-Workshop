# Level 8 — Block the Data Export

**Meridian AG Audit Remediation — Pathlock DAC/ABAC Workshop**

---

| | |
|---|---|
| 🎯 **Goal** | Activate a classification-driven download block — sensitive data stays in SAP, public data flows freely |
| ⏱ **Time** | 10 minutes |
| 🏆 **Points** | 100 |
| 💡 **Difficulty** | 🟠 Independent |

---

## Background

You've tagged the data in Level 7. Now put it to work.

> *"Users can export SCUSTOM and SBOOK data to local Excel files via SE16 — no restriction exists."*

**Your task:** Activate the policy `BLOCK_DOWNLOAD_BY_CLASSIFICATION` and verify it blocks
`Restricted-PII` and `Internal-Financial` tables while allowing `Public` ones.

**How the block works:**

SAP GUI export actions use ok-codes:

| Ok-code | Triggered by |
|---|---|
| `%EX` | Export to local file |
| `%PC` | PC download |
| `&XXL` | Excel / spreadsheet export |

Pathlock intercepts these **before** the file is written — checks `DATA.CLASS_LABEL` — and blocks if the label is `Restricted-PII` or `Internal-Financial`.

> **Data Blocking ≠ Masking.**
> Masking hides a value but lets the action proceed.
> Blocking **prevents the action entirely** — no data leaves the system.

---

## Step 1 — Confirm the Problem First

| # | Action | What you see |
|---|---|---|
| 1 | Run `SE16` → table `SCUSTOM` → **Execute (F8)** | Passenger records |
| 2 | **System → List → Save → Local File** | Download dialog — succeeds ⚠️ |

No block yet. That's the finding. Now fix it.

---

## Step 2 — Activate the Policy

| # | Action | What you see |
|---|---|---|
| 1 | Run **`/N/APPSDM/ABAC`** → **Functional Configuration** tab | Left tree |
| 2 | Expand **Policy Administration Point** → open the policy list | All policies |
| 3 | Find **`BLOCK_DOWNLOAD_BY_CLASSIFICATION`** and open it | Policy detail |
| 4 | Check it is **Active** and assigned to **Data Restriction** enforcement | ✅ |

**Confirm the rule condition reads:**

| Attribute | Condition |
|---|---|
| `DATA.BUTTON_OK_CODE` | is one of `%EX`, `%PC`, `&XXL` |
| `DATA.CLASS_LABEL` | is one of `Restricted-PII`, `Internal-Financial` |

> If `DATA.CLASS_LABEL = Public` → neither condition fully matches → **download allowed.**
> This is why `SCARR` passes through automatically — no exception needed.

> ⚠️ There is a second policy `BLOCK_TABLE_DOWNLOAD` — make sure it is **inactive**.
> Leave it alone if it is already inactive.

---

## Step 3 — Test All Three Cases

| # | Table | Classification | Expected result |
|---|---|---|---|
| 1 | `SCUSTOM` | `Restricted-PII` | ❌ **BLOCKED** |
| 2 | `SBOOK` | `Internal-Financial` | ❌ **BLOCKED** |
| 3 | `SCARR` | `Public` | ✅ **ALLOWED** |

**Test procedure (repeat for each table):**

| # | Action |
|---|---|
| 1 | `SE16` → enter table name → **Execute (F8)** |
| 2 | **System → List → Save → Local File** |
| 3 | Blocked tables show: *"Pathlock ABAC: You don't have permission to download this data."* |

---

## 🏆 Completion Code

All three tests pass? Go to `/N/APPSDM/ABAC` → **Policy Administration Point** →
open `BLOCK_DOWNLOAD_BY_CLASSIFICATION`.

**The completion code is the exact name of this policy** — as it appears in the Policy Name field.

Enter it on the leaderboard exactly as shown, uppercase, underscores included.

---

## Troubleshooting

| Problem | Check |
|---|---|
| Sensitive table still downloads | Is `BLOCK_DOWNLOAD_BY_CLASSIFICATION` active and set to Data Restriction? |
| `SCARR` is unexpectedly blocked | Is `BLOCK_TABLE_DOWNLOAD` accidentally active? Deactivate it. |
| No block message at all | Ask your instructor — system config issue, not your policy |

---

## What you learned

| Concept | Meaning |
|---|---|
| **Data Blocking** | Prevents the action — no data leaves (vs masking which hides values) |
| **Classification-driven policy** | One policy covers all classified tables — no table names hardcoded |
| **`DATA.BUTTON_OK_CODE`** | Detects which export action the user triggered |
| **`DATA.CLASS_LABEL`** | Reads the classification of the active table at runtime |

> *"The data leaving the building is the breach. We stopped it at the door."*

*Next: [Level 9 — Fiori / OData Masking →](/levels/9)*
