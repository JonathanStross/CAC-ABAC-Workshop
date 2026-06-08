# Level 4 — Audit Feed: Who Saw What, and When?

**Meridian AG Audit Remediation — DAC: Practitioner Level**

---

| | |
|---|---|
| 🎯 **Goal** | Enable data access logging on a sensitive field, generate access events, and read the audit feed |
| ⏱ **Time** | 15 minutes |
| 🏆 **Points** | 150 |
| 💡 **Difficulty** | 🟡 Hints |

---

## Background

The DPA audit finding #4 reads:

> *"When asked to provide evidence of who accessed passenger email addresses and credit card references in the last 30 days, Meridian AG could not answer. No data access logging exists at the field level. The DPA expects a full access log: user, timestamp, transaction, field, and whether the value was masked or visible at time of access. GDPR Art. 30 — records of processing activities. SOX Section 404."*

You have been masking and blocking data since L1. But can you prove it? Can you tell an auditor exactly which user accessed `EMAIL` at 14:32 last Thursday — and whether they saw the real value or `***`?

This level activates the **DAC Feed** — Pathlock's real-time access log at the data attribute level.

---

## What the DAC Feed Records

Every time a policy-governed field is accessed, Pathlock can log:

| Field | Description |
|---|---|
| **User** | SAP username of the accessing user |
| **Timestamp** | Exact date and time of access |
| **Transaction** | TCode used (e.g. `SE16`, `FB01`) |
| **Data Attribute** | Which attribute was accessed (`DATA.S_EMAIL`, `DATA.LOCCURAM`, …) |
| **Table / Field** | SAP table and field name |
| **Masked?** | Whether the policy masked the value or allowed it through |
| **Policy** | Which policy triggered (or why none did) |

This is the forensic record. It answers the auditor's question in seconds.

---

## Step 1 — Enable Logging on a Data Attribute

| # | Action | What you see |
|---|---|---|
| 1 | Run **`/N/APPSDM/ABAC`** | Pathlock ABAC main screen |
| 2 | Click the **Functional Configuration** tab | Left tree updates |
| 3 | Expand **Policy Information Point** → **Data Attribute Master** | Attribute list |
| 4 | Open **`DATA.S_EMAIL`** | Attribute detail screen |
| 5 | Click **Change Mode** (pencil icon) | Edit mode |
| 6 | Find the **Logging** flag or **Access Logging** checkbox | Enable it |
| 7 | Save | Logging active for this attribute |

Repeat for **`DATA.LOCCURAM`** — the credit card reference field.

> 💡 Logging is attribute-level — you enable it once per attribute, and every access to that field across all tables and transactions is recorded automatically.

---

## Step 2 — Generate Access Events

Now create log entries. Run the following in your SAP session:

| # | Action |
|---|---|
| 1 | `SE16` → `SCUSTOM` → Execute (F8) — scroll through the results |
| 2 | `SE16` → `SBOOK` → Execute (F8) — scroll through the results |
| 3 | Run `SE16` → `SCUSTOM` a second time |

Each of these accesses a logged attribute and creates a record in the DAC Feed.

---

## Step 3 — Open the DAC Feed

| # | Action | What you see |
|---|---|---|
| 1 | In **`/N/APPSDM/ABAC`**, click the **Functional Configuration** tab | Left tree updates |
| 2 | Look for **Access Log** or **DAC Feed** in the left tree | The access log viewer |
| 3 | Set filter: **Attribute** = `DATA.S_EMAIL` | Filtered results |
| 4 | Check the timestamp, username, TCode and masked flag for your entries | Your access events visible ✅ |

> **The completion code** is shown in a specific column of your log entries. Look carefully at all column values in one of your own access records — you will find it. 🏆

---

## Step 4 — Answer the Auditor's Question

Using the log, fill in the following:

| Question | Your answer |
|---|---|
| How many times did you access `DATA.S_EMAIL` in the last 10 minutes? | |
| Was the field masked or visible during each access? | |
| Which TCode was used for each access? | |

This is a real GDPR Art. 30 access record. You just produced it in under 2 minutes.

---

## Debrief

| Question | Answer |
|---|---|
| What was needed in SAP to enable this? | **Nothing** — no authorisation change, no ABAP development |
| Does logging slow down SAP performance? | Minimal — it is asynchronous |
| Can you log access to unmasked fields too? | Yes — logging is independent of masking |
| Who can read the DAC Feed? | Pathlock admins and authorised compliance officers |
| Can you export the log? | Yes — to CSV/Excel for audit evidence packages |

---

## 🏆 Submit Your Code

Enter the completion code you found in the DAC Feed at **`https://pathlock.academy/submit`**

> **Compliance note:** GDPR Art. 30 — records of processing activities | GDPR Art. 32 — evidence of technical measures | SOX Section 404 — ITGC audit evidence | ISO 27001 A.8.15 — logging and monitoring
