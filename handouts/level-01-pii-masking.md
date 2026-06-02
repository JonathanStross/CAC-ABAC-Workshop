# Level 1 — Passenger PII: Create Your First Masking Rule

**Meridian AG Audit Remediation — Pathlock DAC/ABAC Workshop**

---

| | |
|---|---|
| 🎯 **Goal** | Create a Pathlock DAC masking policy that hides passenger email addresses — for your user only |
| ⏱ **Time** | 15–20 minutes |
| 🏆 **Points** | 100 |
| 💡 **Difficulty** | 🟢 Guided |

---

## Background

The DPA audit finding #1 reads:

> *"All authenticated users can view the full email address of every passenger in table SCUSTOM without restriction. No masking or access control is applied."*

Your task: use Pathlock DAC to create a masking policy that hides the `EMAIL` field in `SCUSTOM` — scoped to **your own SAP user**.

All configuration is done inside SAP via transaction **`/N/APPSDM/ABAC`**
(or menu path: **Pathlock DAC → Pathlock ABAC**).

---

## Step 1 — Verify the Problem & Identify the Data Element

First, confirm the issue is real — and find the technical identifier for the email field.

| # | Action | What you see |
|---|---|---|
| 1 | In SAP, run `SE16N` → table `SCUSTOM` → **Execute (F8)** | Passenger records with full email addresses |
| 2 | Click on the **`EMAIL` column header** to select the column | Column highlighted |
| 3 | Press **F1** | SAP help popup opens |
| 4 | Click **Technical Info** (button in the popup) | Technical details for the field |
| 5 | Note the value in the **Data Element** field | You should see `AD_SMTPADR` |

> ⚠️ Write down `AD_SMTPADR` — you will need it in the next step.

---

## Step 2 — Explore the Data Attribute

A **Data Attribute** in Pathlock DAC defines *what data* a policy acts on. It is linked to SAP via the Data Element you just found. This attribute has been pre-created in the system — go find it and confirm the mapping.

| # | Action | What you see |
|---|---|---|
| 1 | Run **`/N/APPSDM/ABAC`** | Pathlock ABAC main screen |
| 2 | Expand **Functional Configuration** in the left tree | Sub-items appear |
| 3 | Click **Data Attribute Master** | List of data attributes |
| 4 | Find and open **`DATA.CUSTOMER_EMAIL`** | Attribute detail screen |
| 5 | Look at the **Technical Mapping** section / tab | You should see `AD_SMTPADR` already listed — the same Data Element from Step 1 ✅ |
| 6 | Read the **Description** field at the top — note it down | This is part of your completion code |

> **Convention:** All Data Attributes start with `DATA.`  
> **The "aha":** DAC bridges the gap between a business concept (`DATA.CUSTOMER_EMAIL`) and the SAP technical layer (`AD_SMTPADR`). You found both ends yourself.

---

## Step 3 — Explore the User Attribute

A **User Attribute** defines *who* the policy applies to. Again, this has been pre-created.

| # | Action |
|---|---|
| 1 | Still in **`/N/APPSDM/ABAC`**, click **User Attribute Master** |
| 2 | Find and open the attribute **`USER.ID`** |
| 3 | Read its description — this attribute holds the **logged-in user's SAP username** at runtime |

> **Convention:** All User Attributes must start with `USER.`

---

## Step 4 — Create Your Policy

A **Policy** is the rule engine that ties data attributes and user attributes together. You will create your own personal policy now.

| # | Action |
|---|---|
| 1 | Click **Policy Administration Point** in the left tree |
| 2 | Click **New Entry** |
| 3 | Fill in the fields below — use your own SAP username in the policy name to keep it unique |
| 4 | Click **Save** |

**Policy values:**

| Field | Value |
|---|---|
| Policy Name | `MASK_EMAIL_<YOURUSERNAME>` — e.g. `MASK_EMAIL_AMUELLER` |
| Description | `Mask passenger email for my user` |

---

## Step 5 — Add a Rule Condition

The rule defines *when* the policy triggers. You will scope it to your own user so it only affects you.

| # | Action |
|---|---|
| 1 | Inside your new policy, click **Rules** → **New Entry** |
| 2 | Set the condition as shown below |
| 3 | Click **Save** |

**Rule condition:**

| Field | Value |
|---|---|
| User Attribute | `USER.ID` |
| Operator | `EQ` (equals) |
| Value | Your SAP username — e.g. `AMUELLER` (uppercase) |

> This means: *"Only apply this policy when the logged-in user is me."*

---

## Step 6 — Configure the Policy Enforcement Point

This is where you activate masking and link the policy to the data attribute.

| # | Action |
|---|---|
| 1 | In the left tree, click **Policy Enforcement Point** → **Data Masking** |
| 2 | Click **New Entry** |
| 3 | Fill in the values below |
| 4 | Click **Save** |

**Enforcement Point values:**

| Field | Value |
|---|---|
| Policy | `MASK_EMAIL_<YOURUSERNAME>` |
| Attribute | `DATA.CUSTOMER_EMAIL` |

---

## Step 7 — Verify Masking Works

| # | Action | What you see |
|---|---|---|
| 1 | **Log out** of SAP and **log back in** — policies are evaluated at session start |
| 2 | Run `SE16N` → table `SCUSTOM` → **Execute** | The `EMAIL` column now shows `***` for all passengers |
| 3 | Ask a colleague to check `SCUSTOM` on their screen | Their email column is still visible — your policy only affects your user ✅ |

---

## 🏁 Completion

You have created your first Pathlock DAC masking policy. Passenger emails are now masked at the data layer for your user — regardless of which transaction or screen they appear in.

**Claim your Level 1 points:**
Go to the **[leaderboard](http://152.53.187.143:9000)** → **Submit Code** → select **L1 — PII Masking** → enter the code.

<details>
<summary>💬 <strong>Hint</strong> — click to reveal</summary>
<br>

The code is built from the two attributes you explored in Steps 2 and 3:

1. The **name** of the User Attribute you found in Step 3
2. The **Description value** of `DATA.CUSTOMER_EMAIL` from Step 2

Concatenate them with an underscore: `<UserAttributeName>_<DescriptionValue>`

> Still stuck? The Description of `DATA.CUSTOMER_EMAIL` matches the Data Element you found via F1 in Step 1.

</details>

---

## Troubleshooting

| Symptom | Solution |
|---|---|
| `/N/APPSDM/ABAC` gives "No authorization" | Raise your hand — your user may be missing the `/APPSDM/POL_CHANGE` role |
| Policy save fails with "duplicate name" | Add your username to the policy name to make it unique |
| `EMAIL` still visible after re-login | Check that the Rule condition uses your exact SAP username (uppercase) and that the Enforcement Point is saved |
| Colleague's email is also masked | Your rule condition is missing or has the wrong username — check Step 5 |
| Policy save fails | Check that Attribute ID starts with `DATA.` and Policy name has no spaces |

---

*Next: [Level 2 — Contextual Access →](level-02-contextual-access.md)*
