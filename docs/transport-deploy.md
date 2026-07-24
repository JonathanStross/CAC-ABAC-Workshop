# Transport Deploy Guide — DAC Workshop

> **Infrastructure note (July 2026):** sap3, sap4, sap5 have been decommissioned.
> All workshop sessions now run on **sap2 only** (`159.195.81.132`).

## Status

| Transport | Type | Status on SAP2 | K/R files |
|---|---|---|---|
| `A4HK900136` | Workbench | Created, **not yet released** | ❌ Not generated |
| `A4HK900139` | Customizing (client 001) | Created, **not yet released** | ❌ Not generated |

**Contents:** DAC Data Attributes — `DATA.APPLICATION`, `DATA.BUTTON_OK_CODE`, `DATA.TABLE_NAME`

---

## Step 1 — Release on SAP2 (SAP GUI required)

1. Log into SAP2, run **`SE10`**
2. Find `A4HK900136` and `A4HK900139`
3. Release all **sub-tasks** first (select each, click Release)
4. Release the **parent transport request**
5. Confirm the following files now exist on SAP2:
   - `/usr/sap/trans/cofiles/K900136.A4H`
   - `/usr/sap/trans/data/R900136.A4H`
   - `/usr/sap/trans/cofiles/K900139.A4H`
   - `/usr/sap/trans/data/R900139.A4H`

---

## Step 2 — Import on SAP2

Since SAP2 is both the source and the only target, import directly:

```bash
ssh -i ~/.ssh/netcup_sap2 root@159.195.81.132 \
  "docker exec abaptrial su - a4hadm -c \
   'tp import A4HK900136 A4H client=001 pf=/usr/sap/trans/bin/TP_DOMAIN_A4H.PFL 2>&1' && \
   docker exec abaptrial su - a4hadm -c \
   'tp import A4HK900139 A4H client=001 pf=/usr/sap/trans/bin/TP_DOMAIN_A4H.PFL 2>&1'"
```

---

## Step 3 — Verify

Log into SAP2 and go to:
`/N/APPSDM/ABAC` → **Functional Configuration** → **Policy Information Point** → **Data Attribute Master**

Confirm presence of:
- `DATA.APPLICATION`
- `DATA.BUTTON_OK_CODE`
- `DATA.TABLE_NAME`

---

## Instructor Pre-Configuration Checklist

Run on **sap2** after transport import:

### 1. Role `Z_GERMAN` (empty shell)
- `PFCG` → Create role `Z_GERMAN`
- No menu, no auth objects — pure name carrier for DAC
- Do **not** generate a profile

### 2. Policy `RESTRICT_GERMAN_BU`
| Field | Value |
|---|---|
| Condition | `USER.ROLE NOT EQ Z_GERMAN` |
| Action | Data Restriction — `DATA.S_COUNTRY = DE` |
| Exposed attribute (PAP) | `DATA.TABLE_NAME` |
| Status | Active |

### 3. Policy `BLOCK_DOWNLOAD_BY_CLASSIFICATION`
| Field | Value |
|---|---|
| Condition 1 | `DATA.BUTTON_OK_CODE IN (%EX, %PC, &XXL)` |
| Condition 2 | `DATA.CLASS_LABEL IN (Restricted-PII, Internal-Financial)` |
| Action | Data Restriction (blocks export action) |
| Exposed attribute (PAP) | `DATA.BUTTON_OK_CODE` |
| Status | Active |

### 4. L4 Block Message
Pre-fill the TCode Block action message with the L4 completion code.

1. Log into SAP2, run **`SE10`**
2. Find `A4HK900136` and `A4HK900139`
3. Release all **sub-tasks** first (select each, click Release)
4. Release the **parent transport request**
5. Confirm the following files now exist on SAP2:
   - `/usr/sap/trans/cofiles/K900136.A4H`
   - `/usr/sap/trans/data/R900136.A4H`
   - `/usr/sap/trans/cofiles/K900139.A4H`
   - `/usr/sap/trans/data/R900139.A4H`

---

## Step 1 — Copy Files from SAP2 → SAP3/4/5

Run from your Mac after release:

