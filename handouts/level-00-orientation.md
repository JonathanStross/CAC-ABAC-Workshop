# Level 0 — Orientation: Connect & Log In
**Meridian AG Audit Remediation — Pathlock DAC/ABAC Workshop**

> 🎯 **Goal:** Connect to the workshop VPN and log into the SAP system.  
> ⏱ **Estimated time:** 10–15 minutes  
> 🏆 **Points:** 100  
> 💡 **Difficulty:** 🟢 Fully guided

---

## What you need before starting

| | Required |
|---|---|
| 💻 | A **laptop** (Windows, macOS, or Linux) |
| 📦 | **WireGuard** installed — [wireguard.com/install](https://www.wireguard.com/install/) |
| 🖥️ | **SAP GUI** installed — [SAP Support downloads](https://support.sap.com/en/product/connectors/sapgui.html) |
| 📄 | Your **WireGuard .conf file** — downloaded from the registration page |

---

## Step 1 — Connect to the Workshop VPN (WireGuard)

You registered on the leaderboard and downloaded a `.conf` file. Now import it into WireGuard.

### Windows

1. Open **WireGuard** from the Start menu
2. Click **▼ Import tunnel(s) from file** (the small arrow button, bottom-left)
3. Select your `.conf` file (e.g. `Anna_Mueller_customer.conf`)
4. The tunnel appears in the list — click **Activate**
5. The status changes to **Active** with a green indicator ✅

### macOS

1. Open **WireGuard** from Applications or the menu bar icon
2. Click **Import tunnel(s) from file…** (bottom-left)
3. Select your `.conf` file
4. Click **Allow** if macOS asks for VPN permissions
5. Toggle the tunnel **ON** — status shows **Active** ✅

### Linux (CLI)

```bash
sudo cp YourName_customer.conf /etc/wireguard/wg-workshop.conf
sudo wg-quick up wg-workshop
```

---

### ✅ Verify VPN is working

Open a terminal / command prompt and run:

```
ping 10.8.0.1
```

You should see replies within a second or two. If you do — the VPN is up. 🎉

> ⏱ **Note:** The first connection may take up to a minute before the SAP system responds — this is normal. Give it a moment before moving to Step 2.

---

## Step 2 — Create your SAP GUI connection

1. Open **SAP Logon** (the SAP GUI launcher — look for the gold SAP icon)
2. Click **New** → **Advanced** → choose connection type **Custom Application Server**
3. Fill in the fields exactly as shown:

| Field | Value |
|---|---|
| **Description** | `Meridian AG Workshop` |
| **Application Server** | `10.8.0.1` |
| **Instance Number** | `00` |
| **System ID (SID)** | `A4H` |
| **Client** | `001` |

4. Click **Save** (or **Finish**)

> ⚠️ Make sure your WireGuard tunnel is **Active** before trying to connect — the SAP server is only reachable over the VPN.

---

## Step 3 — Log into SAP

1. Double-click **Meridian AG Workshop** in the SAP Logon list
2. The SAP logon screen opens
3. Enter your credentials:

| Field | Value |
|---|---|
| **Client** | `001` |
| **User** | Your SAP username (e.g. `AMUELLER`) — from your registration page |
| **Password** | Your temporary password — from your registration page |
| **Language** | `EN` |

4. Press **Enter** or click the green ✅ button
5. SAP will prompt you to **set a new password** — do this now and note it down.

> 🔑 **Password rules:** Minimum 8 characters. Must include uppercase, lowercase, a digit, and a special character (e.g. `#`, `$`, `+`). Cannot start with `!` or `?`.

---

## Step 4 — Explore Meridian AG

Once logged in, take a quick look around. You are inside Meridian AG's live SAP system.

1. In the **command field** (top-left input box), type `SE16N` and press **Enter**
   - This opens the **General Table Display** — your main tool throughout this workshop
2. In the **Table** field, type `SCARR` and press **Execute** (F8 or the clock icon)
   - You see the airline carriers — this is Meridian AG's flight network
3. Go back (F3), change table to `SCUSTOM` → Execute
   - You see **passenger records**: names, addresses, phone numbers, emails, credit card references
   - 👀 Notice anything? **Everything is visible. No restrictions. No masking.**
   - This is exactly what the external auditors found — and why you're here.
4. Go back, try table `SBOOK`
   - Booking records — flight class, prices, payment data, customer references

This is the data you will be protecting across the following levels.

---

## 🏁 Completion

You've connected to the VPN, logged into SAP, and seen the unprotected data first-hand.

**Now claim your Level 0 points.**

> 💬 **Hint:** You've already seen the answer. Log out of SAP and read everything on the login screen carefully.

Go to **[the leaderboard](http://152.53.187.143:9000)** → click **Submit Code** → select **L0 — Orientation** → enter the code.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| WireGuard says "Unable to start tunnel" | Check that no other VPN is active — disconnect it first, then activate the workshop tunnel |
| Ping to `10.8.0.1` times out | Wait 30–60 seconds and try again. The tunnel handshake can take a moment. |
| SAP GUI says "Cannot connect to server" | Confirm WireGuard shows **Active**. Double-check application server is `10.8.0.1` and instance is `00` |
| SAP says "Name or password is incorrect" | Passwords are case-sensitive. Check Caps Lock. Username must be uppercase (e.g. `AMUELLER`) |
| SAP says "User is locked" | Raise your hand — your instructor will unlock the account |
| "I lost my credentials / .conf file" | Go to `http://152.53.187.143:9000` — ask your instructor to reset your account |
| macOS blocks WireGuard VPN permission | Go to **System Settings → Privacy & Security → VPN** and allow it |

---

*Next up: [Level 1 — Passenger PII Visible to All Staff →](level-01-pii-masking.md)*
