# Level 4 — After-Hours Access: Block a TCode by Time

**Meridian AG Audit Remediation — Pathlock DAC/ABAC Workshop**

---

| | |
|---|---|
| 🎯 **Goal** | Create a policy that **blocks `SE16`** outside business hours using the `USER.CURRENT_TIME` attribute |
| ⏱ **Time** | 15 minutes |
| 🏆 **Points** | 100 |
| 💡 **Difficulty** | 🟡 Hints |

---

## Background

The DPA audit finding #3 reads:

> *"Booking agents and analysts can run sensitive transactions — including table browser SE16, payment reports and finance postings — at any hour of the day. No time-of-day restriction exists. Access to financial and PII data must be limited to authorised business hours. SOX Section 404 deficiency."*

In L1 and L2 you masked **fields**. This level introduces a completely different enforcement type: **blocking access to a dataset entirely** based on the time of day.

The policy fires whenever the current time falls **outside** your configured window. Depending on when the workshop runs, you may need to adjust the time range so the block fires during your session — see the hint in Step 3.

> ⚠️ Remember to **deactivate the policy** at the end of this level so you can continue using `SE16` in later levels.

---

## Step 1 — Explore the `USER.CURRENT_TIME` Attribute

`USER.CURRENT_TIME` is a pre-created User Attribute in Pathlock DAC. Unlike `USER.ID` (identity) or `USER.IP_ADDRESS` (network location), this one resolves to the **current server time** at the moment the policy is evaluated — every single time a transaction is called.

| # | Action | What you see |
|---|---|---|
| 1 | Run **`/N/APPSDM/ABAC`** in SAP | Pathlock ABAC main screen |
| 2 | Click the **Functional Configuration** tab (second tab) | Left tree updates |
| 3 | Expand **Policy Information Point** in the left tree | Sub-items appear |
| 4 | Double-click **User Attribute Master** | List of all user attributes |
| 5 | Find and open **`USER.CURRENT_TIME`** | Attribute detail screen — the attribute details including format (`HHMMSS` — system time from **System → Status**) are displayed directly |

> **Three ABAC condition types so far:**

| Level | Attribute | What it captures |
|---|---|---|
| L2 | `USER.ID` | Who you are |
| L3 | `USER.IP_ADDRESS` | Where you connect from |
| L4 | `USER.CURRENT_TIME` | When you connect |

---

## Step 2 — Create the Policy

| # | Action | What you see |
|---|---|---|
| 1 | In **`/N/APPSDM/ABAC`**, click the **Functional Configuration** tab **(second tab)** | Left tree updates |
| 2 | **Double-click** on **Policy Administration Point** in the left tree | List of all existing policies opens |
| 3 | Click the **Change Mode** button in the top toolbar (pencil icon) | Screen switches to edit mode |
| 4 | Click the **Create** button (📄 blank page icon at the top of the policy list) | Blank policy form opens |
| 5 | **Policy Name**: `BLOCK_SE16_HOURS_<YOURUSERNAME>` — e.g. `BLOCK_SE16_HOURS_AMUELLER` | Field fills in |
| 6 | **Description**: `Block SE16 outside business hours` | Field fills in |
| 7 | Leave **Process Area** and **Application Area** empty | — |
| 8 | Set the **Logging** dropdown to **`Do not log`** | Dropdown updates |
| 9 | *(Optional)* Add a note in the **Long Text** field | — |
| 10 | Click **Save** (💾 or Ctrl+S), then navigate back to the **Policy Administration Point** overview | Your policy appears in the list |

> ⚠️ If you get a "duplicate name" error, double-check your username is included in the policy name.

---

## Step 3 — Add the Time Condition

| # | Action | What you see |
|---|---|---|
| 1 | In the left tree, double-click **Policy Administration Point → Rules** | Selection dialog |
| 2 | Select your policy and confirm | Rules list |
| 3 | Click **Change Mode** (pencil icon) if not already in edit mode | Edit mode active |
| 4 | Click **Append Row** (📄 blank page icon) — enter **Condition ID `1`** | Blank condition row |
| 5 | **Attribute**: `DATA.APPLICATION` · **Operator**: `EQ` · **Value**: `SE16` | TCode scoped |
| 6 | Click **Append Row** again — enter **Condition ID `1`** again | Second condition row (AND) |
| 7 | **Attribute**: `USER.CURRENT_TIME` · **Operator**: `IN` · click **Define Ranges** and enter `080000` in the **From** field and `160000` in the **To** field → **Accept** | Time window set |
| 8 | Click **Append Row** again — enter **Condition ID `1`** again | Third condition row (AND) |
| 9 | **Attribute**: `USER.ID` · **Operator**: `EQ` · **Value**: your SAP username (e.g. `DEVELOPER`) | User scoped |
| 10 | Click **Save** | All three conditions saved |
| 11 | Select any condition row and click **Details** — confirm the logic reads: | |

