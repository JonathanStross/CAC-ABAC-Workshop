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
| 1 | In SAP, run `SE16` → table `SCUSTOM` → **Execute (F8)** | Passenger records with full email addresses |
| 2 | Click on the **`EMAIL` column header** to select the column | Column highlighted |
| 3 | Press **F1** | SAP help popup opens |
| 4 | Click **Technical Info** (button in the popup) | Technical details for the field |
| 5 | Note the value in the **Data Element** field | You should see `S_EMAIL` |

> ⚠️ Write down `S_EMAIL` — you will need it in the next step.

---

## Step 2 — Explore the Data Attribute

A **Data Attribute** in Pathlock DAC defines *what data* a policy acts on. It is linked to SAP via the Data Element you just found. This attribute has been pre-created in the system — go find it and then trace the mapping all the way down to the SAP field.

**2a — Open the attribute**

| # | Action | What you see |
|---|---|---|
| 1 | Run **`/N/APPSDM/ABAC`** | Pathlock ABAC main screen |
| 2 | Click the **Functional Configuration** tab **(first tab)** | Left tree updates |
| 3 | Expand **Policy Information Point** in the left tree | Sub-items appear |
| 4 | **Double-click** on **Data Attribute Master** | List of data attributes |
| 5 | Find and open **`DATA.S_EMAIL`** | Attribute detail screen opens |
| 6 | Read the **Attribute ID** field at the top — **note it down** | — |

> **Convention:** All Data Attributes start with `DATA.`

**2b — Confirm the Technical Mapping**

| # | Action | What you see |
|---|---|---|
| 1 | Click the **Technical Configuration** tab **(second tab)** | Left tree updates |
| 2 | Expand **Data Attribute Config** in the left tree | Sub-items appear |
| 3 | Click **Technical Mapping** | Mapping entries for `DATA.S_EMAIL` |
| 4 | Find the entry for `DATA.S_EMAIL` — note the SAP Data Element shown | You should see **`S_EMAIL`** — the same element you found in Step 1 ✅ |

> **The "aha":** DAC bridges the gap between a business concept (`DATA.S_EMAIL`) and the SAP technical layer (`S_EMAIL`). You found both ends yourself.

> ⚠️ All other configuration in this level (Data Attribute Master, User Attribute Master, Policy Administration Point, Policy Enforcement Point) is done in the **first tab — Functional Configuration**.

---

## Step 3 — Explore the User Attribute

A **User Attribute** defines *who* the policy applies to. Again, this has been pre-created.

| # | Action | What you see |
|---|---|---|
| 1 | In **`/N/APPSDM/ABAC`**, click the **Functional Configuration** tab **(first tab)** | Left tree updates |
| 2 | Expand **Policy Information Point** in the left tree | Sub-items appear |
| 3 | **Double-click** on **User Attribute Master** | List of user attributes |
| 4 | Find and open **`USER.ID`** | Attribute detail screen |
| 5 | Read its description — this attribute holds the **logged-in user's SAP username** at runtime | — |

> **Convention:** All User Attributes start with `USER.`

---

## Step 4 — Create the Policy

A **Policy** is the container that holds the masking rules and links them to the data. You will create your own personal policy — because there are 20+ participants on this system, your policy name **must include your SAP username** to avoid collisions.

| # | Action | What you see |
|---|---|---|
| 1 | In **`/N/APPSDM/ABAC`**, click the **Functional Configuration** tab **(first tab)** | Left tree updates |
| 2 | **Double-click** on **Policy Administration Point** in the left tree | List of all existing policies opens |
| 3 | Click **New Entry** (top toolbar) | A blank policy form opens |
| 4 | Enter the **Policy Name**: `MASK_EMAIL_<YOURUSERNAME>` — e.g. `MASK_EMAIL_AMUELLER` | Field fills in |
| 5 | Enter the **Description**: `Mask passenger email for my user` | Field fills in |
| 6 | Click **Save** (💾 or Ctrl+S) | Policy appears in the list |

> ⚠️ If you get a "duplicate name" error, someone already used that name — double-check your username is in the policy name.

---

## Step 5 — Add a Rule Condition

A **Rule Condition** tells the policy *when* it should fire. Without one, the policy would apply to every user on the system — we want it to apply only to you.

