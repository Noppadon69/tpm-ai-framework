# n8n — Telegram bridge + automation glue (no-code)

Self-hosted workflow automation. Used as the **Telegram bot layer** for TPM AI
without writing Python bot handlers — and as a generic glue for cron / file
watcher / webhook plumbing.

Rationale: see `.tpm_context/tool_watchlist.md` (2026-05-13 batch, n8n entry).

---

## Quick start

```bash
cd services/n8n
docker compose up -d
# UI: http://localhost:5678  (first launch asks to create owner account)
```

Owner account is local-only (N8N_SECURE_COOKIE=false; do not expose this
port to the LAN without enabling HTTPS first).

---

## Wiring the Telegram bot (one-time, no code)

1. **Get a bot token from @BotFather** in Telegram:
   - `/newbot` → name + username → copy the `123456:ABC-DEF...` token
   - `/setprivacy` → Disable (so bot sees all messages in groups, optional)

2. **Get your chat_id** (so the bot can reply to you):
   - DM the bot once → open `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Copy the `chat.id` integer

3. **In n8n UI** (http://localhost:5678):
   - Credentials → New → Telegram API → paste token
   - New Workflow → add nodes:
     1. **Telegram Trigger** (event: message) — credential = step above
     2. **HTTP Request** — Method POST, URL `http://host.docker.internal:8000/api/ask`
        (or wherever your local FastAPI wrapper around `cli_demo.py` listens).
        Body = `{ "prompt": "{{ $json.message.text }}" }`
     3. **Telegram Send Message** — Chat ID = `{{ $json.message.chat.id }}`,
        Text = `{{ $node["HTTP Request"].json.answer }}`
   - Activate workflow.

4. **Optional patterns** (drop separate workflows for each):
   - **Night-cycle alert:** Cron node 06:00 → Read morning_brief.md →
     Telegram Send (you receive brief on phone).
   - **Egress block alert:** Webhook node listens for orchestrator POST →
     Telegram Send (you see CONFIDENTIAL blocks in real time).
   - **PM reminder:** Cron node weekly → query `tpm_mold/pm_log.py` for
     molds with shots > threshold → Telegram Send list.

---

## Portable workflows

Workflows export to JSON in `./workflows/` (volume-mounted). Commit those
JSONs to the repo so the bot setup migrates with the project (per Section 19
portability principle).

```bash
# n8n UI → workflow → ... menu → Download
# move the file into ./workflows/ before next container restart
```

Do **not** commit `n8n_data` (contains the bot token in encrypted form);
it's a Docker volume, not a host path.

---

## When to migrate off n8n

n8n is overkill if you only need 1 cron + 1 send-message and never grow past
that. The cutover threshold:
- ≥ 3 active workflows → keep n8n
- ≤ 2 workflows + no UI editing needed → replace with `python-telegram-bot`
  + `apscheduler` in a single script (~80 LOC).

Right now (2026-05-13) the plan is: start with n8n, re-evaluate after a month
of internship use.
