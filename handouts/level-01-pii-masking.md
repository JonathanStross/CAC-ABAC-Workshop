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

## Step 1 — Verify the Problem

| # | Action | What you see |
|---|---|---|
| 1 | In SAP, run `SE16N` → table `SCUSTOM` → **Execute (F8)** | Passenger records |
| 2 | Find the `EMAIL` column | Full email addresses — e.g. `max.mueller@gmail.com` |

Note any email address. After completing this level you will come back and confirm it is masked.

---

## Step 2 — Explore the Data Attribute

A **Data Attribute** defines *what data* the policy will act on. The attribute for email has been pre-created in the system.

| # | Action |
|---|---|
| 1 | Run **`/N/APPSDM/ABAC`** |
| 2 | In the left navigation tree, expand **Functional Configuration** |
| 3 | Click **Data Attribute Master** |
| 4 | Find and open the attribute **`DATA.CUSTOMER_EMAIL`** |
| 5 | Read the **Description** field — note it down |

> **Convention:** All Data Attributes must start with `DATA.` — you will see this pattern throughout the workshop.

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

The code is hidden in plain sight inside the tool you just used. Go back to **`/N/APPSDM/ABAC`** → **Data Attribute Master** → open **`DATA.CUSTOMER_EMAIL`** → read the Description field.

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
