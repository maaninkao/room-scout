# Room Scout

Monitors Joivy coliving listings in Trento and sends a push notification to your phone via ntfy.sh when a new room matches your filters. No login, no auto-messaging — pure observer.

## Quick Start

```bash
# 1. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

# 2. Install
pip install -e ".[dev]"

# 3. Install the ntfy app on your phone, then subscribe to a long random topic
#    e.g. ntfy.sh/my-secret-room-scout-abc123

# 4. Copy example configs and fill in your values
cp config.example.yaml config.yaml    # edit filters as needed
cp .env.example .env                  # set NTFY_TOPIC=your-topic

# 5. Verify push works (sends a test notification)
room-scout test-notify

# 6. Run the scanner once
room-scout run-once
```

## Filters (config.yaml)

| Key | Type | Description |
|-----|------|-------------|
| `max_price_eur` | int \| null | Reject rooms above this monthly price |
| `min_price_eur` | int \| null | Reject rooms below this monthly price |
| `min_size_sqm` | float \| null | Reject rooms smaller than this |
| `max_size_sqm` | float \| null | Reject rooms larger than this |
| `earliest_available` | YYYY-MM-DD \| null | Reject rooms available before this date |
| `latest_available` | YYYY-MM-DD \| null | Reject rooms not available by this date |
| `address_must_contain` | list[str] | Room address must contain at least one of these strings (case-insensitive) |
| `address_must_not_contain` | list[str] | Room address must not contain any of these strings |
| `include_recently_booked` | bool | Include rooms marked as "Recently Booked" (default: false) |

## Data Paths

| Path | Purpose |
|------|---------|
| `data/seen.db` | SQLite database tracking seen and notified listings |

To reset deduplication (re-notify all matching rooms on next run):

```bash
rm data/seen.db
```

## Known Limitations

- **Parse is best-effort** — the scraper uses HTML parsing (Strategy B) against Joivy's rendered page structure; if Joivy changes their markup, some fields may silently fall back to `None`.
- **No scheduler** — `run-once` is a single scan. Schedule it yourself (Task Scheduler, cron, etc.) if you want periodic checks.
- **Live fetch requires internet** — tests run entirely against a local fixture; live mode calls `joivy.com` directly via httpx.

## Deploy via GitHub Actions

Scout runs every 10 minutes on GitHub Actions for free on a public repo.

1. Push this repo to GitHub (public).
2. Go to repo **Settings → Secrets and variables → Actions → New repository secret**.
3. Add two secrets:
   - `NTFY_TOPIC` — your ntfy topic name (plain text, same as in .env)
   - `CONFIG_YAML` — your `config.yaml` file contents encoded as base64.
     Generate with PowerShell:
     `[Convert]::ToBase64String([System.IO.File]::ReadAllBytes("config.yaml"))`
4. Go to **Actions** tab. If workflows are disabled, click to enable.
5. First run: click **Room Scout** → **Run workflow** → **Run workflow** button. 
   This triggers immediate test run. Check logs and your phone.
6. After that, the scheduler runs every 10 min automatically.

### Updating filters

To change filters, regenerate the base64 from your edited local `config.yaml` 
and paste the new value into the `CONFIG_YAML` secret. Changes take effect 
on the next scheduled run.
