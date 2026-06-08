# DAC Workshop — Student Exercise Sheet
**Meridian AG — Audit Remediation**  
*Pathlock DAC / ABAC Hands-On Session*

---

## Your Situation

You are a member of the **Meridian AG IT Security team**.

Last week, an external audit concluded that your SAP system has **critical data access control deficiencies**. The auditors have given you **30 days to demonstrate technical mitigations** before escalating to the data protection authority.

You have just been handed the audit report. You have access to **Pathlock DAC** and a fully running SAP ABAP system.

Your task: work through each finding and implement a mitigation. No code changes. No SAP role changes. Just policy.

---

## Your Credentials

| What | Value |
|---|---|
| VPN Config | Provided by instructor |
| SAP GUI | `10.8.0.1:3200` |
| SAP Client | **assigned at registration** — see your confirmation page |
| Demo User A | `DEMO_USER_A` / see 1Password share |
| Demo User B (HR Manager) | `DEMO_USER_B` / see 1Password share |
| Finance Controller | `MSCHMIDT` / see 1Password share |
| Pathlock | `http://10.8.0.1` |
| Pathlock Admin | `DEMO_ADMIN` / see 1Password share |

---

## The Audit Report

> **CONFIDENTIAL — External Audit Finding Summary**  
> **Company:** Meridian AG  
> **Scope:** SAP ERP — HR, Finance, Basis  
> **Overall risk:** 🔴 Critical

---

### Finding F-01 🔴 Critical
**Unrestricted access to personal data**

> All users with transaction PA20 access can view full employee personal data: date of birth, national ID, bank account (IBAN) and salary — regardless of their job function or department. No field-level restrictions exist. This violates **GDPR Art. 5(1)(c)** (data minimisation).

**Your remediation target:**  
Only HR department staff may view PII fields. All other departments see masked values.

**Guidance level:** 🟢 Step-by-step instructions provided  
→ See Level 1 in your session guide

---

### Finding F-02 🟠 High
**Access is not context-aware**

> HR managers can access full employee personal data at any time — outside business hours, from personal devices, from unmanaged networks. There is no contextual enforcement of access. This creates elevated risk of data leakage outside controlled environments (**GDPR Art. 32**).

**Your remediation target:**  
Even HR managers must be restricted outside Mon–Fri 08:00–18:00 and outside the corporate VPN.

**Guidance level:** 🟡 Hints provided — some steps are yours to figure out  
→ See Level 2 in your session guide

---

### Finding F-03 🟠 High
**Real personal data in development environment**

> Real employee names, IBANs and addresses were found accessible to developer accounts. Developers need realistic data to test but must not be able to identify real individuals. This violates **GDPR Art. 25** (privacy by design).

**Your remediation target:**  
Developers see realistic but synthetic data — not real PII, not asterisks.

**Guidance level:** 🟡 Hints provided — you choose the technique  
→ See Level 3 in your session guide

---

### Finding F-04 🔴 Critical
**Overprivileged role with no compensating control**

> User `MSCHMIDT` (Finance Controller) holds role `Z_FI_CONTROLLER_ALL` — granting display access to all HR, payroll and financial data across all company codes and cost centres, including entities outside their scope of responsibility. A role cleanup would take 6 months. No compensating control exists. This is a **SOX Section 404** deficiency and **GDPR Art. 5(1)(c)** violation.

**Your remediation target:**  
Restrict `MSCHMIDT`'s effective data access to their own cost centre — without modifying the SAP role. Document it with an audit trail.

**Guidance level:** 🔴 No instructions — apply what you've learned  
→ You decide the approach. Be ready to explain your reasoning.

---

### Finding F-05 🟡 Medium → Escalating
**Data exfiltration risk + missing classification**

> Users can export sensitive data (salary reports, employee lists, customer master) to local files via SAP GUI download. Additionally, no data classification scheme exists — the system cannot distinguish between public and restricted data. These two gaps together mean sensitive data can leave the organisation silently, with no audit trail. **ISO 27001 A.8.12** (data leakage prevention) and **GDPR Art. 32**.

**Your remediation target:**  
1. Block downloads of sensitive data
2. Implement a data classification scheme and make your earlier policies classification-driven

**Guidance level:** 🔴 No instructions — this is your final exam  
→ You decide everything. Instructor available for questions only.

---

## Reflection Questions

Answer these at the end of the session. No wrong answers.

1. **Which finding was hardest to mitigate, and why?**

2. **In Finding F-04, you implemented a control without changing the SAP role. How would you explain this to an auditor in one sentence?**

3. **What's the difference between masking and scrambling? Give a real-world example of when you'd use each.**

4. **GDPR says data access must be "adequate, relevant and limited to what is necessary." How does ABAC enforce this technically?**

5. **If a new employee joins the Finance department tomorrow, do your policies automatically apply to them? Why or why not?**

6. **What would happen to your policies if Meridian AG added a new SAP transaction next year?**

---

## Compliance Cheat Sheet

*Use this to map your remediations to audit requirements.*

| Framework | Key requirement | What you configured |
|---|---|---|
| GDPR Art. 5(1)(c) | Data minimisation | |
| GDPR Art. 25 | Privacy by design | |
| GDPR Art. 32 | Technical security measures | |
| SOX Section 404 | IT General Controls — access evidence | |
| ISO 27001 A.5.15 | Access control | |
| ISO 27001 A.8.11 | Data masking | |
| ISO 27001 A.8.12 | Data leakage prevention | |
| NIS2 Art. 21 | Access control as mandatory measure | |

---

*Good luck. The DPA is watching.*
