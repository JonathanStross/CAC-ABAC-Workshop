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

Make sure you have the following **installed** before you begin:

| | Requirement | Download |
|---|---|---|
| 💻 | A laptop (Windows, macOS, or Linux) | — |
| 📦 | **WireGuard** installed and running | [wireguard.com/install](https://www.wireguard.com/install/) |
| 🖥️ | **SAP GUI** installed | Ask your instructor or your IT team |
| 🌐 | **Google Chrome** or **Microsoft Edge** | [chrome](https://www.google.com/chrome/) / [edge](https://www.microsoft.com/edge) — needed for L8 Fiori |
| 📄 | Your **WireGuard `.conf` file** | Downloaded from your registration confirmation page |
| 🔑 | Your **SAP credentials** | From your registration confirmation page (username + temporary password + client number) |

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

---

## 🏁 Completion

You have connected to the VPN, logged into SAP, and seen the unprotected data first-hand.

**Claim your Level 1 points:**
Go to the **[leaderboard](http://152.53.187.143:9000)** → **Submit Code** → select **L0 — Orientation** → enter the code.

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
