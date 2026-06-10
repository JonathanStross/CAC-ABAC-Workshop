# Level 5 — The DAC Feed: Policy Events as Intelligence

**Meridian AG Audit Remediation — DAC: Practitioner Level**

---

| | |
|---|---|
| 🎯 **Goal** | Enable policy-level logging, generate feed events, and use an allow-policy as a passive sensor |
| ⏱ **Time** | 15 minutes |
| 🏆 **Points** | 150 |
| 💡 **Difficulty** | 🟡 Hints |

---

## Background

The DPA audit finding #4 reads:

> *"When asked to provide evidence of who accessed passenger email addresses and credit card references in the last 30 days, Meridian AG could not answer. No data access logging exists at the field level. The DPA expects a full access record: user, timestamp, transaction, field, and whether the value was masked or visible at time of access. GDPR Art. 30 — records of processing activities."*

You have been masking and blocking data since L2. But can you **prove** it?

The **DAC Feed** is Pathlock's real-time policy event log. Every time a policy condition is evaluated — whether it fires or not — Pathlock can record the full context of that evaluation:

| What it captures | Why it matters |
|---|---|
| **Who** accessed the data | User identity — GDPR Art. 30 |
| **When** they accessed it | Exact timestamp — forensic evidence |
| **From where** | Source IP / VPN address — access context |
| **What transaction** | TCode — operational context |
| **Which data attribute** | `DATA.S_EMAIL`, `DATA.LOCCURAM` etc. |
| **Which policy matched** | Or why no policy matched |
| **Masked or visible** | Whether the user saw real data or `***` |
| **Action taken** | Masked / Blocked / Allowed |

This is not just a log — it is **policy execution telemetry**.

---

## The Allow-Policy Pattern: Sensor Without Enforcement

Most policies in this workshop **act** on data — they mask or block. But you can also create a policy that does **nothing except log**.

Set the policy action to **Allow** (or **Log only**), enable logging, and you now have a passive sensor: every time the condition matches, a feed entry is written — with full context — but the user experience is unchanged. No masking, no block.

**Why this is powerful:**

> A booking agent at 03:00 from an unexpected IP runs `SE16 → SCUSTOM`. The policy condition `USER.TIME NOT IN 08:00-20:00` matches. The action is Allow — nothing is blocked. But the feed records: *user, IP, timestamp, transaction, attribute.* Your SIEM gets an alert. The SOC investigates. All without the attacker knowing they were detected.

This is the difference between a **fence** (blocking) and a **camera** (logging). You need both.

---

## Step 1 — Enable Logging on the Policy

You already have `MASK_EMAIL_<YOURUSERNAME>` from L2. Enable logging on it to start generating feed events.

| # | Action | What you see |
|---|---|---|
| 1 | Run **`/N/APPSDM/ABAC`** → **Functional Configuration** tab | Left tree updates |
| 2 | Double-click **Policy Administration Point** | All policies |
| 3 | Find and open **`MASK_EMAIL_<YOURUSERNAME>`** | Policy detail |
| 4 | Click **Change Mode** (pencil icon) | Edit mode |
| 5 | Change **Logging** from `Do not log` → **`Log all accesses`** | Dropdown updates |
| 6 | Save | Logging active on this policy |

> 💡 Logging is per-policy, not per-attribute. A single attribute can be governed by multiple policies with different logging settings — or no logging at all.

---

## Step 2 — Generate Access Events

Create log entries by accessing the data your policy governs:

| # | Action | What happens in the feed |
|---|---|---|
| 1 | Run `SE16` → table `SCUSTOM` → **Execute (F8)** | Policy evaluates → condition matches → `EMAIL` masked → feed entry written |
| 2 | Run `SE16` → `SCUSTOM` a second time from a different TCode path | Second entry — same user, same data, same result |
| 3 | Note the **server time** from **System → Status** | You will filter by this timestamp in Step 3 |

---

## Step 3 — Read the DAC Feed

| # | Action | What you see |
|---|---|---|
| 1 | In **`/N/APPSDM/ABAC`**, click the **Functional Configuration** tab | Left tree updates |
| 2 | Expand **Access Log** (or **DAC Feed**) in the left tree | Feed viewer opens |
| 3 | Filter by **User** = your SAP username | Your events only |
| 4 | Find your `SE16 → SCUSTOM` entries | Timestamped entries |
| 5 | Click into one entry and read all columns | Full context record |

