# Minimal Private Telegram ↔ Bale File Relay (Python 3.12)

Family-use skeleton that runs on **two Linux servers** with polling and local JSON state.

## What this does

- **Server A**
  1. Polls Telegram updates.
  2. Receives a file document from Telegram.
  3. Downloads file, splits into 20 MB parts.
  4. Sends protocol text + part documents to Bale.
  5. Polls Bale for `LINK_READY`, then forwards link back to original Telegram chat.

- **Server B**
  1. Polls Bale updates.
  2. Receives `JOB_START`, part documents (`PART` in caption), and `JOB_DONE`.
  3. Downloads all parts, verifies all exist, reassembles and checks SHA256.
  4. Hosts the output file over HTTP.
  5. Sends `LINK_READY` back in Bale chat.

## Layout

```
server_a/
  app.py
  telegram_bot.py
  bale_client.py
  splitter.py
  state.py
server_b/
  app.py
  bale_listener.py
  reassembler.py
  file_host.py
  state.py
shared/
  protocol.py
  utils.py
requirements.txt
.env.example
README.md
```

## Protocol

- `JOB_START {job_id, original_filename, total_parts, original_size, sha256}`
- `PART {job_id, part_index, total_parts, part_filename}` in document caption
- `JOB_DONE {job_id}`
- `LINK_READY {job_id, download_url}`

All protocol messages are plain text: `KIND <json>`.

## Quick start

## 1) Install

On both servers:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Configure env

Copy `.env.example` and set values:

```bash
cp .env.example .env
```

Required highlights:

- `TELEGRAM_BOT_TOKEN` (server A)
- `BALE_API_BASE` (both)
- `BALE_CHAT_ID` (shared chat or group where A and B bots can communicate)
- `PUBLIC_BASE_URL` (server B public URL to downloads)
- `BALE_BOT_TOKEN`
  - For server A process: token for A Bale bot.
  - For server B process: token for B Bale bot (or reuse same bot for testing).

If using `BALE_BOT_TOKEN_B` from sample, export before starting server B:

```bash
export BALE_BOT_TOKEN="$BALE_BOT_TOKEN_B"
```

## 3) Run server B first

```bash
python -m server_b.app
```

## 4) Run server A

```bash
python -m server_a.app
```

## Usage

1. Send a file (as document) to Telegram bot (server A).
2. Wait for relay.
3. Receive final link back in Telegram.

## Notes

- Polling only, no webhooks.
- No database, only JSON state in `data/server_a/jobs.json` and `data/server_b/jobs.json`.
- This is intentionally minimal and not hardened for production.
- Bale API calls assume Telegram-compatible endpoints.
