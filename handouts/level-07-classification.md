# Level 7 — Regional Access: Your Business Unit Shapes Your View

**Meridian AG Audit Remediation — DAC: Practitioner Level**

---

| | |
|---|---|
| 🎯 **Goal** | Discover how a single SAP role controls which **rows** of data you see — without any ABAP change, table split, or authorization object |
| ⏱ **Time** | 15 minutes |
| 🏆 **Points** | 100 |
| 💡 **Difficulty** | 🟡 Hints |

---

## Background

The DPA audit finding #6 reads:

> *"All booking agents, regardless of business unit, can browse the full SCUSTOM passenger table — including records belonging to regional subsidiaries they have no business need to access. No regional data separation exists. GDPR Art. 5(1)(b) — purpose limitation violation."*

Meridian AG operates across multiple European markets. German-market passenger records are managed by the **German business unit** — other analysts have no legitimate reason to view them.

The solution is **row-level access control**: users without the `Z_GERMAN` business unit role see a filtered result set. German passenger entries simply do not appear. Same table. Same transaction. Same SAP role. Fewer rows.

---

## Step 1 — Establish a Baseline

First, run `SE16` on `SCUSTOM` and note what you see.

| # | Action | What you see |
|---|---|---|
| 1 | Run `SE16` in SAP → table `SCUSTOM` → **Execute (F8)** | Full passenger list |
| 2 | Note the **total row count** (bottom status bar) | e.g. `135 entries` |
| 3 | Look for entries where **`COUNTRY`** = `DE` | German passenger records |

> ⚠️ Write down the **total row count** and how many German entries (`COUNTRY = DE`) you can see. You will compare this after the policy is applied.

---

## Step 2 — Check Your Business Unit Role

| # | Action | What you see |
|---|---|---|
| 1 | Run `SU01` in SAP | User maintenance |
| 2 | Enter your SAP username → **Execute (F8)** | Your user master record |
| 3 | Click the **Roles** tab | List of assigned roles |
| 4 | Look for a role named **`Z_GERMAN`** | Present or absent |

> Note whether `Z_GERMAN` is assigned to your user — this determines what you will see after the policy is active.

---

## Step 3 — Find the Row-Level Policy

The instructor has pre-configured a Data Restriction policy that enforces the business unit separation. Locate it and read its logic.

| # | Action | What you see |
|---|---|---|
| 1 | Run **`/N/APPSDM/ABAC`** → **Functional Configuration** tab | Left tree updates |
| 2 | Double-click **Policy Administration Point** | All policies |
| 3 | Find and open **`RESTRICT_GERMAN_BU`** | Policy detail screen |
| 4 | Read the **Condition** | `USER.ROLE NOT EQ Z_GERMAN` |
| 5 | Read the **Action** | Data Restriction on `DATA.S_COUNTRY` — value `DE` |

**What this means:**

| If... | Then... |
|---|---|
| `USER.ROLE NOT EQ Z_GERMAN` evaluates to **TRUE** (you don't have the role) | All rows where `COUNTRY = DE` are removed from the SE16 result set |
| `USER.ROLE NOT EQ Z_GERMAN` evaluates to **FALSE** (you have the role) | No restriction — full result set returned |

> This is **row-level access control** — not masking. The rows are absent, not starred out.
> A user without `Z_GERMAN` cannot even tell how many German records exist.

---

## Step 4 — Test: Run SE16 Again

| # | Action | Expected result |
|---|---|---|
| 1 | Run `SE16` → table `SCUSTOM` → **Execute (F8)** | Result set loads |
| 2 | Check the **total row count** | Compare with your Step 1 baseline |
| 3 | Filter for `COUNTRY = DE` | Result depends on your role (see below) |

| Your role | What you see |
|---|---|
| **Has `Z_GERMAN`** | Same count as Step 1 — German rows visible ✅ |
| **No `Z_GERMAN`** | Lower count — German rows silently absent 🚫 |

> If you don't have `Z_GERMAN`: the row count in Step 4 will be lower than Step 1.
> The difference = the number of German passenger records you are no longer permitted to see.

---

## Step 5 — The Partner Comparison

Compare results with a colleague who has the opposite role assignment.

| | Without `Z_GERMAN` | With `Z_GERMAN` |
|---|---|---|
| SCUSTOM row count | Lower | Full |
| `COUNTRY = DE` filter result | 0 entries | German records visible |
| Any error or warning shown? | ❌ None | ✅ Full view |

> This is the key implication: a user without the role doesn't see an error or a masked value —
> they simply see a shorter list. They have no way to know what they are missing.
> This is the strongest form of data segregation.

---

## Step 6 — The Insight: Role as a Data Gate

Every previous level used `USER.ROLE` as a **condition** to decide *how* data is presented (masked or blocked). This level uses it to decide *whether* data is returned at all.

| Level | Attribute | Effect |
|---|---|---|
| L2 | `USER.ID` | Field masked for specific user |
| L3 | `USER.NETWORK` | Field masked based on source IP |
| L4 | `USER.TIME` | TCode blocked outside hours |
| L6 | `USER.ROLE` | TCode blocked for non-privileged roles |
| **L7** | **`USER.ROLE`** | **Rows removed — data never returned** |

**What changed in SAP?**
- No authorization object added or removed
- No table partitioned or split
- No ABAP developed
- One DAC policy, one role, one country code — full regional data separation

---

## 🏆 Completion Code

**The completion code is the name of the SAP role that grants access to German entries.**

Enter it exactly as it appears in the policy condition — uppercase, underscore included.

---

## What You Learned

| Concept | Meaning |
|---|---|
| **Row-level access control** | Rows are filtered out of the result set entirely — not masked |
| **`USER.ROLE` as a data gate** | A role controls not just what you can do, but what data you can see |
| **Silent exclusion** | Users without the role see a shorter list with no indication that records are missing |
| **No SAP changes** | Zero authorization objects, zero ABAP — pure DAC policy |
| **Regional data separation** | Business unit boundaries enforced at the data layer, not the application layer |

---

> **Level 8** uses data classification labels (pre-configured by the instructor) to block
> data exports — `Restricted-PII` and `Internal-Financial` tables stay in SAP, `Public` data flows freely.

*Next: [Level 8 — Export Block →](/levels/8)*
