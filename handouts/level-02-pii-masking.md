# Level 2 — Passenger PII: Create Your First Masking Rule

**Meridian AG Audit Remediation — DAC: Practitioner Level**

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

> 💡 **Reminder from L0:** DAC implements ABAC at the individual field level — same user, same role, different result based on policy. `USER.ID EQ <your username>` is the simplest possible condition.

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

![SE16 → SCUSTOM — passenger email addresses fully visible](/screenshots/l2_scustom_email.png)
*SCUSTOM: EMAIL column showing real passenger email addresses — unmasked, unrestricted. This is the audit finding.*

![F1 Technical Info — Data Element S_EMAIL](/screenshots/l02-step1-technical-info.png)
*F1 → Technical Info: Data Element field showing `S_EMAIL`.*

> ⚠️ Write down `S_EMAIL` — you will need it in the next step.

---

## Step 2 — Explore the Data Attribute

A **Data Attribute** in Pathlock DAC defines *what data* a policy acts on. It is linked to SAP via the Data Element you just found. This attribute has been pre-created in the system — go find it and then trace the mapping all the way down to the SAP field.

**2a — Open the attribute**

| # | Action | What you see |
|---|---|---|
| 1 | Run **`/N/APPSDM/ABAC`** | Pathlock ABAC main screen — three tabs at the top: **Home**, **Functional Configuration**, **Technical Configuration** |
| 2 | Click the **Functional Configuration** tab **(second tab)** | Left tree updates |
| 3 | Expand **Policy Information Point** in the left tree | Sub-items appear |
| 4 | **Double-click** on **Data Attribute Master** | List of data attributes |
| 5 | Find and open **`DATA.S_EMAIL`** | Attribute detail screen opens |
| 6 | Read the **Attribute ID** field at the top — **note it down** | — |

![Data Attribute Master — DATA.S_EMAIL](/screenshots/l2_data_attribute_master.png)
*Data Attribute Master: `DATA.S_EMAIL` open, showing the Attribute ID and description.*

> **Convention:** All Data Attributes start with `DATA.`

**2b — Confirm the Technical Mapping**

| # | Action | What you see |
|---|---|---|
| 1 | Click the **Technical Configuration** tab **(third tab)** | Left tree updates |
| 2 | Expand **Data Attribute Config** in the left tree | Sub-items appear |
| 3 | Click **Technical Mapping** | Mapping entries for `DATA.S_EMAIL` |
| 4 | Find the entry for `DATA.S_EMAIL` — note the SAP Data Element shown | You should see **`S_EMAIL`** — the same element you found in Step 1 ✅ |

![Technical Mapping — DATA.S_EMAIL to S_EMAIL](/screenshots/l2_technical_mapping.png)
*Technical Mapping: `DATA.S_EMAIL` mapped to SAP Data Element `S_EMAIL` — connecting the business attribute to the physical field.*

> **The "aha":** DAC bridges the gap between a business concept (`DATA.S_EMAIL`) and the SAP technical layer (`S_EMAIL`). You found both ends yourself.

> ⚠️ All other configuration in this level is done in the **Functional Configuration tab (second tab)**.

---

## Step 3 — Explore the User Attribute

A **User Attribute** defines *who* the policy applies to. Again, this has been pre-created.

| # | Action | What you see |
|---|---|---|
| 1 | In **`/N/APPSDM/ABAC`**, click the **Functional Configuration** tab **(second tab)** | Left tree updates |
| 2 | Expand **Policy Information Point** in the left tree | Sub-items appear |
| 3 | **Double-click** on **User Attribute Master** | List of user attributes |
| 4 | Find and open **`USER.ID`** | Attribute detail screen |
| 5 | Read its description — this attribute holds the **logged-in user's SAP username** at runtime | — |

![User Attribute Master — USER.ID](/screenshots/l2_user_attribute_master.png)
*User Attribute Master: `USER.ID` — resolves to the logged-in SAP username at policy evaluation time.*

> **Convention:** All User Attributes start with `USER.`

---

## Step 4 — Create the Policy

A **Policy** is the container that holds the masking rules and links them to the data. You will create your own personal policy — because there are 20+ participants on this system, your policy name **must include your SAP username** to avoid collisions.

