# MSMC

**Microsoft / Xbox / Minecraft account checker** — multi-threaded, proxy-aware, with Hypixel enrichment and Discord webhook notifications.

Windows · Linux · macOS

> Original concept and initial implementation by **KillinMachine**. This is a rewritten, bug-fixed, cross-platform build.

---

## What it does

Takes a combo file (`email:password`), authenticates each against Microsoft's OAuth flow, walks the Xbox Live → XSTS → Minecraft Services chain, and classifies the result:

- **Hit** — valid MS login *and* owns a Minecraft product
- **XGPU** — Xbox Game Pass Ultimate (includes Java + Bedrock)
- **XGP** — Xbox Game Pass PC
- **Other** — owns Bedrock / Legends / Dungeons but not Java
- **Valid Mail** — MS login works, no Minecraft entitlement
- **2FA** — login triggered a 2FA challenge
- **Bad** — invalid credentials, locked, or rate-limited
- **MFA / SFA** — full vs. single-factor mail access (via `email.avine.tools`)

Each hit gets enriched with:

- Minecraft username, UUID, capes
- Optifine cape presence
- Hypixel name, level, first/last login, Bedwars stars
- Hypixel SkyBlock networth (via SkyCrypt)
- Hypixel ban status (via pyCraft connection to `alpha.hypixel.net`)
- Minecraft name-change availability + last change date

All hits are written to disk and pushed to a Discord webhook.

---

## Project layout

```
MSMC.py              — the checker
requirements.txt     — python deps
config.ini           — created on first run, editable
results/
  <combo-name>/
    Hits.txt                — every valid Minecraft hit
    Capture.txt             — full enriched capture blocks
    2fa.txt                 — accounts that hit 2FA
    MFA.txt                 — accounts with mail access
    SFA.txt                 — accounts without mail access
    Banned.txt              — Hypixel-banned hits
    Unbanned.txt            — clean Hypixel hits
    Valid_Mail.txt          — MS login works, no MC
    XboxGamePass.txt
    XboxGamePassUltimate.txt
    Other.txt
```

---

## Requirements

- **Python 3.9+** (3.10 or 3.11 recommended)
- **pip**
- **tkinter** for file dialogs (usually bundled; on Debian/Ubuntu you may need `sudo apt install python3-tk`)
- **pyCraft** for Hypixel ban checks (optional but enabled by default)

### Install

```bash
pip install -r requirements.txt
```

On macOS or externally-managed Linux, pyCraft may need:

```bash
pip install --user git+https://github.com/ammaraskar/pyCraft.git
```

### Platform notes

**Windows**
- Tested on Windows 10 / 11 with stock Python from python.org.
- Windows Defender will flag this as PUA — it reads Microsoft login flows and opens raw sockets to Hypixel. Whitelist the folder if needed.

**Linux**
- If you run this on a headless box, tkinter dialogs won't work. The script falls back to typing paths in the terminal. Or install `python3-tk`.
- `python3 -m pip install -r requirements.txt`.

**macOS**
- On Apple Silicon, `pip install pyCraft` may compile. If it fails, use the `--user git+https://...` form.
- If your Python is Homebrew-managed (externally managed env), use a venv:
  ```bash
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  ```

---

## Usage

```bash
python MSMC.py
```

You'll be prompted in order:

### 1. Threads

```
Threads: 
```

- **100** with proxies (or higher if proxies are fast)
- **≤5** proxyless — Microsoft will rate-limit you hard above this

### 2. Proxy type

```
Proxy Type: [1] Http [2] Socks4 [3] Socks5 [4] None [5] Auto: 
```

- **1** — HTTP proxies from your file
- **2** — SOCKS4
- **3** — SOCKS5
- **4** — proxyless (your IP, low threads)
- **5** — auto-scrape live proxies in background (refreshes every N minutes per config)

### 3. Screen

```
Screen: [1] CUI [2] Log: 
```

- **1 — CUI**: clears and reprints the stats block every second. Clean view, but scrollback is gone.
- **2 — Log**: scrolling hits/errors plus live stats in the window title bar. Better for debugging.

### 4. File pickers

- **Combos** — `.txt`, one `email:password` per line. Dupes auto-removed.
- **Proxies** — `.txt`, one `host:port` per line (`user:pass@host:port` supported for SOCKS5).
- **Ban-check proxies** — SOCKS5 only, used exclusively for the Hypixel ban check.

Files can also be entered as text paths if tkinter isn't available.

---

## Output

Live stats in the title bar and/or CUI:

```
Checked 1234\10000  -  Hits: 12  -  Bad: 900  -  2FA: 5  -  SFA: 40  -  MFA: 8
-  XGP: 3  -  XGPU: 2  -  VM: 15  -  Other: 1  -  Cpm: 480  -  Retries: 40  -  Errors: 0
```

On completion, a summary is printed and any key exits cleanly.

Results are written under `results/<combo-filename>/`. Re-running with the same combo file **appends** — rename or move the results folder for a clean run.

---

## Configuration — `config.ini`

Auto-created on first run. Missing keys are backfilled automatically on upgrade, so your existing config keeps working.

