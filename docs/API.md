# SIP HTTP API Reference

SIP (Sustainable Irrigation Platform) exposes a small HTTP API built on
[web.py](http://webpy.org/). Every control endpoint is a `GET` request.
This reference was verified against `urls.py` and `webpages.py` on the
`master` branch.

## Base URL

By default SIP listens on port **8080** (configurable via the `htp` option).
If your instance is behind a reverse proxy, adjust the host/port accordingly:

```
http://<host>:8080/
```

## Authentication

SIP has a "use password" flag `upas`:

- If `upas == 0`, **no authentication is required**.
- Otherwise, pass the **plaintext** password as a `pw` query parameter on any
  endpoint, e.g. `?pw=YOUR_PASSWORD`. The server computes `sha256(pw)`
  internally, so do **not** pre-hash it.
- Alternatively, authenticate with a session cookie by `POST /login` (form
  field `password`). Endpoints that require auth are `ProtectedPage`
  subclasses and will redirect to `/login` when unauthenticated.

```bash
B="http://<host>:8080"
PW="?pw=YOUR_PASSWORD"   # omit entirely if no password is set (upas == 0)
```

## Endpoints

| Method | Path | Purpose | Key parameters |
|--------|------|---------|----------------|
| GET | `/api/status` | JSON status of all stations + system | — |
| GET | `/api/log` | JSON run log | — |
| GET | `/api/plugins` | plugin data | — |
| GET | `/sn` | get/set a station | `sid` (1-based; `0` = all), `set_to` (1/0), `set_time` (seconds; `0` = until turned off). **Requires manual mode (`mm=1`).** |
| GET | `/cr` | run-once program | `t=` JSON array of per-station seconds (0-based), e.g. `t=[0,300,0]` |
| GET | `/rp` | run a saved program now | `pid` (0-based program index) |
| GET | `/cv` | change controller values | `mm=1` → Manual mode, `mm=0` → Auto (Auto calls `clear_mm`, stopping manual stations); `en=0` (all off), `rd=<hours>` (rain delay), `rsn=1` (pause/rain stop) |
| GET | `/ep` | enable/disable a program | `pid`, `enable` (1/0) |
| GET | `/dp` | delete a program | `pid` (`-1` = all) |
| GET | `/cp` | add/modify a program | `pid`, `v=` JSON program object |
| GET | `/restart` | restart SIP | — |

## Manual vs Auto mode

The home page **Manual | Auto** switch corresponds to the `mm` option:

- `GET /cv?mm=1` → Manual mode (enables manual station control)
- `GET /cv?mm=0` → Auto mode (scheduled programs run; also stops any
  manually-running stations)

## Examples

```bash
# System + station status (read-only, safe to run anytime)
curl -s "$B/api/status$PW" | python3 -m json.tool

# Run station #2 for 5 minutes — run-once needs no manual mode
curl -s "$B/cr$PW?t=[0,300,0,0,0,0,0,0]"

# Run saved program #0 now
curl -s "$B/rp$PW?pid=0"

# Manual control of a single station (enable manual mode first)
curl -s "$B/cv$PW?mm=1"
curl -s "$B/sn$PW?sid=3&set_to=1&set_time=600"   # station 3 ON for 10 min
curl -s "$B/sn$PW?sid=3&set_to=0"                # station 3 OFF

# All stations off
curl -s "$B/cv$PW?en=0"

# Rain delay of 12 hours
curl -s "$B/cv$PW?rd=12"
```

## Notes / pitfalls

- `/sn` with `set_to` returns *"Manual mode not active."* unless manual mode is
  on (`/cv?mm=1`). Use `/cr` (run-once) to avoid that requirement.
- `/cr?t=` is a 0-based JSON array indexed by station. Pad it to the number of
  stations; a wrong index waters the wrong zone.
- Relay polarity (active low/high) is configured by the `relay_board` plugin
  and is independent of these endpoints (wiring-side, not API-side).
- Always call `GET /api/status` before and after a write operation to confirm
  the resulting state.
