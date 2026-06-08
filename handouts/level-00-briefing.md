# Level 0 — The Briefing: Why We Are Here

**Meridian AG Audit Remediation — DAC: Practitioner Level**

---

| | |
|---|---|
| 🎯 **Goal** | Understand the Meridian AG scenario, the audit findings, and the access control model you will be using all day |
| ⏱ **Time** | 10 minutes |
| 🏆 **Points** | 50 |
| 💡 **Difficulty** | 🟢 Reading |

---

## The Scenario

**Meridian AG** is a mid-size European airline group operating 14 routes across central Europe. They process passenger bookings, payments, and HR data entirely within SAP.

Three weeks ago, the German **Data Protection Authority (DPA)** completed a surprise audit. The findings were serious enough to trigger a formal warning — one step below an enforcement notice. Meridian AG has been given **30 days** to implement compensating controls or face regulatory action.

You are part of the emergency remediation team. Today you will work through all nine findings and close each one using Pathlock DAC.

> The DPA's closing statement read:
> *"Meridian AG demonstrates a systemic failure of data access governance. Full visibility of passenger PII, payment references and financial data is granted to all authenticated users with no contextual restriction, no audit trail, and no export controls. Immediate remediation is required under GDPR Art. 32, SOX Section 404, and ISO 27001 A.8."*

---

## The Nine Findings

| # | Finding | Standard |
|---|---|---|
| **1** | All users can view full passenger email addresses — no masking applied | GDPR Art. 5(1)(f) |
| **2** | Masking is user-scoped only — no network-location enforcement | GDPR Art. 32 |
| **3** | Sensitive transactions accessible at any hour — no time restriction | SOX §404, PCI-DSS Req. 7 |
| **4** | No field-level access logging — cannot evidence who saw what | GDPR Art. 30 |
| **5** | ZRANALYST role carries FB01 and credit card field access without business justification | SOX SoD, PCI-DSS Req. 3 |
| **6** | No data classification — system cannot distinguish PII from public reference data | ISO 27001 A.8.3 |
| **7** | Sensitive tables can be exported to local files with no restriction | ISO 27001 A.8.12 |
| **8** | Fiori app masks fields visually only — raw values visible in OData response | GDPR Art. 32 |

Each level today corresponds to one finding. You fix it. You find the completion code. You submit it. The leaderboard updates live.

---

## The Problem with the Old Model

Meridian AG's SAP security was built the traditional way — **Role-Based Access Control (RBAC)**. A user gets a role. The role says yes or no to a transaction or table. That's it.

```
RBAC:  User → Role → Access?  YES / NO
```

RBAC works for basic gatekeeping. But it cannot answer any of these questions:

- *"This user should only see passenger data when connecting from the corporate network"*
- *"This transaction should be inaccessible outside business hours"*
- *"This field should be masked for analysts but visible to compliance officers"*
- *"No file export should be allowed for tables classified as PII"*

To handle these with RBAC you would need a separate role for every combination — and roles cannot evaluate live context like IP address, time of day, or data sensitivity at all.

---

## The Solution: ABAC

**Attribute-Based Access Control (ABAC)** evaluates a policy at the **moment of access** — dynamically, every time a user touches data.

```
ABAC:  User + Context + Data  →  Policy evaluated  →  Allow / Mask / Block
```

Instead of "what role does this user have?", it asks:
*"Given who this user is, where they connect from, what time it is, and what data they are requesting — what should happen?"*

Any security-relevant property becomes an **attribute**:

| Attribute type | Example | Used in level |
|---|---|---|
| **Identity** | Username, role, department | L2, L6 |
| **Network** | IP address, VPN subnet | L3 |
| **Temporal** | Time of day, day of week | L4 |
| **Data** | Table field, classification label | L2, L7, L8 |

A policy combines conditions with an **enforcement action**:

| Action | What it does | Used in |
|---|---|---|
| **Masking** | Replaces field value with `***` | L2, L3, L7 |
| **TCode Block** | Prevents a SAP transaction from opening | L4, L6 |
| **Download Block** | Prevents data export to file | L8 |

**Pathlock DAC** implements ABAC at the individual SAP field level. The same user can open `SE16`, see `SCUSTOM`, but have specific columns masked — based entirely on policy, with zero changes to SAP roles or authorisation objects.

> **Key message:** DAC does not replace SAP roles. It sits on top of them and adds a dynamic, context-aware enforcement layer. Role cleanup still matters — but you do not have to wait for it. You can fix findings today.

---

## What the Certificate Requires

Complete all 10 levels (L0–L9) to qualify for the **Pathlock DAC: Practitioner Certificate**.

Each completion code you submit is proof that you configured and verified the control yourself — not just read about it.

---

## 🏆 Completion Code

**The completion code for this level is the name of the access control model that solves the problems described above.**

It is a four-letter acronym. You have already read it on this page.

Submit it at **[Submit Code](/submit)**.

---

*Next: [Level 1 — Connect & Log In →](/levels/1)*