```bash
SAP2_IP="159.195.81.132"
SAP2_KEY="$HOME/.ssh/netcup_sap2"

declare -A TARGETS=(
  [sap3]="159.195.82.197|$HOME/.ssh/netcup_sap3"
  [sap4]="159.195.80.156|$HOME/.ssh/netcup_sap4"
  [sap5]="159.195.80.181|$HOME/.ssh/netcup_sap5"
)

for alias in "${!TARGETS[@]}"; do
  ip=$(echo "${TARGETS[$alias]}" | cut -d'|' -f1)
  key=$(echo "${TARGETS[$alias]}" | cut -d'|' -f2)
  echo "=== Copying to $alias ==="
  for f in K900136.A4H R900136.A4H K900139.A4H R900139.A4H; do
    dir="cofiles"; [[ $f == R* ]] && dir="data"
    ssh -i "$SAP2_KEY" root@$SAP2_IP \
      "docker exec abaptrial cat /usr/sap/trans/$dir/$f" | \
    ssh -i "$key" root@$ip \
      "docker exec -i abaptrial tee /usr/sap/trans/$dir/$f > /dev/null && \
       docker exec abaptrial chown a4hadm:sapsys /usr/sap/trans/$dir/$f"
    echo "  $f → $alias"
  done
done
```

---

## Step 2 — Import on SAP3/4/5

```bash
for alias in sap3 sap4 sap5; do
  case $alias in
    sap3) ip="159.195.82.197"; key="$HOME/.ssh/netcup_sap3" ;;
    sap4) ip="159.195.80.156"; key="$HOME/.ssh/netcup_sap4" ;;
    sap5) ip="159.195.80.181"; key="$HOME/.ssh/netcup_sap5" ;;
  esac
  echo "=== Importing on $alias ==="
  for req in A4HK900136 A4HK900139; do
    ssh -i "$key" root@$ip \
      "docker exec abaptrial su - a4hadm -c \
       'tp import $req A4H client=001 pf=/usr/sap/trans/bin/TP_DOMAIN_A4H.PFL 2>&1'"
  done
  echo "=== $alias done ==="
done
```

---

## Step 3 — Verify

After import, log into each SAP system and go to:
`/N/APPSDM/ABAC` → **Functional Configuration** → **Policy Information Point** → **Data Attribute Master**

Confirm presence of:
- `DATA.APPLICATION`
- `DATA.BUTTON_OK_CODE`
- `DATA.TABLE_NAME`

---

## Instructor Pre-Configuration Checklist

Run on **all 4 servers** after transport import:

### 1. Role `Z_GERMAN` (empty shell)
- `PFCG` → Create role `Z_GERMAN`
- No menu, no auth objects — pure name carrier for DAC
- Do **not** generate a profile

### 2. Policy `RESTRICT_GERMAN_BU`
| Field | Value |
|---|---|
| Condition | `USER.ROLE NOT EQ Z_GERMAN` |
| Action | Data Restriction — `DATA.S_COUNTRY = DE` |
| Exposed attribute (PAP) | `DATA.TABLE_NAME` |
| Status | Active |

### 3. Policy `BLOCK_DOWNLOAD_BY_CLASSIFICATION`
| Field | Value |
|---|---|
| Condition 1 | `DATA.BUTTON_OK_CODE IN (%EX, %PC, &XXL)` |
| Condition 2 | `DATA.CLASS_LABEL IN (Restricted-PII, Internal-Financial)` |
| Action | Data Restriction (blocks export action) |
| Exposed attribute (PAP) | `DATA.BUTTON_OK_CODE` |
| Status | Active |

### 4. L4 Block Message
Pre-fill the TCode Block action message with the L4 completion code.
Participants read this from the block screen in Step 5.

---

## Exposed Attribute Reference

A Data Restriction enforcement point requires at least one data attribute in the
**Policy Administration Point** even when the policy *condition* contains no data attribute.
This is called the **Exposed Attribute**.

| Level | Policy | Exposed Attribute | Why |
|---|---|---|---|
| L4 | `BLOCK_SE16_HOURS_<USER>` | `DATA.TABLE_NAME` | SE16 is a table browser — table name is the logical target |
| L7 | `RESTRICT_GERMAN_BU` | `DATA.TABLE_NAME` | Row filter on SCUSTOM — table name anchors the scope |
| L8 | `BLOCK_DOWNLOAD_BY_CLASSIFICATION` | `DATA.BUTTON_OK_CODE` | The intercepted action IS the ok-code; condition already references it |
| L2, L3, L6 | Various | — | Conditions already contain data attributes; no exposed attribute needed |