| # | Action | What you see |
|---|---|---|
| 1 | In **`/N/APPSDM/ABAC`**, click the **Functional Configuration** tab **(second tab)** | Left tree updates |
| 2 | **Double-click** on **Policy Administration Point** in the left tree | List of all existing policies opens |
| 3 | Enter change mode by clicking **Change** on the top left hand side | Screen switches to edit mode |
| 4 | Click the **Create** button (📄 blank page icon at the top of the policy list) | A blank policy form opens |
| 5 | Enter the **Policy Name**: `MASK_EMAIL_<YOURUSERNAME>` — e.g. `MASK_EMAIL_AMUELLER` | Field fills in |
| 6 | Enter the **Description**: `Mask passenger email for my user` | Field fills in |
| 7 | Leave **Process Area** and **Application Area** empty | — |
| 8 | Set the **Logging** dropdown to **`Do not log`** | Dropdown updates |
| 9 | *(Optional)* In the **Long Text** field, write something about the workshop — feedback is always welcome 😄 | — |
| 10 | Click **Save** (💾 or Ctrl+S), then navigate back to the **Policy Administration Point** overview | Your policy appears in the list |

> ⚠️ If you get a "duplicate name" error, someone already used that name — double-check your username is in the policy name.

---

## Step 5 — Add a Rule Condition

A **Rule Condition** tells the policy *when* it should fire. Without one, the policy would apply to every user on the system — we want it to apply only to you.

| # | Action | What you see |
|---|---|---|
| 1 | In the left tree, **double-click** on **Policy Administration Point** → **Rules** | A selection dialog asks for a Rule ID |
| 2 | Select or enter your policy `MASK_EMAIL_<YOURUSERNAME>` and confirm | The rules list for your policy opens |
| 3 | Check whether you are already in edit mode — look for the toolbar buttons: **Check entries** (scale icon), **Append Row** (blank page icon), **+** and **−** above the condition columns. If those buttons are visible, you are already in edit mode. If not, click **Change Mode** (pencil icon) in the top toolbar. | Edit mode active |
| 4 | Click the **Append Row** button (📄 blank page icon) to create a new condition | A blank condition row appears |
| 5 | In the **Condition ID** field: type `1` directly, or press **F4** to open value help and select `1` | Condition ID set to `1` |
| 6 | In the **Attribute ID** field: press **F4** to open value help, search for and select **`USER.ID`** | Attribute set |
| 7 | The **Operator** defaults to `EQ` (equals) — leave it as-is | Operator set |
| 8 | For the **Value**, you have two options: | |
| | **Option A — Direct input:** type your SAP username directly into the value field (e.g. `AMUELLER`) | |
| | **Option B — Ranges:** click **Define Ranges**, then in the **Single Values** section enter your username in the **`BNAME`** field (must be **uppercase**), click **Accept** | Value filled |
| 9 | Click the **Check entries** button (⚖️ scale icon) to validate — no errors should appear | Validation passed |
| 10 | Click **Save** | Condition row saved |
| 11 | To review what you built: select the condition row and click **Details** (above the list) | DAC shows the policy rule in plain text — it should read exactly: |

```
Policy: MASK_EMAIL_<YOURUSERNAME>
Policy Name: Mask passenger email for my user

*******************************************************************

Rule:

IF USER.ID EQ <YOURUSERNAME>
```

![Creating a rule condition — USER.ID EQ your username](/videos/l2_create_rule.mp4)
*Walkthrough: opening the Rules dialog, appending a row, setting USER.ID EQ and saving the condition.*

> This condition reads: *"Only apply this policy when the currently logged-in user ID equals AMUELLER."*  
> Your colleagues' sessions will not be affected at all.

---

## Step 6 — Configure the Enforcement Point

The **Policy Enforcement Point** (PEP) is where you activate the masking action and connect your policy to the data attribute `DATA.S_EMAIL`. Without this, DAC knows the rule but does not act on anything.