```ini
[Settings]
Webhook = https://discord.com/api/webhooks/...
Max Retries = 5
Proxyless Ban Check = False
WebhookMessage = @everyone HIT: ||`<email>:<password>`||
Name: <name>
...

[Scraper]
Auto Scrape Minutes = 5

[Captures]
Hypixel Name = True
Hypixel Level = True
First Hypixel Login = True
Last Hypixel Login = True
Optifine Cape = True
Minecraft Capes = True
Email Access = True
Hypixel Skyblock Coins = True
Hypixel Bedwars Stars = True
Hypixel Ban = True
Name Change Availability = True
Last Name Change = True
```

### Key notes

- **Webhook** — Discord webhook URL. Leave as the default placeholder to disable notifications.
- **WebhookMessage** — template. Placeholders: `<email>`, `<password>`, `<name>`, `<type>`, `<hypixel>`, `<level>`, `<firstlogin>`, `<lastlogin>`, `<ofcape>`, `<capes>`, `<access>`, `<skyblockcoins>`, `<bedwarsstars>`, `<banned>`, `<namechange>`, `<lastchanged>`.
- **Max Retries** — per-stage retry cap for network/auth failures.
- **Proxyless Ban Check** — set `True` to run the Hypixel ban check from your own IP (needs proxyless mode and low threads).
- **Auto Scrape Minutes** — refresh interval for the auto-scraper.
- **Captures** — toggle individual enrichment fields on/off. Turn off what you don't need to speed up hits significantly.

---

## Architecture

```
Main()
 ├─ loadconfig()
 ├─ prompt threads / proxy type / screen
 ├─ Load()                              → Combos
 ├─ Proxys() / banproxyload()           as needed
 ├─ get_proxies() (background)          if auto-scrape
 └─ ThreadPoolExecutor(threads)
     └─ Checker(combo)
         └─ authenticate(email, password)
             ├─ get_urlPost_sFTTag()    → PPFT + urlPost
             ├─ get_xbox_rps()          → MS access token
             ├─ user.auth.xboxlive.com  → xbox token + uhs
             ├─ xsts.auth.xboxlive.com  → xsts token
             ├─ mc_token()              → MC access token
             └─ checkmc()
                 └─ capture_mc()
                     └─ Capture.handle()
                         ├─ Hits.txt
                         ├─ hypixel()       (Plancke + SkyCrypt)
                         ├─ optifine()
                         ├─ full_access()
                         ├─ namechange()
                         ├─ ban()           (pyCraft → alpha.hypixel.net)
                         ├─ Capture.txt
                         └─ notify()        (Discord webhook)
```

### Threading model

- A single `ThreadPoolExecutor` runs `Checker` per combo.
- Two daemon threads drive the stats screen (CUI repaint or title-bar log).
- One background thread scrapes proxies when auto mode is on.
- A single lock (`_socket_lock`) serializes the socket monkey-patch used by `ban()` — ban checks queue on it, but they're slow anyway, so no throughput loss.

### Proxy handling

Every `requests.Session` is created via `new_session()`, which stamps the current proxy dict onto `session.proxies`. On 429 or connection error, the session rotates to a fresh proxy from the pool. The ban check uses a separate SOCKS5 pool, patches `socket.socket` under a lock, connects, and restores immediately.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'minecraft'`**
pyCraft isn't installed. Run `pip install git+https://github.com/ammaraskar/pyCraft.git`, or ignore — the checker will just skip ban checks.

**`ModuleNotFoundError: No module named 'socks'`**
`pip install PySocks`.

**tkinter missing on Linux**
`sudo apt install python3-tk` (Debian/Ubuntu), or just type file paths when prompted.

**Defender / antivirus flags the .py**
Expected. It reads login forms and opens raw sockets to Hypixel. Whitelist the folder or run in a VM.

**All hits are Bad / 2FA**
Your proxy pool is dead. Check that your proxy file is one `host:port` per line, and that the proxies work with the protocol you selected. Test with a small run before a big one.

**Cpm drops to zero**
Every thread is stuck retrying. Usually means the proxy pool is exhausted. Either load a bigger pool, drop threads, or switch to proxyless with 3-5 threads.

**Hypixel ban check always returns "Unknown"**
Alpha Hypixel is closed (it goes down regularly), or you're being rate-limited. Try a different SOCKS5 pool or drop threads.

**`email.avine.tools` returns nothing**
The original author's API is down. MFA/SFA fields will be "Unknown" for those hits; everything else still works.

**Config errors on startup**
Delete `config.ini` — it will be regenerated with defaults.

---

## Legal / disclaimer

This tool performs authentication requests against Microsoft, Xbox Live, and Mojang services using credentials you supply. It is intended for use against accounts you own or are authorized to test. Running it against accounts you don't control, or at volumes that trigger rate limiting, may violate Microsoft's Terms of Service. The author and contributors accept no responsibility for misuse.

---

## Credits

- **KillinMachine** — original MSMC design and implementation
- **ammaraskar** — [pyCraft](https://github.com/ammaraskar/pyCraft)
- **Plancke** — Hypixel stats at `plancke.io`
- **SkyCrypt** — SkyBlock stats at `sky.shiiyu.moe`
- **hookzof**, **prxchk**, **ProxyScrape**, **Geonode** — proxy lists

---

## License

Unlicensed / for-personal-use. Fork it, modify it, ship your own.