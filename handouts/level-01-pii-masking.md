# Level 1 — Passenger PII: Mask the Email Field

**Meridian AG Audit Remediation — Pathlock DAC/ABAC Workshop**

---

| | |
|---|---|
| 🎯 **Goal** | Create a Pathlock DAC masking policy to hide passenger email addresses in SAP |
| ⏱ **Time** | 15–20 minutes |
| 🏆 **Points** | 100 |
| 💡 **Difficulty** | 🟢 Guided |

---

## Background

The DPA audit finding #1 reads:

> *"All authenticated users can view the full email address, phone number and postal code of every passenger in the SCUSTOM table without restriction. No masking or access control is applied."*

Your task: create a DAC masking policy that hides the **email address** field in `SCUSTOM` for your user.

The Pathlock DAC tool is accessed in SAP via transaction **`/N/APPSDM/ABAC`** — or through the SAP menu: **Pathlock DAC → Pathlock ABAC**.

---

## Step 1 — Verify the Problem

Before you fix it, confirm what you are fixing.

| # | Action | What you see |
|---|---|---|
| 1 | In SAP, type `SE16N` → **Enter** | General Table Display |
| 2 | Table: `SCUSTOM` → **Execute (F8)** | Passenger records |
| 3 | Find the `EMAIL` column | Full email addresses visible — e.g. `max.mueller@gmail.com` |

Note the email of any passenger — you will verify it is masked after completing this level.

---

## Step 2 — Define a Data Attribute

A Data Attribute tells Pathlock DAC *what* data to act on.

| # | Action |
|---|---|
| 1 | Run transaction **`/N/APPSDM/ABAC`** |
| 2 | In the left navigation tree, click **Data Attribute Master** |
| 3 | Click **New Entry** (or the ➕ button) |
| 4 | Fill in the fields as shown below |
| 5 | Click **Save** |

**Data Attribute values:**

| Field | Value |
|---|---|
| Attribute ID | `DATA.CUSTOMER_EMAIL` |
| Description | `Passenger Email Address` |

> **Note:** All Data Attributes must start with the prefix `DATA.`

---

## Step 3 — Create a Policy

A Policy defines *when* masking applies — in this case, always (no conditions = mask for everyone).

| # | Action |
|---|---|
| 1 | In the left tree, click **Policy Administration Point** |
| 2 | Click **New Entry** |
| 3 | Fill in the policy details below |
| 4 | Leave rules blank for now — no conditions means the policy always triggers |
| 5 | Click **Save** |

**Policy values:**

| Field | Value |
|---|---|
| Policy Name | `MASK_PASSENGER_EMAIL` |
| Description | `Mask passenger email address for all users` |

---

## Step 4 — Configure Policy Enforcement Point (Data Masking)

This links the policy to the data attribute and activates masking.

| # | Action |
|---|---|
| 1 | In the left tree, click **Policy Enforcement Point** → **Data Masking** |
| 2 | Click **New Entry** |
| 3 | Fill in the values below |
| 4 | Click **Save** |

**Enforcement Point values:**

| Field | Value |
|---|---|
| Policy | `MASK_PASSENGER_EMAIL` |
| Attribute | `DATA.CUSTOMER_EMAIL` |
| Action | `Mask` |

---

## Step 5 — Technical Mapping

This tells DAC which SAP field to physically mask — by linking your Data Attribute to a **SAP Data Element**.

| # | Action |
|---|---|
| 1 | In the left tree, click **Technical Configuration** → **Data Attribute Configuration** → **Technical Mapping** |
| 2 | Find your attribute `DATA.CUSTOMER_EMAIL` (or click New Entry) |
| 3 | In the **Data Element** field, you need to enter the technical data element name for the email field in `SCUSTOM` |
| 4 | To find it: open a **new SAP session**, go to `SE16N` → `SCUSTOM`, click on the `EMAIL` column header → press **F1** → click the **Technical Info** button |
| 5 | Note the **Data Element** shown — this is your answer |
| 6 | Enter that Data Element in the Technical Mapping → **Save** |

> 💡 The Data Element name you discover here is also your **Level 1 completion code**.

---

## Step 6 — Verify Masking Works

| # | Action | What you see |
|---|---|---|
| 1 | Go back to `SE16N` → `SCUSTOM` → **Execute** | The `EMAIL` column should now show `***` for all passengers |
| 2 | If it still shows plain text, log out and log back in — the policy takes effect on next session | — |

---

## 🏁 Completion

You have created your first Pathlock DAC masking policy. Passenger email addresses are now hidden at the data layer — not just the UI.

**Claim your Level 1 points:**
Go to the **[leaderboard](http://152.53.187.143:9000)** → **Submit Code** → select **L1 — PII Masking** → enter the SAP Data Element you discovered in Step 5.

<details>
<summary>💬 <strong>Hint</strong> — click to reveal</summary>
<br>

In SE16N → SCUSTOM, click on the EMAIL column header and press **F1**. In the F1 help popup, click the **Technical Info** button. The Data Element field is your answer — enter it exactly as shown (uppercase).

</details>

---

## Troubleshooting

| Symptom | Solution |
|---|---|
| `/N/APPSDM/ABAC` gives "No authorization" | Ask your instructor — your user may be missing the `/APPSDM/POL_CHANGE` role |
| Masking not visible after saving policy | Log out of SAP and log back in — policies are evaluated at session start |
| F1 help shows no Technical Info button | Make sure you clicked directly on a field/column header, not on a value |
| EMAIL column still shows plain text after re-login | Verify the Data Element in Technical Mapping is saved correctly and matches exactly |
| Policy save fails | Check that Attribute ID starts with `DATA.` and Policy name has no spaces |

---

*Next: [Level 2 — Contextual Access →](level-02-contextual-access.md)*
