# Level 0 — The Briefing: Why We Are Here

**Meridian AG Audit Remediation — DAC: Practitioner Level**

---

| | |
|---|---|
| 🎯 **Goal** | Understand the Meridian AG scenario, the nine audit findings, and the access control model you will fix them with |
| ⏱ **Time** | 10 minutes |
| 🏆 **Points** | 50 |
| 💡 **Difficulty** | 🟢 Reading |

---

## The Scenario

**Meridian AG** is a European travel services and booking platform. They act as a distribution intermediary — processing reservations, passenger PII, and payment data on behalf of 12 partner carriers. Booking records, customer data, and financial settlements for carriers including Lufthansa, American Airlines, and Qantas flow through Meridian AG's central SAP instance. Meridian AG never flies a single aircraft; they are the system of record for everyone else's passengers.

Three weeks ago, the German **Data Protection Authority (DPA)** completed a surprise audit. The findings were serious enough to trigger a formal warning — one step below an enforcement notice. Meridian AG has been given **30 days** to implement compensating controls or face regulatory action.

You are part of the emergency remediation team. Today you will work through all eight findings and close each one using Pathlock DAC.

> The DPA's closing statement read:
> *"Meridian AG demonstrates a systemic failure of data access governance. Full visibility of passenger PII, payment references and financial data is granted to all authenticated users with no contextual restriction, no audit trail, and no export controls. Immediate remediation is required under GDPR Art. 32, SOX Section 404, and ISO 27001 A.8."*

---

## The Eight Findings

| # | Finding | Standard | Fixed in |
|---|---|---|---|
| **1** | All users can view full passenger email addresses — no masking applied | GDPR Art. 5(1)(f) | L2 |
| **2** | Masking is user-scoped only — no network-location enforcement | GDPR Art. 32 | L3 |
| **3** | Sensitive transactions accessible at any hour — no time restriction | SOX §404, PCI-DSS Req. 7 | L4 |
| **4** | No field-level access logging — cannot evidence who saw what | GDPR Art. 30 | L5 |
| **5** | ZRANALYST role carries FB01 and credit card field access without business justification | SOX SoD, PCI-DSS Req. 3 | L6 |
| **6** | All users see passenger data across all business units — no regional data separation | GDPR Art. 5(1)(b) | L7 |
| **7** | No data classification — system cannot distinguish PII from public reference data | ISO 27001 A.8.3 | L8 |
| **8** | Sensitive tables can be exported to local files with no restriction | ISO 27001 A.8.12 | L8 |

Each level today corresponds to one or more findings. You fix it. You find the completion code. You submit it. The leaderboard updates live.

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
- *"German business unit data should only be accessible to users assigned to that unit"*
- *"No file export should be allowed for tables classified as PII"*

To handle these with RBAC you would need a separate role for every combination — and roles cannot evaluate live context like IP address, time of day, or data classification at all.

---

## The Solution: ABAC

**Attribute-Based Access Control (ABAC)** evaluates a policy at the **moment of access** — dynamically, every time a user touches data.

```
ABAC:  User + Context + Data  →  Policy evaluated  →  Allow / Mask / Block / Filter
```

Instead of "what role does this user have?", it asks:
*"Given who this user is, where they connect from, what time it is, and what data they are requesting — what should happen?"*

Any security-relevant property becomes an **attribute**:

| Attribute type | Example | Used in level |
|---|---|---|
| **Identity** | Username | L2 |
| **Role** | SAP role name | L6, L7 |
| **Network** | VPN IP address | L3 |
| **Temporal** | Time of day | L4 |
| **Data** | Table field, classification label, ok-code | L2, L8 |

A policy combines conditions with an **enforcement action**:

| Action | What it does | Used in |
|---|---|---|
| **Masking** | Replaces field value with `***` | L2, L3 |
| **Row Filter** | Removes entire rows from result sets | L7 |
| **TCode Block** | Prevents a SAP transaction from opening | L4, L6 |
| **Download Block** | Prevents data export to file | L8 |
| **Allow + Log** | Passes access through but records full context | L5 |

**Pathlock DAC** implements ABAC at the individual SAP field and row level. The same user can open `SE16`, see `SCUSTOM`, but have specific columns masked or specific rows removed — based entirely on policy, with zero changes to SAP roles or authorisation objects.

> **Key message:** DAC does not replace SAP roles. It sits on top of them and adds a dynamic, context-aware enforcement layer. Role cleanup still matters — but you do not have to wait for it. You can fix findings today.

---

## 🏆 Completion Code

**The completion code for this level is the name of the access control model that solves all eight findings above.**

It is a four-letter acronym. You have already read it on this page.

Submit it at **[Submit Code](/submit)**.

---

*Next: [Level 1 — Connect & Log In →](/levels/1)*
