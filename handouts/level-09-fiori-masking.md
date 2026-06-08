# Level 9 — Fiori / OData: The UI Lied

**Meridian AG Audit Remediation — Pathlock DAC/ABAC Workshop**

---

| | |
|---|---|
| 🎯 **Goal** | Prove that UI-level masking is not data protection — then fix it at the OData response layer |
| ⏱ **Time** | 25 minutes |
| 🏆 **Points** | 175 |
| 💡 **Difficulty** | 🔴 Independent |

---

## Background

The DPA audit finding #8 reads:

> *"A junior consultant reviewed the Manage Sales Orders Fiori app and confirmed that sensitive fields appear masked in the UI. The finding was closed as remediated. The external auditor re-opened it immediately: browser DevTools shows the raw OData JSON response contains all unmasked values in plaintext. The UI mask is a CSS display trick — the data is fully exposed at the HTTP layer. GDPR Art. 32 — technical security measures must be effective at the data layer, not the display layer."*

A finding was closed without being fixed. Your job: prove it is still open, then close it properly.

> ⚠️ **This is a fully independent level.** No step-by-step instructions beyond this point. Use what you know from L1–L7.

---

## The Core Concept

```
RBAC / CSS mask:   Data travels to the browser → UI hides it visually
                   → DevTools sees the real value in the HTTP response ❌

Pathlock OData:    Data is masked server-side before leaving SAP
                   → DevTools sees *** in the HTTP response ✅
```

Every Fiori app communicates with SAP via **OData** — HTTP requests and JSON responses. If the mask only happens in the browser (CSS/JavaScript), the unmasked value is already in the response payload. Any user with DevTools — or any API client — can read it.

Pathlock DAC can intercept the OData response **on the server**, before the JSON leaves SAP. At that point the value never travels to the client at all.

---

## Part 1 — Prove the Finding Is Still Open

### Step 1 — Open the Fiori App

Navigate to the Fiori Launchpad via your browser:

```
https://10.8.0.1:50001/sap/bc/ui2/flp
```

Log in with your SAP credentials. Find and open the **Manage Sales Orders** app.

Observe: the `Net Amount` and `Gross Amount` fields display as `***` in the UI. A previous consultant marked this as "fixed".

---

### Step 2 — Open DevTools and Inspect the Network Traffic

| # | Action | What you see |
|---|---|---|
| 1 | Press **F12** (Chrome/Edge) or right-click → **Inspect** | DevTools panel opens |
| 2 | Click the **Network** tab | Network request list |
| 3 | Reload the page (**F5**) | Requests populate |
| 4 | In the filter box, type **`odata`** or **`sap/opu`** | OData requests filtered |
| 5 | Click on a request to `SEPMRA_C_SO_SalesOrder` | Request detail opens |
| 6 | Click the **Response** or **Preview** tab | JSON response body |

Look carefully at the JSON. You will see something like:

```json
{
  "d": {
    "results": [
      {
        "SalesOrderID": "500000001",
        "NetAmount": "14850.00",
        "GrossAmount": "17671.50",
        "CustomerID": "CUST-10001",
        ...
      }
    ]
  }
}
```

**The UI shows `***`. The JSON shows `14850.00`.** The data was never masked — it was only hidden visually. The finding is still open.

> 📸 Take a screenshot of this JSON response — you now have the evidence the auditor used to re-open the finding.

---

## Part 2 — Fix It at the Data Layer

Now configure Pathlock DAC to mask these fields **in the OData response** — server-side, before the JSON is sent.

### Step 3 — Configure OData Masking in Pathlock DAC

Navigate to the OData masking configuration in **`/N/APPSDM/ABAC`**.

> 💡 Hint: it is not in the same place as field masking. Look in the **Technical Configuration** tab — there is a dedicated section for OData / Fiori services.

Fields to mask for the `SEPMRA_C_SO_SalesOrder` service:
- `NetAmount`
- `GrossAmount`
- `CustomerID`

> **The completion code is pre-entered in the description of the OData masking policy entry.** You will see it when you open the correct configuration screen. 🏆

---

### Step 4 — Verify the Fix

| # | Action | Expected result |
|---|---|---|
| 1 | Reload the Fiori app | App loads normally |
| 2 | Open DevTools → Network → find the OData request | Request visible |
| 3 | Inspect the JSON response | `"NetAmount":"***"` ✅ |
| 4 | The UI also shows `***` | Still masked in UI ✅ |

Now both layers are consistent — and the protection is real. The auditor cannot re-open this finding.

---

## Debrief

| Question | Answer |
|---|---|
| Why did the original "fix" fail? | CSS/JS masking hides values in the browser — the data already arrived in the HTTP response |
| Who can bypass a CSS mask? | Anyone with DevTools, Postman, curl, or any API client |
| What does Pathlock OData masking do differently? | Intercepts the OData response server-side — the value never leaves SAP unmasked |
| Does this affect all API clients? | Yes — any tool calling the OData service gets the masked response |
| Is this the same masking engine as L1? | Same policy engine, different enforcement point — L1 masks in SE16, L8 masks in the OData layer |

---

## 🏆 Submit Your Code

Enter the completion code you found in the OData masking configuration at **`https://pathlock.academy/submit`**

> **Compliance note:** GDPR Art. 32 — technical security measures must operate at the data layer | PCI-DSS Req. 3 — protect cardholder data in transit | ISO 27001 A.8.11 — data masking