| # | Action | What you see |
|---|---|---|
| 1 | In the left tree, expand **Policy Administration Point** | Your policy is listed |
| 2 | Expand your policy `MASK_EMAIL_<YOURUSERNAME>` | Sub-items appear, including **Rules** |
| 3 | **Double-click** on **Rules** | Rules list opens |
| 4 | Click **New Entry** | A blank rule row appears |
| 5 | Set **User Attribute** to `USER.ID` | Attribute selector fills |
| 6 | Set **Operator** to `EQ` (equals) | Operator set |
| 7 | Set **Value** to your SAP username — e.g. `AMUELLER` **(uppercase, exactly as you log in)** | Value filled |
| 8 | Click **Save** | Rule row saved |

> This condition reads: *"Only apply this policy when the currently logged-in user ID equals AMUELLER."*  
> Your colleagues' sessions will not be affected at all.

---

## Step 6 — Configure the Enforcement Point

The **Policy Enforcement Point** (PEP) is where you activate the masking action and connect your policy to the data attribute `DATA.S_EMAIL`. Without this, DAC knows the rule but does not act on anything.

| # | Action | What you see |
|---|---|---|
| 1 | In **`/N/APPSDM/ABAC`**, click the **Functional Configuration** tab **(first tab)** | Left tree updates |
| 2 | **Double-click** on **Policy Enforcement Point** in the left tree | Sub-items appear: **Data Masking** and **Data Blocking** |
| 3 | **Double-click** on **Data Masking** | List of all active masking enforcement points |
| 4 | Click **New Entry** | A blank row appears |
| 5 | In the **Policy** field, select or type `MASK_EMAIL_<YOURUSERNAME>` | Your policy linked |
| 6 | In the **Attribute** field, select or type `DATA.S_EMAIL` | Data attribute linked |
| 7 | Click **Save** | New enforcement point row saved ✅ |

> You have now told DAC: *"When my policy condition is met, mask the field defined by `DATA.S_EMAIL`."*

---

## Step 7 — Test: Verify the Masking Works

Pathlock DAC policies are evaluated when a session starts — **you must log out and back in** for your new policy to take effect.

| # | Action | Expected result |
|---|---|---|
| 1 | **Log out** of SAP (System → Log Off) | SAP login screen |
| 2 | **Log back in** with your username and password | SAP menu |
| 3 | Run `SE16` → table `SCUSTOM` → **Execute (F8)** | The `EMAIL` column now shows `***` for every passenger row ✅ |
| 4 | Ask a colleague sitting next to you to open `SE16` → `SCUSTOM` | Their `EMAIL` column still shows real addresses — your policy only affects your own session ✅ |

> **Still seeing real emails after re-login?**  
> → Check Step 5: the `USER.ID` value must be your exact SAP username, uppercase, no spaces.  
> → Make sure the Enforcement Point in Step 6 is saved.  
> → Log out and back in again after fixing.

---

## 🏁 Completion

You have created your first Pathlock DAC masking policy. Passenger emails are now masked at the data layer for your user — regardless of which transaction or screen they appear in.

**Claim your Level 1 points:**
Go to the **[leaderboard](http://152.53.187.143:9000)** → **Submit Code** → select **L1 — PII Masking** → enter the code.

> 💭 *What was the Attribute ID of the data attribute you masked?*

<details>
<summary>💬 <strong>Hint</strong> — click to reveal</summary>
<br>

The code is the **Attribute ID** of the data attribute you explored in Step 2a.

Ask yourself: *which field do we mask?*

</details>

---

## Troubleshooting

| Symptom | Solution |
|---|---|
| `/N/APPSDM/ABAC` gives "No authorization" | Raise your hand — your user may be missing the `/APPSDM/POL_CHANGE` role |
| Policy save fails with "duplicate name" | Your username is already in a policy name — check Step 4, make the name unique |
| `EMAIL` still visible after re-login | Check Step 5: the `USER.ID` value must be your exact SAP username (uppercase). Also confirm Step 6 Enforcement Point is saved. Log out and back in again. |
| Colleague's email is also masked | Your Step 5 rule condition is missing or has the wrong username — it should be your username only |
| Enforcement Point save fails | Check Step 6: Policy field must match your exact policy name, Attribute must be `DATA.S_EMAIL` |
| Can't find `DATA.S_EMAIL` in the list | Make sure you are in **Data Attribute Master** (Step 2), not User Attribute Master |

---

*Next: [Level 2 — Contextual Access →](level-02-contextual-access.md)*
