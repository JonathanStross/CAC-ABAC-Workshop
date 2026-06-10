# Level 1 — Orientation: Connect & Log In

**Meridian AG Audit Remediation — DAC: Practitioner Level**

---

| | |
|---|---|
| 🎯 **Goal** | Connect to the workshop VPN and log into the SAP system |
| ⏱ **Time** | 10–15 minutes |
| 🏆 **Points** | 100 |
| 💡 **Difficulty** | 🟢 Fully guided |

---

## Prerequisites

**Step 0 — Register first**

Before this level you must have completed registration at **[https://pathlock.academy/register](https://pathlock.academy/register)**:

| # | What to do |
|---|---|
| 1 | Go to **https://pathlock.academy/register** and enter the access code your instructor gave you |
| 2 | Fill in your details and **accept the Participant Agreement** (the checkbox at the bottom) |
| 3 | On the confirmation page: **download your WireGuard `.conf` file** and your **credentials `.txt` file** — both links appear after successful registration |
| 4 | Save both files somewhere you can find them — you need them in Steps 1 and 3 below |

![Registration confirmation page — download links for .conf and credentials](/screenshots/l1_credentials_screen.png)
*Registration confirmation: download your WireGuard `.conf` and your credentials `.txt` from here. If you close this page the links are gone — ask your instructor to reset your password.*

> ⚠️ **If you skipped registration** — stop here, go to `https://pathlock.academy/register`, and complete it before continuing. You cannot connect to the SAP system without a WireGuard config and a valid SAP user.

---

Make sure you also have the following **installed** before you begin:

| | Requirement | Download |
|---|---|---|
| 💻 | A laptop (Windows, macOS, or Linux) | — |
| 📦 | **WireGuard** installed and running | [wireguard.com/install](https://www.wireguard.com/install/) |
| 🖥️ | **SAP GUI** installed | Ask your instructor or your IT team |
| 🌐 | **Google Chrome** or **Microsoft Edge** | [chrome](https://www.google.com/chrome/) / [edge](https://www.microsoft.com/edge) — needed for L8 Fiori |
| 📄 | Your **WireGuard `.conf` file** | Downloaded from your registration confirmation page *(Step 0 above)* |
| 🔑 | Your **SAP credentials `.txt`** | Downloaded from your registration confirmation page *(Step 0 above)* |

> ⚠️ **If you have not installed WireGuard or SAP GUI yet — do it now before continuing.**
> If you run into installation issues, ask your instructor or your IT team.

> 💡 **SAP GUI version:** Any version from SAP GUI 7.60 onwards works. If your company already has SAP GUI installed, use that.

**SAP system parameters** — you will need these in Step 2:

| Parameter | Value |
|---|---|
| Application Server | `10.8.0.1` |
| Instance Number | `00` |
| System ID (SID) | `A4H` |
| Client | **see your registration confirmation page** |
| Language | `EN` |

> ⚠️ Your SAP **client number** is personal — it was assigned to you when you registered and is shown on your registration confirmation page. It is **not** the same for everyone.

> 👥 **Shared client:** Depending on participant count, you may share a client with one or two other people. Please be considerate — keep time in change mode to a minimum (locks block others), and do not modify policies that are not your own.

---

## Step 1 — Connect to the VPN

You downloaded a `.conf` file during registration. Import it into WireGuard now.

**Windows**

| # | Action |
|---|---|
| 1 | Open **WireGuard** from the Start menu |
| 2 | Click **▼ Import tunnel(s) from file** (bottom-left arrow button) |
| 3 | Select your `.conf` file — e.g. `Anna_Mueller_customer.conf` |
| 4 | The tunnel appears in the list — click **Activate** |
| ✅ | Status changes to **Active** with a green indicator |

**macOS**

| # | Action |
|---|---|
| 1 | Open **WireGuard** from Applications or the menu bar |
| 2 | Click **Import tunnel(s) from file…** (bottom-left) |
| 3 | Select your `.conf` file |
| 4 | Click **Allow** if macOS asks for VPN permissions |
| ✅ | Toggle the tunnel **ON** — status shows **Active** |

**Linux**

```bash
sudo cp YourName_customer.conf /etc/wireguard/wg-workshop.conf
sudo wg-quick up wg-workshop
```

![WireGuard — importing and activating the tunnel](/screenshots/l1_wireguard_import_activate.png)
*Import your `.conf` file via the bottom-left button, then click Activate. The tunnel entry appears in the list.*

![WireGuard tunnel in Active state](/screenshots/l01-wireguard-active.png)
*Status shows Active (green). Confirm this before moving on.*

**Verify the connection**

Open a terminal or command prompt and run:

```
ping 10.8.0.1
```

WireGuard typically establishes the tunnel within **5–15 seconds** of activating. Once connected, ping replies come back in 1–2 ms. If there is no reply yet, wait up to 30 seconds — the first handshake can take a moment depending on your network. If it still does not respond after 30 seconds, toggle the tunnel off and on once.

---

## Step 2 — Add the SAP System in SAP Logon

> ⚠️ Your WireGuard tunnel must be **Active** before SAP can connect — the server is only reachable over the VPN.

| # | Action |
|---|---|
| 1 | Open **SAP Logon** (look for the gold SAP icon) |
| 2 | Click **New** → **Advanced** → select **Custom Application Server** |
| 3 | Fill in the connection details as shown below |
| 4 | Click **Save** (or **Finish**) |

**Connection details:**

| Field | Value |
|---|---|
| Description | `Meridian AG Workshop` |
| Application Server | `10.8.0.1` |
| Instance Number | `00` |
| System ID (SID) | `A4H` |
| Client | **see your registration confirmation page** |

![SAP Logon — Custom Application Server dialog](/screenshots/l01-saplogon-connection.png)
*SAP Logon: New Custom Application Server filled in with `10.8.0.1`, instance `00`, SID `A4H`.*

---

## Step 3 — Log In

| # | Action |
|---|---|
| 1 | Double-click **Meridian AG Workshop** in SAP Logon |
| 2 | The SAP logon screen opens — enter your credentials below |
| 3 | Press **Enter** or click the green ✅ button |
| 4 | SAP will immediately prompt you to **set a new password** — do this now and write it down |

**Credentials:**

| Field | Value |
|---|---|
| Client | **your assigned client** — from your registration page |
| User | Your SAP username (e.g. `AMUELLER`) — from your registration page |
| Password | Your temporary password — from your registration page |
| Language | `EN` |

> **Password rules:** Minimum 8 characters. Must include uppercase, lowercase, a digit, and a special character (e.g. `#`, `$`, `+`). Cannot start with `!` or `?`.

---

## Step 4 — Explore the Meridian AG System

You are now inside Meridian AG's live SAP environment. Take a few minutes to look around.

| # | Transaction / Action | What you see |
|---|---|---|
| 1 | Type `SE16N` in the command field (top-left) → **Enter** | General Table Display — your main tool throughout this workshop |
| 2 | Enter table `SCARR` → **Execute (F8)** | Carrier master data — Meridian AG's partner airlines (LH, AA, QF and others) |
| 3 | **F3** back → table `SCUSTOM` → **Execute** | Passenger records: names, addresses, phone numbers, emails, credit card references |
| 4 | **F3** back → table `SBOOK` → **Execute** | Booking records: flight class, prices, payment data, customer references |

👀 Notice anything about `SCUSTOM`? **Everything is visible. No restrictions. No masking.**

This is exactly what the external auditors flagged — and it is why you are here. Over the following levels, you will fix this.

![SE16 → SCUSTOM — unprotected passenger data](/screenshots/l01-scustom-unprotected.png)
*SCUSTOM result: passenger names, emails, addresses, credit card references — fully visible. This is the "before" state.*

---

## 🏁 Completion

You have connected to the VPN, logged into SAP, and seen the unprotected data first-hand.

**Claim your Level 1 points:**
Go to **[https://pathlock.academy/submit](https://pathlock.academy/submit)** → select **L1 — Orientation** → enter the code.

<details>
<summary>💬 <strong>Hint</strong> — click to reveal</summary>
<br>
You've already seen the answer. Log out of SAP and read everything on the login screen carefully.
</details>

---

## Troubleshooting

| Symptom | Solution |
|---|---|
| WireGuard — "Unable to start tunnel" | Disconnect any other active VPN first, then activate the workshop tunnel |
| Ping to `10.8.0.1` times out | Wait 30–60 seconds and retry — the first handshake can be slow |
| SAP GUI — "Cannot connect to server" | Confirm WireGuard shows **Active**; verify application server `10.8.0.1` and instance `00` |
| SAP — "Name or password is incorrect" | Passwords are case-sensitive. Check Caps Lock. |
| SAP — "User is locked" | Raise your hand — your instructor will unlock the account |
| Lost credentials or `.conf` file | Ask your instructor — credentials cannot be retrieved after registration and must be reset manually |
| macOS blocks WireGuard VPN permission | **System Settings → Privacy & Security → VPN** → allow WireGuard |

---

*Next: [Level 2 — Passenger PII Visible to All Staff →](/levels/2)*
