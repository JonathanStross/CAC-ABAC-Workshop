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
| 3 | Click **Change Mode** → **New** | Blank condition row |
| 4 | **Attribute**: `USER.CURRENT_TIME` | |
| 5 | **Operator**: `NOT IN` | |
| 6 | **Value**: a 5-minute window starting now — check **System → Status** for the server time (format `HHMMSS`), then enter e.g. `142300-142800` | Time range in HHMMSS format |
| 7 | Save | Condition saved |

> **☕ Good timing — you have ~5 minutes:**
>
> 1. Check the exact server time: in SAP GUI go to **System menu → Status** — note the **User Time** field (format `HHMMSS`, server clock).
> 2. Set the **Value** to a 5-minute window starting now — e.g. if User Time shows `142300`, enter `142300-142800`.
> 3. Save — the window is now counting down.
> 4. Use the remaining time to complete **Step 4** below (add the Data Restriction action).
> 5. Once Step 4 is done, run **`SE16`** — it still works (you are inside the window).
> 6. Step back out (F3), wait for the window to close, then run **`SE16`** again — blocked.

![SAP System → Status — server time](/screenshots/l04-step3-system-status.png)
*System → Status: note the System Time field (24h) to calibrate your 5-minute window.*

---

## Step 4 — Add the TCode Block Action

The **Policy Enforcement Point** for a TCode block is under **Data Restriction** — the same tree node as in L8. At least one Data Attribute must be linked to the policy, or the enforcement point cannot be saved.

| # | Action | What you see |
|---|---|---|
| 1 | In **`/N/APPSDM/ABAC`**, click the **Functional Configuration** tab **(second tab)** | Left tree updates |
| 2 | **Double-click** on **Policy Enforcement Point** in the left tree | Sub-items appear: **Data Masking** and **Data Restriction** |
| 3 | **Double-click** on **Data Restriction** | List of all active restriction enforcement points |
| 4 | Check whether edit mode is already active — look for the **Insert Row** (blank page icon) button. If not, click **Change Mode** (pencil icon) in the top toolbar. | Edit mode active |
| 5 | Click the **Insert Row** button (📄 blank page icon) | A blank row appears |
| 6 | Check the **Active** flag | Row is marked active |
| 7 | In the **Policy** field, select or type `BLOCK_SE16_HOURS_<YOURUSERNAME>` | Your policy linked |
| 8 | **Action Type**: `Block TCode` | Different from Masking |
| 9 | **TCode**: `SE16` | The table browser |
| 10 | **Data Attribute**: `DATA.TABLE_NAME` — required as an *exposed attribute* | Every Data Restriction enforcement point needs at least one data attribute assigned, even when the policy condition contains no data attribute. `DATA.TABLE_NAME` is the logical choice here: it identifies the table being browsed in SE16. |
| 11 | **Block Message**: read carefully — **the completion code is in this message** 🏆 | |
| 12 | Click **Save** | Enforcement point saved — policy is now live |

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