![DAC Feed viewer — filtered to your user](/screenshots/l05-step3-feed-entries.png)
*DAC Feed: entries showing Timestamp, TCode=SE16, Attribute=DATA.S_EMAIL, Action=Masked, Source IP=10.8.0.x.*

**Every entry shows:**

| Column | Example value |
|---|---|
| User | `AMUELLER` |
| Timestamp | `2026-06-09 14:32:17` |
| Transaction | `SE16` |
| Data Attribute | `DATA.S_EMAIL` |
| Policy | `MASK_EMAIL_AMUELLER` |
| Action | `Masked` |
| Source IP | `10.8.0.x` (your VPN IP) |

---

## Step 4 — Build a Passive Sensor (Allow Policy)

Now create a second policy — identical condition, but **Allow** action with logging. This is your camera.

| # | Action | What you see |
|---|---|---|
| 1 | Go to **Policy Administration Point** → Create new policy | Blank form |
| 2 | **Policy Name**: `MONITOR_EMAIL_<YOURUSERNAME>` | |
| 3 | **Description**: `Log all access to EMAIL — no enforcement` | |
| 4 | Leave **Process Area** and **Application Area** empty | |
| 5 | Set **Logging** → **`Log all accesses`** | |
| 6 | Save | Policy created |
| 7 | Add a **Rule Condition**: `USER.ID EQ <YOURUSERNAME>` | Same as L2 condition |
| 8 | Add a **PEP entry** under **Data Masking**: action = **Allow**, attribute = `DATA.S_EMAIL` | Allow — no masking |
| 9 | Run `SE16 → SCUSTOM` again | Data appears **unmasked** (allow policy wins) — but feed entry still written |

> ⚠️ In a real deployment you would set this on a **different user or role** — not yourself. The point is: you can monitor access patterns without imposing any enforcement on the monitored user.

---

## Step 5 — Threat Hunting with the Feed

The feed becomes most valuable when you filter it like a security analyst:

| Question | Feed filter |
|---|---|
| Who accessed `DATA.S_EMAIL` outside business hours? | Attribute = `DATA.S_EMAIL`, Time range = `00:00-08:00` or `20:00-23:59` |
| Which users triggered the masking policy more than 10 times? | Policy = `MASK_EMAIL_*`, group by User |
| Was any access made from an unexpected IP range? | Source IP not in `10.8.0.0/24` |
| Did anyone bypass the masking? (Allow policy match) | Policy = `MONITOR_EMAIL_*`, Action = `Allowed` |

> **Plug-and-play threat detection:** The DAC Feed exports to CSV/Excel and streams to SIEM platforms (Splunk, Microsoft Sentinel, QRadar). Each feed entry is a structured event with consistent field names — no custom parser needed.

---

## Debrief

| Question | Answer |
|---|---|
| What changed in SAP to enable this? | **Nothing** — no auth object, no ABAP, no Basis change |
| Does it slow down SAP? | Minimal — logging is asynchronous |
| Can you log access to unmasked fields? | Yes — Allow policy with logging gives you visibility without interference |
| What is the allow-policy pattern? | Condition matches → action = Allow → user sees real data → feed records full context |
| How does this feed threat detection? | Every policy evaluation is a structured event — timestamp, user, IP, transaction, data, action — ready for SIEM ingestion |
| What does GDPR Art. 30 require? | Records of processing: who, what, when, purpose — the feed satisfies this at field level |

---

## 🏆 Completion Code

Look at one of your feed entries. **The completion code is the value shown in the `Action` column for your masked access events.**

Enter it at **`https://pathlock.academy/submit`** — exact case, no spaces.

---

> **Compliance note:** GDPR Art. 30 — records of processing | GDPR Art. 32 — evidence of technical measures | SOX Section 404 — ITGC audit evidence | ISO 27001 A.8.15 — logging and monitoring | NIS2 Art. 21 — security monitoring and incident detection

*Next: [Level 6 — Overprivileged Role →](/levels/6)*
