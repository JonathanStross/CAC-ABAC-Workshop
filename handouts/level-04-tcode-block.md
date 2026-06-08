# Level 4 — After-Hours Access: Block a TCode by Time

**Meridian AG Audit Remediation — Pathlock DAC/ABAC Workshop**

---

| | |
|---|---|
| 🎯 **Goal** | Create a policy that **blocks `SE16`** outside business hours using the `USER.TIME` attribute |
| ⏱ **Time** | 15 minutes |
| 🏆 **Points** | 100 |
| 💡 **Difficulty** | 🟡 Hints |

---

## Background

The DPA audit finding #3 reads:

> *"Booking agents and analysts can run sensitive transactions — including table browser SE16, payment reports and finance postings — at any hour of the day. No time-of-day restriction exists. Access to financial and PII data must be limited to authorised business hours. SOX Section 404 deficiency."*

In L1 and L2 you masked **fields**. This level introduces a completely different enforcement type: **blocking a TCode entirely** based on the time of day.

The policy fires immediately — the workshop runs outside 08:00–18:00, so the moment you activate it you will be locked out of `SE16`. That is the point.

> ⚠️ Remember to **deactivate the policy** at the end of this level so you can continue using `SE16` in later levels.

---

## Step 1 — Explore the `USER.TIME` Attribute

`USER.TIME` is a pre-created User Attribute in Pathlock DAC. Unlike `USER.ID` (identity) or `USER.NETWORK` (network location), this one resolves to the **current server time** at the moment the policy is evaluated — every single time a transaction is called.

| # | Action | What you see |
|---|---|---|
| 1 | Run **`/N/APPSDM/ABAC`** in SAP | Pathlock ABAC main screen |
| 2 | Click the **Functional Configuration** tab (second tab) | Left tree updates |
| 3 | Expand **Policy Information Point** in the left tree | Sub-items appear |
| 4 | Double-click **User Attribute Master** | List of all user attributes |
| 5 | Find and open **`USER.TIME`** | Attribute detail screen |
| 6 | Read the **Description** and **Format** fields | Format: `HH:MM` — 24-hour server time |

> **Three ABAC condition types so far:**
> | Level | Attribute | What it captures |
> |---|---|---|
> | L1 | `USER.ID` | Who you are |
> | L2 | `USER.NETWORK` | Where you connect from |
> | L3 | `USER.TIME` | When you connect |

---

## Step 2 — Create the Policy

| # | Action | What you see |
|---|---|---|
| 1 | In **`/N/APPSDM/ABAC`**, click the **Functional Configuration** tab | Left tree updates |
| 2 | Double-click **Policy Administration Point** | List of all policies |
| 3 | Click **Change Mode** (pencil icon) | Edit mode |
| 4 | Click **New Entry** | Blank policy form |
| 5 | **Policy Name**: `BLOCK_SE16_HOURS_<YOURUSERNAME>` | Field fills in |
| 6 | **Description**: `Block SE16 outside business hours` | Field fills in |
| 7 | Click **Save** (💾 or Ctrl+S) | Policy saved |

---

## Step 3 — Add the Time Condition

| # | Action | What you see |
|---|---|---|
| 1 | In the left tree, double-click **Policy Administration Point → Rules** | Selection dialog |
| 2 | Select your policy and confirm | Rules list |
| 3 | Click **Change Mode** → **New** | Blank condition row |
| 4 | **Attribute**: `USER.TIME` | |
| 5 | **Operator**: `NOT IN` | |
| 6 | **Value**: `08:00-18:00` | Time range in 24h format |
| 7 | Save | Condition saved |

> **What this means:** the policy fires whenever the current time is **outside** 08:00–18:00. Since the workshop runs in the evening, this fires immediately.

---

## Step 4 — Add the TCode Block Action

This is where L3 differs from all previous levels — the action type is **Block**, not Masking.

| # | Action | What you see |
|---|---|---|
| 1 | In the left tree, double-click **Policy Administration Point → Actions** | Actions list |
| 2 | Click **Change Mode** → **New** | Blank action row |
| 3 | **Action Type**: `Block TCode` | Different from Masking |
| 4 | **TCode**: `SE16` | The table browser |
| 5 | **Block Message**: read carefully — **the completion code is in this message** 🏆 | |
| 6 | Save | Action saved — policy is now live |

> ⚠️ The completion code is pre-filled in the Block Message by your instructor. Note it down now — you'll need it to submit to the leaderboard.

---

## Step 5 — Test: Trigger the Block

| # | Action | What you see |
|---|---|---|
| 1 | In SAP, type `/NSE16` in the command field and press Enter | **Access denied — Pathlock block screen** |
| 2 | Read the block message on screen | The message contains your completion code ✅ |
| 3 | Note down the code | |

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
| Can you combine this with L1/L2? | Yes — stack conditions: `USER.TIME NOT IN 08:00-18:00 AND USER.NETWORK NOT EQ 10.8.0.X` |
| What other TCodes could you block? | `FB01`, `F110`, `SE37`, `SM59` — any sensitive transaction |
| Does this survive a role change? | Yes — the policy is independent of SAP authorisation objects |

---

## 🏆 Submit Your Code

Enter the completion code you found in the block message at **`https://pathlock.academy/submit`**

> **Compliance note:** SOX Section 404 — access control | PCI-DSS Req. 7 — restrict access by business need | ISO 27001 A.9.4 — system and application access control

*Next: [Level 5 — Audit Feed →](/levels/5)*
