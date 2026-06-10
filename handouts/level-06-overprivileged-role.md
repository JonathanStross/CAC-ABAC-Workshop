# Level 6 — Overprivileged Role: One Policy, Two Controls

**Meridian AG Audit Remediation — Pathlock DAC/ABAC Workshop**

---

| | |
|---|---|
| 🎯 **Goal** | Create a single policy that simultaneously **masks a PCI field** and **blocks a financial TCode** — scoped to a role |
| ⏱ **Time** | 15 minutes |
| 🏆 **Points** | 150 |
| 💡 **Difficulty** | 🔴 Independent |

---

## Background

The DPA audit finding #5 reads:

> *"The ZRANALYST role was cloned from an Accounts Receivable Clerk template 18 months ago and never cleaned up. It carries two privileges with no business justification:*
> - *`SBOOK.LOCCURAM` (credit card reference) is fully readable — PCI-DSS violation*
> - *TCode `FB01` (Post Financial Document) is accessible — SOX Segregation of Duties violation*
>
> *An analyst should only READ revenue data. Role remediation is 9 months away. A compensating control is required immediately."*

This is the first **independent** level — no step-by-step instructions. Use what you have learned in L1–L3 to figure it out.

---

## What You Need to Build

One policy. One condition. Two enforcement actions.

```
Condition:  USER.ROLE  EQ  ZRANALYST
Action 1:   Mask       DATA.LOCCURAM     (on SBOOK)
Action 2:   Block TCode  FB01
```

The condition fires once. Both controls activate simultaneously. That is the point.

---

## Hints

> Expand only if you are stuck.

<details>
<summary>💡 Hint 1 — Where is the completion code?</summary>

Same mechanic as L1, L2 and L3.

Go to: **`/N/APPSDM/ABAC`** → Functional Configuration → Policy Information Point → User Attribute Master → open **`USER.ROLE`** → read the **Description** field.

</details>

<details>
<summary>💡 Hint 2 — How do I find my role name?</summary>

In SAP, run **`SU01`** → enter your username → Execute → click the **Roles** tab.
Your assigned role name is listed there. It begins with `Z`.

</details>

<details>
<summary>💡 Hint 3 — How do I add two actions to one policy?</summary>

In **Policy Administration Point → Actions** for your policy:
- Click **New** → set Action Type = `Masking`, Data Attribute = `DATA.LOCCURAM`
- Click **New** again → set Action Type = `Block TCode`, TCode = `FB01`

Both rows sit under the same policy. The single condition drives both.

</details>

<details>
<summary>💡 Hint 4 — Where is DATA.LOCCURAM?</summary>

**Functional Configuration** → Policy Information Point → **Data Attribute Master** → find `DATA.LOCCURAM`.
It maps to the `LOCCURAM` field in table `SBOOK` — the local currency credit card reference.

</details>

---

## Verify Both Controls

### Test 1 — Credit card field masked

| # | Action | Expected result |
|---|---|---|
| 1 | Run `SE16` → table `SBOOK` → Execute (F8) | Booking records load |
| 2 | Find the `LOCCURAM` column | **`***`** — masked ✅ |

![SE16 → SBOOK — LOCCURAM masked](/screenshots/l06-test1-loccuram-masked.png)
*SBOOK: LOCCURAM (credit card reference) showing `***` — triggered by USER.ROLE EQ ZRANALYST.*

### Test 2 — Financial posting blocked

| # | Action | Expected result |
|---|---|---|
| 1 | Type `/NFB01` in the command field → Enter | **Pathlock block screen** ✅ |
| 2 | Read the block message | Confirms: access denied by policy |

![Pathlock block screen on FB01](/screenshots/l06-test2-fb01-blocked.png)
*FB01 blocked: "Access to transaction FB01 has been denied." One condition, two enforcements.*

Both controlled by one condition. The analyst's role triggered both enforcements at once.

---

## Debrief

| Question | Answer |
|---|---|
| How many SAP role changes were needed? | **Zero** — `ZRANALYST` still has `FB01` in its authorisation profile |
| How many Pathlock policies were needed? | **One** |
| What two compliance issues were resolved? | PCI-DSS (credit card field) + SOX SoD (financial posting) |
| What happens when role cleanup finishes in 9 months? | Delete the Pathlock policy — no residue, no technical debt |
| What if 15 users have this role? | The policy already covers all of them — `USER.ROLE EQ ZRANALYST` applies to every user holding that role |

**The key message:** ABAC is not a workaround. It is a compensating control with a defined lifespan — operational from day one, cleanly retired when the root cause is fixed.

---

## 🏆 Submit Your Code

Enter the completion code you found in the `USER.ROLE` attribute description at **`https://pathlock.academy/submit`**

> **Compliance note:** SOX Section 404 — SoD compensating controls | PCI-DSS Req. 3 — protect stored cardholder data | GDPR Art. 5(1)(c) — data minimisation

*Next: [Level 7 — Data Classification →](/levels/7)*
