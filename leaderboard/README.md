# DAC Workshop Leaderboard

Flask app that runs on the off-grid server at `http://10.8.0.1:9000`.

## TODO — Public Deployment (no VPN required)

> **Feasibility: ✅ Yes, straightforward.**
>
> The leaderboard can be added to the existing `docker-compose.yml` alongside `abaptrial` and `nginx-pathlock`,
> and exposed publicly via the server's public IP `152.53.187.143` on port `9000` (or via nginx on 443 with a path).
>
> This means participants can:
> - View the leaderboard from their phone/laptop **without being on the VPN**
> - Submit codes from anywhere — useful if the workshop is in-person and you want a big screen leaderboard
> - Register before the session starts (from home/office)
>
> **What needs to be done:**
> - [ ] Add `dac-leaderboard` service to `infra/docker/docker-compose.yml`
> - [ ] Add `iptables` rule to allow `0.0.0.0 → port 9000` (or route through nginx on 443)
> - [ ] Update `infra/iptables/rules.v4` accordingly
> - [ ] Optional: add `/leaderboard` location block in `infra/nginx/nginx.conf` so it's served over HTTPS
>       as `https://152.53.187.143/leaderboard` instead of raw port 9000
> - [ ] Admin route (`/admin`, `/admin/reset`) should stay VPN-only — add IP restriction in nginx
>       so only `10.8.0.0/24` can hit those paths
>
> **Note:** The leaderboard has no sensitive data — just names, scores, and completion codes.
> Safe to expose publicly. The SAP system itself remains VPN-only as always.

---

## How it works

Participants register → complete levels in SAP/Pathlock → find a **completion code** embedded in the system → submit it → score points.

The leaderboard auto-refreshes every 10 seconds and can be shown on a shared screen.

## Scoring

| Action | Points |
|---|---|
| Level completion (correct code) | 100–200 pts (varies by level) |
| 1st to complete a level | +50 pts |
| 2nd to complete | +25 pts |
| 3rd to complete | +10 pts |
| Wrong code attempt | -5 pts |

## Instructor setup (before the session)

### 1. Set the completion codes

Edit `level_codes.json`. Each code must be something participants find **inside SAP or Pathlock** — not guessable. Examples:

- L0: Count of rows in `SCUSTOM` (participants run `SE16N → SCUSTOM → count`)
- L1: The policy ID generated when they save the masking rule in Pathlock
- L2: The exact masked value pattern shown for `LOCCURAM` field
- L3: First 3 chars of scrambled `NAME` for customer `00000001`
- L4: Row count in `SFLIGHT` visible to `RANALYST` after policy applied
- L5: Classification tag string they assigned to `SCUSTOM.LOCCURAM`

Codes are **case-insensitive** — the app uppercases everything before comparing.

### 2. Deploy

**Option A — Direct (on server):**
```bash
pip install flask
export LEVEL_CODES_FILE=/etc/dac-workshop/level_codes.json
python3 leaderboard.py
```

**Option B — Docker:**
```bash
# Build
docker build -t dac-leaderboard .

# Run (mounts /data for persistent SQLite DB)
docker run -d \
  --name dac-leaderboard \
  -p 9000:9000 \
  -v /srv/dac-workshop:/data \
  dac-leaderboard
```

**Option C — Add to existing docker-compose.yml:**
```yaml
  dac-leaderboard:
    build: ./dac-workshop/leaderboard
    container_name: dac-leaderboard
    ports:
      - "9000:9000"
    volumes:
      - /srv/dac-workshop:/data
    restart: unless-stopped
```

### 3. Routes

| URL | Who uses it |
|---|---|
| `http://10.8.0.1:9000/` | Leaderboard (show on projector) |
| `http://10.8.0.1:9000/register` | Participants register |
| `http://10.8.0.1:9000/submit` | Participants submit codes |
| `http://10.8.0.1:9000/admin` | Instructor — see all submissions, active codes |
| `http://10.8.0.1:9000/admin/reset` | POST — wipe all data between sessions |
| `http://10.8.0.1:9000/api/leaderboard` | JSON API |

### 4. Reset between sessions
```bash
curl -X POST http://10.8.0.1:9000/admin/reset
```

Or restart the container to wipe everything including the DB:
```bash
docker rm -f dac-leaderboard && docker run -d ... (same command as above)
```