| # | Action | What you see |
|---|---|---|
| 1 | In **`/N/APPSDM/ABAC`**, click the **Functional Configuration** tab **(second tab)** | Left tree updates |
| 2 | **Double-click** on **Policy Enforcement Point** in the left tree | Sub-items appear: **Data Masking** and **Data Restriction** |
| 3 | **Double-click** on **Data Masking** | List of all active masking enforcement points |
| 4 | Check whether edit mode is already active — the same buttons from Step 5 should be visible: **Check entries** (scale icon), **Append Row** (blank page icon), **+** and **−**. If not, click **Change Mode** (pencil icon) in the top toolbar. | Edit mode active |
| 5 | Click the **Insert Row** button (📄 blank page icon) | A blank row appears at the bottom |
| 6 | Check the **Active** flag | Row is marked active |
| 7 | Set the **Action** dropdown to **Deny** | Action set |
| 8 | In the **Policy** field, select or type `MASK_EMAIL_<YOURUSERNAME>` | Your policy linked |
| 9 | In the **Attribute** field, select or type `DATA.S_EMAIL` | Data attribute linked |
| 10 | Click **Save** | New enforcement point row saved ✅ |
| 11 | Click the **selection box** at the very start of your row to highlight the entire line, then click **Details** (above the list) | Full policy summary is displayed |

**Your Details screen should show:**

```
Policy: MASK_EMAIL_<YOURUSERNAME>
Description: Mask passenger email for my user
Policy Status: Active
Policy Enforcement Type: Data Masking

*******************************************************************

Rule:

IF USER.ID EQ <YOURUSERNAME>


THEN DENY ACCESS TO ATTRIBUTES:

DATA.S_EMAIL
```

> You have now told DAC: *"When my policy condition is met, mask the field defined by `DATA.S_EMAIL`."*

![Configuring the Policy Enforcement Point — Data Masking](/videos/l2_enforcement_point.mp4)
*Walkthrough: opening Data Masking, inserting a row, linking policy + attribute, saving and verifying the Details output.*

---

## Step 7 — Test: Verify the Masking Works

Pathlock DAC policies take effect immediately — in most cases you will see the masking without logging out. If the result is not yet visible, a logout and re-login will force the session to pick up the new policy.

| # | Action | Expected result |
|---|---|---|
| 1 | Run `SE16` → table `SCUSTOM` → **Execute (F8)** | The `EMAIL` column now shows `***` for every passenger row ✅ |
| 2 | If emails are still visible — **log out** (System → Log Off) and **log back in**, then repeat step 1 | Masking now active ✅ |
| 3 | Ask a colleague sitting next to you to open `SE16` → `SCUSTOM` | Their `EMAIL` column still shows real addresses — your policy only affects your own session ✅ |

![SE16 → SCUSTOM after masking](/screenshots/l02-step7-email-masked.png)
*SCUSTOM: EMAIL column showing `***` for all rows. Compare with the before screenshot above.*

> **Still seeing real emails after re-login?**  
> → Check Step 5: the `USER.ID` value must be your exact SAP username, uppercase, no spaces.  
> → Make sure the Enforcement Point in Step 6 is saved.  
> → Log out and back in again after fixing.

> **Policy Enforcement Point not showing Data Masking or Data Restriction?**  
> The enforcement types need to be activated first. In **`/N/APPSDM/ABAC`** → **Functional Configuration** tab → expand the top node → click **Activate Functionality**. Check the boxes for **Data Masking** and **Data Restriction**, then save. The sub-items will appear under Policy Enforcement Point.

> **Masking not firing even though the policy is configured correctly?**  
> This can happen after a system restart if the SAP profile parameter `dynp/usr_masking` is not set to `ALL`. This is a system-level setting — **raise your hand and ask your instructor** to check it. You cannot fix this yourself.

---

## 🏁 Completion

You have created your first Pathlock DAC masking policy. Passenger emails are now masked at the data layer for your user — regardless of which transaction or screen they appear in.

**Claim your Level 2 points:**
Go to **[https://pathlock.academy/submit](https://pathlock.academy/submit)** → select **L2 — PII Masking** → enter the code.

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
| PEP tree shows no **Data Masking** or **Data Restriction** items | Go to **Functional Configuration** → expand the top node → **Activate Functionality** → check **Data Masking** and **Data Restriction** → Save |
| Masking policy is correct but nothing is masked | Profile parameter `dynp/usr_masking` may not be set to `ALL` after a system restart — raise your hand, instructor must fix this |

---

*Next: [Level 3 — Contextual Access →](/levels/3)*