```
IF DATA.APPLICATION EQ SE16
AND USER.CURRENT_TIME IN 080000-160000
AND USER.ID EQ <YOURUSERNAME>
```

> 💡 **AND vs OR — how Condition IDs work:**  
> All rows sharing the **same Condition ID** (e.g. `1`) are joined with **AND** — all must be true for the policy to fire.  
> If you add a row with **Condition ID `2`**, that creates a separate **OR** branch — the policy fires if branch 1 OR branch 2 is true.  
> Example: `1 / DATA.APPLICATION EQ SE16` + `2 / DATA.APPLICATION EQ SE17` would block both SE16 and SE17.

> **☕ Adjust the time window for your session:**  
> Check the exact server time: in SAP GUI go to **System menu → Status** — note the **User Time** field (format `HHMMSS`).  
> If you want to see the block fire *now*, set the value to a 5-minute window starting at the current time — e.g. if User Time shows `142300`, enter `142300-142800`. Save, complete Step 4, then run `SE16` after the window closes.

![SAP System → Status — server time](/screenshots/l04-step3-system-status.png)
*System → Status: note the User Time field (HHMMSS) to calibrate your time window.*

---

## Step 4 — Add the Block Action

The **Policy Enforcement Point** for a block action is under **Data Restriction**.

| # | Action | What you see |
|---|---|---|
| 1 | In **`/N/APPSDM/ABAC`**, click the **Functional Configuration** tab **(second tab)** | Left tree updates |
| 2 | **Double-click** on **Policy Enforcement Point** in the left tree | Sub-items appear: **Data Masking** and **Data Restriction** |
| 3 | **Double-click** on **Data Restriction** | List of all active restriction enforcement points |
| 4 | Enter change mode by clicking **Change** on the top left-hand side — if the **Append Row** button is already visible, you are already in edit mode | Edit mode active |
| 5 | Click the **Append Row** button (📄 blank page icon) | A blank row appears |
| 6 | Check the **Active** flag | Row is marked active |
| 7 | Set the **Action** dropdown to **`Deny`** | Action set |
| 8 | In the **Policy** field, select or type `BLOCK_SE16_HOURS_<YOURUSERNAME>` | Your policy linked |
| 9 | **Block Message**: read carefully — **the completion code is in this message** 🏆 | |
| 10 | Click **Save** | Enforcement point saved — policy is now live |

> ⚠️ The completion code is pre-filled in the Block Message by your instructor. Note it down now — you'll need it to submit to the leaderboard.

---

## Step 5 — Test: Trigger the Block

| # | Action | What you see |
|---|---|---|
| 1 | In SAP, type `/NSE16` in the command field and press Enter | **Access denied — Pathlock block screen** |
| 2 | Read the block message on screen | The message contains your completion code ✅ |
| 3 | Note down the code | |

![Pathlock TCode block screen on SE16](/screenshots/l04-step5-block-screen.png)
*Pathlock block screen: access to SE16 denied. The completion code is in the message body.*

This is exactly what a Meridian AG booking agent would see if they tried to access passenger data at midnight.

---

## Step 6 — Deactivate the Policy

You need `SE16` for the rest of the workshop — deactivate the policy before continuing.

| # | Action | What you see |
|---|---|---|
| 1 | Go back to **Policy Administration Point** | Policy list |
| 2 | Open your policy `BLOCK_SE16_HOURS_<YOURUSERNAME>` | Policy detail |
| 3 | Click **Change Mode** | Edit mode |
| 4 | Set **Active** flag to `inactive` (or delete the policy) | Policy deactivated |
| 5 | Save | |
| 6 | Run `SE16` again | Opens normally ✅ |

---

## Debrief

| Question | Answer |
|---|---|
| What changed in SAP? | **Nothing** — no authorisation object, no role change |
| What enforcement type was this? | **TCode Block** — completely different from field masking |
| Can you combine this with L1/L2? | Yes — stack conditions: `USER.CURRENT_TIME NOT IN 080000-180000 AND USER.IP_ADDRESS NOT EQ 10.8.0.X` |
| What other TCodes could you block? | `FB01`, `F110`, `SE37`, `SM59` — any sensitive transaction |
| Does this survive a role change? | Yes — the policy is independent of SAP authorisation objects |

---

## 🏆 Submit Your Code

Enter the completion code you found in the block message at **`https://pathlock.academy/submit`**

> **Compliance note:** SOX Section 404 — access control | PCI-DSS Req. 7 — restrict access by business need | ISO 27001 A.9.4 — system and application access control

*Next: [Level 5 — Audit Feed →](/levels/5)*
