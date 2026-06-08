# Level 3 — Contextual Access: Same User, Different Rules

**Meridian AG Audit Remediation — Pathlock DAC/ABAC Workshop**

---

| | |
|---|---|
| 🎯 **Goal** | Create a masking policy that fires based on **network location** — same user, same role, different result |
| ⏱ **Time** | 15–20 minutes |
| 🏆 **Points** | 100 |
| 💡 **Difficulty** | 🟡 Hints |

---

## Background

The DPA audit finding #2 reads:

> *"The masking policy created for finding #1 is scoped to a specific user identity. It provides no protection when a different user accesses the same data, nor does it enforce any network-location requirement. An attacker with any valid SAP account can access full passenger PII from any network endpoint."*

In Level 2 you created a policy with condition `USER.ID EQ <your username>`.
That approach is brittle: one policy per user, no network enforcement.

**The goal of this level:** create a policy that protects data based on **where** the connection comes from — not just who — using the `USER.NETWORK` attribute.

---

## The Key Idea

Every participant in this workshop has a unique VPN IP address (e.g. `10.8.0.12`). The `USER.NETWORK` attribute in Pathlock DAC resolves to that IP at the moment a user logs in.

By setting the policy condition to:

```
USER.NETWORK NOT EQ <your_VPN_IP>
```

…the masking rule fires for **everyone whose IP is not yours**. From their perspective, the data is masked. From yours, it is visible. This is workstation-locked access control — with zero SAP changes.

---

## Step 1 — Find Your VPN IP

Your VPN IP is in the credentials you received at registration. You can also find it in the leaderboard:
- Go to the **leaderboard home page** (`https://pathlock.academy`)
- Your IP is shown in your registration confirmation, or check the WireGuard tunnel on your machine

> ⚠️ Write down your `10.8.0.X` address — you will need it in Step 4.

---

## Step 2 — Explore the `USER.NETWORK` Attribute

A **User Attribute** in Pathlock DAC defines a piece of context about the user at runtime. The `USER.NETWORK` attribute has been pre-created in the system — it resolves to the client's source IP address at the moment the SAP session starts.

> **The completion code for this level is hidden inside the description of `USER.NETWORK`. You will find it in this step.**

| # | Action | What you see |
|---|---|---|
| 1 | In SAP, run **`/N/APPSDM/ABAC`** | Pathlock ABAC main screen |
| 2 | Click the **Functional Configuration** tab (second tab) | Left tree updates |
| 3 | Expand **Policy Information Point** in the left tree | Sub-items appear |
| 4 | Double-click **User Attribute Master** | List of all user attributes |
| 5 | Find and open **`USER.NETWORK`** | Attribute detail screen opens |
| 6 | Read the **Description** field carefully | The completion code is here 🏆 |

> ⚠️ Note down the completion code now — submit it to the leaderboard at the end of this level.

---

## Step 3 — Create a Network-Based Masking Policy

Create a new masking policy — name it with your username to avoid collisions.

| # | Action | What you see |
|---|---|---|
| 1 | In **`/N/APPSDM/ABAC`**, click the **Functional Configuration** tab | Left tree updates |
| 2 | Double-click **Policy Administration Point** | List of all policies |
| 3 | Click **Change Mode** (pencil icon) | Edit mode |
| 4 | Click the **Create** button (📄 blank page icon at the top of the policy list) | Blank policy form |
| 5 | **Policy Name**: `MASK_NET_<YOURUSERNAME>` — e.g. `MASK_NET_AMUELLER` | Field fills in |
| 6 | **Description**: `Block EMAIL access from untrusted network endpoints` | Field fills in |
| 7 | Click **Save** (💾 or Ctrl+S) | Policy saved |

---

## Step 4 — Add the Network Condition

Now add a rule condition: mask EMAIL for anyone whose VPN IP is **not** yours.

| # | Action | What you see |
|---|---|---|
| 1 | In the left tree, double-click **Policy Administration Point → Rules** | Selection dialog for Rule ID |
| 2 | Select your policy `MASK_NET_<YOURUSERNAME>` and confirm | Rules list for your policy |
| 3 | Click **Change Mode** → **New** | Blank condition row |
| 4 | **Attribute**: `USER.NETWORK` | Attribute selector |
| 5 | **Operator**: `NOT EQ` (≠) | |
| 6 | **Value**: `10.8.0.X` — your VPN IP from Step 1 | Condition set |
| 7 | Save | |

> **What this means:** the policy fires (masking is applied) for all sessions where the VPN IP ≠ your IP. Your own session is exempt.

---

## Step 5 — Add the Data Action

Link the policy to the data it should mask: `SCUSTOM.EMAIL` via `DATA.S_EMAIL`.

| # | Action | What you see |
|---|---|---|
| 1 | In the left tree, double-click **Policy Administration Point → Actions** | Actions list for your policy |
| 2 | Click **Change Mode** → **New** | Blank action row |
| 3 | **Action Type**: `Masking` | |
| 4 | **Data Attribute**: `DATA.S_EMAIL` | |
| 5 | **Masking Pattern**: `***` (or choose a pattern from the dropdown) | |
| 6 | Save | Policy is now active |

---

## Step 6 — Test It

Use the **Find Your Lab Partner** widget at the bottom of this page to see who is on your server. Pick any colleague and share your **client number** with them. They log into SAP on your client from their machine — or you can share your credentials and use their machine, logging out immediately after.

**No partner available?** Enter your own IP as the exception in the condition — you will see the data unmasked since your IP matches. Then swap the condition to a different IP and re-test: you will now see the masking fire. That gives you both the positive and the negative test on your own.

### Test A — Your own session (should be VISIBLE)

| # | Action | Expected result |
|---|---|---|
| 1 | Run **`SE16`** → table `SCUSTOM` → **Execute (F8)** | Full table loads |
| 2 | Look at the `EMAIL` column | **Full email addresses visible** ✅ |

Your VPN IP matches the exception you configured — the policy does not fire for you.

### Test B — Your lab partner's session (should be MASKED)

Your partner logs into SAP on **your client number** using their own machine:

| # | Action | Expected result |
|---|---|---|
| 1 | Partner logs into SAP with their own credentials on **your client** | Normal login |
| 2 | Partner runs **`SE16`** → table `SCUSTOM` → **Execute (F8)** | Full table loads |
| 3 | Partner looks at the `EMAIL` column | **`***` — masked** ✅ |

Their VPN IP is different from yours → the condition `USER.NETWORK NOT EQ <your IP>` evaluates to TRUE → masking fires.

**This is contextual ABAC.** Same server. Same client. Same table. Same role. Different VPN IP. Different result. Zero SAP changes.

---

## Debrief

| Question | Answer |
|---|---|
| What changes in SAP were needed? | **None** — no role change, no authorisation object |
| What changes in Pathlock were needed? | One policy, one condition, one action |
| Does this scale to 2,000 users? | Yes — change the condition to `USER.NETWORK NOT IN 10.8.0.0/24` and it covers the entire VPN subnet |
| How does this compare to L1? | L1 = user-identity scope. L2 = network-location scope. Both are ABAC conditions — stack them together for defence in depth |

---

## 🏆 Submit Your Code

Enter the completion code you found in Step 3 at **`https://pathlock.academy/submit`**

> **Compliance note:** GDPR Art. 32 — technical security measures | NIS2 Art. 21 — access control | ISO 27001 A.8.11 — data masking

*Next: [Level 4 — After-Hours TCode Block →](/levels/4)*
