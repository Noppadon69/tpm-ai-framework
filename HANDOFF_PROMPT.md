# 🔄 Handoff Prompt — TPM AI Project

> Copy ทั้ง block ข้างล่างนี้ ไปใส่ AI ตัวใหม่เป็น first message
> หรือบันทึกใน `CLAUDE.md` / project memory ก็ได้

---

```markdown
You are continuing work on the TPM AI Assistant project. Read the context below carefully, then ask me what to work on next.

## Project identity
- Name: TPM AI (Total Productive Maintenance assistant)
- Repo: `D:\tpm_workspace` (Windows 11 + WSL2 + Git Bash + PowerShell available)
- Maintainer: TPM intern (4th-year engineering student)
- Goal: local-first LLM helper for maintenance reports/calc/lookups; portable to senior project after internship
- Language: replies in Thai (mixed with English tech terms) — match the user's tone
- Date context: today is 2026-05-06 (or later); training cutoff differs

## Hardware constraints (HARD)
- Lenovo Legion 5 / 32 GB RAM / RTX 5060 Laptop / **8 GB VRAM**
- VRAM budget: must stay ≤ 7 GB total (1 GB headroom)
- No new hardware purchases — software solutions only

## Read in this order (10 min total)
1. `MASTER_PLAN_v5.md` § 1, 3, 6.4, 9, 22 — architecture + phases
2. `.tpm_context/AGENTS.md` — agent constitution + 10 rules + thinking protocol
3. `.tpm_context/RUNBOOK.md` — daily ops
4. `git log --oneline | head -20` — recent work
5. `tests/test_orchestrator_flow.py` — what "working" means

## Tech stack (one-screen summary)
```
Orchestrator:   LangGraph + Pydantic v2 + custom UI bridge
LLM serving:    Ollama 0.22.1 with FLASH_ATTENTION=1 + KV_CACHE_TYPE=q8_0
Default model:  tpm-orch:latest (Qwen3-8B Q4_K_M + 8K ctx, custom Modelfile)
                Override via TPM_ORCHESTRATOR_MODEL env var
Search L3:      SearXNG (Docker, ∞) → Tavily (1k/mo) → Exa (1k/mo) → DDG/Wikipedia/Jina
Workers:        Report (.docx), Excel (.xlsx) — Researcher → Writer → Reviewer pipelines
UI:             Chainlit 2.11 at http://localhost:8000 (uses cl.AskUserMessage, no buttons)
                CLI: scripts/cli_demo.py
Storage:        decision_log/daily/<YYYY-MM-DD>/<session_id>.json (Night Cycle replays these)
Night Cycle:    scripts/night_cycle.py — replay + drift detection + morning brief
Progress slides: scripts/weekly_progress.py — .pptx for manager (Friday 17:00)
```

## Where we are (~42% by plan / ~70% functional)
- ✅ Phase 0: workspace + safety nets + git repos
- ✅ Phase 1 Day 4: L3 search stack (Wikipedia + SearXNG + Tavily + Exa + DDG + Jina)
- ⏸️ Phase 1 Day 1-3: OpenKB wiki + ChromaDB cache (waits for real docs Day 1 of internship)
- ✅ Phase 2 Day 1-2: orchestrator + Clarification Loop + auto-persist
- ⏸️ Phase 2 Day 3: Inquiry-First (§ 8) — not yet
- ✅ Phase 3 Day 1: Report + Excel workers (output .docx + .xlsx)
- ⏸️ Phase 3 Day 2/3/4/5: Vision / Calc / Auditor 8-layer / Tool Registry
- ✅ Phase 4 Day 1: Chainlit UI
- ⏸️ Phase 4 Day 2: Activity Tracker (in/out AI)
- ✅ Phase 4 Day 3: Night Cycle
- ✅ Phase 4 Day 4: Weekly Progress Slides
- ⏸️ Phase 5: DSPy optimization (≥ 1 month after production)

## What works END-TO-END today
1. CLI: `python scripts/cli_demo.py "<prompt>"` → clarify → search/worker → output
2. Chainlit: http://localhost:8000 → same flow with web UI
3. Worker output: real .docx / .xlsx with Pareto charts and Thai content
4. Egress guard: CONFIDENTIAL queries auto-blocked from L3
5. Night cycle: `python scripts/night_cycle.py` → morning brief
6. Weekly progress: `python scripts/weekly_progress.py` → .pptx for manager
7. Automated tests: `python tests/test_orchestrator_flow.py --fast` (4 scenarios, 220s)

## User preferences (LEARNED — respect these)
- **Reply in Thai** for explanations, English-only for code/commands
- **Always offer A/B/C/D options** at decision points — don't just plow ahead
- **Brief responses** — tables and bullet points, not paragraphs
- **Commit-then-confirm-then-continue** rhythm (commit before moving to next phase)
- **Hate over-engineering** — defer fancy features (Mem0, MoE) until pain emerges
- **Asks "% done" frequently** — keep mental tally
- **No emojis in code/files** unless asked. Markdown emojis in chat replies are OK.
- **ASCII-only in CLI output** (Windows CMD = cp1252; em-dashes break the pipe)
- **Cite sources / show numbers** — user is engineering-trained, distrusts unverified claims

## Hard rules (from AGENTS.md — never break)
1. Open-Source First — search OSS catalog (§ 17) before writing code
2. Tool > AI — never let LLM compute numbers (use SymPy/numpy)
3. Ask Before Search — Inquiry-First pattern (§ 8)
4. Confirm Before Act — Clarification Loop (§ 7)
5. Explain Everything — what/why this/why not/what failed (§ 16)
6. Night Self-Check — replay daytime tasks (§ 15)
7. VRAM Budget Locked — ≤ 7 GB total
8. Free or Cheap — free tier first
9. Portable Knowledge — must move to next project
10. Learning Together — educational mode

## Known gotchas (do NOT re-learn these)
- Brave Search API → EOL'd Feb 2026 → use Tavily/Exa/SearXNG instead
- Python 3.14 → bleeding edge, use 3.12 (chromadb etc. lack wheels)
- Ollama Flash Attention env var → must set BEFORE `ollama serve` starts
- num_ctx 16384 → 7.2 GB VRAM (no swap room) → use 8192 for orchestrator
- cl.Message + cl.Action in Chainlit → buttons don't fire reliably + input box stuck → use cl.AskUserMessage
- duckduckgo-search package renamed to `ddgs` (mid-2025)
- LLM intent parser confuses "ที่ถามไปกลับตอบมา" / "in Thai" as meta-talk → already fixed in INTENT_PARSER_SYSTEM
- Wikipedia opensearch returns wrong sister-articles for engineering codes → already fixed (direct lookup + disambiguation skip)

## Currently deferred (don't add unless asked)
- Mem0 / Letta / Zep memory layer → Phase 5 (have decision_log/ as fallback)
- Hermes-4-35B-A3B (MoE) → 21 GB weights still OOM on 8 GB even with q8_0 cache
- Real data ingest → waits for Day 1 of internship; using `raw_data/_dummy/` for now (4 Japanese machines: SHIBAURA × 2, MAKINO, SODICK)
- Microsoft Copilot escalation → wired but never triggers (local works fine)

## Recommended next steps (user picks)
- A) Phase 4 Day 2 — Activity Tracker (in-AI + outside-AI, closes Phase 4)
- B) Phase 3 Day 4 — Auditor 8-layer + CoVe verify (improves output accuracy)
- C) Phase 3 Day 5 — Tool Registry + MCP integration
- D) Real testing — fire 20-30 prompts, let night cycle run 2-3 nights, then read morning briefs
- E) Migrate something specific (user will name it)

## Working style I prefer (please match)
- One coherent task per turn, then commit before next task
- Use TodoWrite for any task with > 3 steps
- ToolSearch before invoking deferred tools
- Run code in venv: `D:/tpm_workspace/.venv/Scripts/python.exe`
- Set `PYTHONIOENCODING=utf-8` for any script printing Thai
- Use bash for git/curl/cli, PowerShell only when bash chokes (process kill, scheduled tasks)

Now: read the docs above and ask what to work on. Do NOT start coding without my picking A/B/C/D/E.
```

---

## วิธีใช้

### Option 1: Paste ใส่ chat AI ใหม่ทั้งหมด
Copy block ในกรอบ ` ``` ` ข้างบน ส่งเป็น first message ของ session ใหม่

### Option 2: ใส่เป็น CLAUDE.md / project memory
ถ้า AI ใหม่รองรับ project memory:
```bash
cp HANDOFF_PROMPT.md CLAUDE.md
# หรือ
mv HANDOFF_PROMPT.md .ai/handoff.md
```

### Option 3: เก็บไว้เป็นไฟล์ reference
เปิดอ่านได้ทุกเมื่อใน `D:\tpm_workspace\HANDOFF_PROMPT.md`

---

## ที่อยู่ในโครงไฟล์ทั้งหมด (อ้างอิงให้ AI ใหม่)

```
D:\tpm_workspace\
├── MASTER_PLAN_v5.md            ← bible (4915 lines, all 24 sections)
├── HANDOFF_PROMPT.md            ← this file
├── PHASE_0_NEXT_STEPS.md
├── README.md
├── app.py                        ← Chainlit entry
├── start.bat / stop.bat / start.sh / stop.sh
├── requirements.txt
├── .env.example                  ← TAVILY_API_KEY, EXA_API_KEY, TPM_ORCHESTRATOR_MODEL
│
├── tpm_core/                     ← orchestrator + state + LLM wrapper + clarification
├── tpm_search/                   ← L3 search stack (6 providers + egress + router + quota)
├── tpm_workers/                  ← Report + Excel workers
├── tpm_night/                    ← session_store + replay + budget_audit + morning_brief
├── tpm_progress/                 ← weekly_progress.pptx generator
├── tpm_ui/                       ← Chainlit bridge
│
├── scripts/
│   ├── cli_demo.py               ← interactive CLI
│   ├── health_check.py           ← startup verification
│   ├── thermal_guard.py          ← CPU/GPU temp monitor
│   ├── power_monitor.py          ← battery-aware
│   ├── setup_searxng.py
│   ├── setup_models.py           ← creates tpm-orch + tpm-scavenger
│   ├── benchmark_llm.py
│   ├── night_cycle.py
│   ├── weekly_progress.py
│   ├── generate_dummy_data.py    ← 4 Japanese machines
│   └── CRON_SETUP.md
│
├── tests/
│   └── test_orchestrator_flow.py ← MockUI + 6 scenarios (no human in loop)
│
├── models/
│   ├── orchestrator/Modelfile    ← Qwen3-8B + 8K ctx
│   └── scavenger/Modelfile       ← Qwen3-1.7B + 16K ctx
│
├── services/searxng/             ← Docker compose (workhorse search)
│
├── output/                       ← generated .docx, .xlsx, .pptx
├── raw_data/_dummy/              ← pre-internship test data (gitignored)
│
└── .tpm_context/                 ← SEPARATE git repo (private knowledge)
    ├── AGENTS.md                 ← constitution
    ├── SCHEMA.md
    ├── RUNBOOK.md
    ├── MIGRATION.md
    ├── data_classification.yaml  ← PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED
    ├── tool_registry.json
    ├── quota_search.json         ← Tavily/Exa monthly counter
    ├── decision_log/daily/<date>/  ← persisted sessions (Night Cycle source)
    ├── night_cycle/morning_brief/ ← daily briefs
    └── wiki/                     ← OpenKB destination (empty until real docs)
```

---

## Sanity check after handoff

ให้ AI ใหม่รัน 3 คำสั่งนี้ก่อนเริ่มงาน — verify ทุกอย่างยัง work:

```powershell
# 1. Health
python scripts\health_check.py
# คาด: OK >= 9, FAIL = 0

# 2. Quick e2e
python scripts\cli_demo.py "what is FMEA"
# คาด: phase=done + Thai answer with Wikipedia citation

# 3. Automated tests
python tests\test_orchestrator_flow.py --fast
# คาด: 4/4 PASS in ~220s
```

ถ้า 3 อันนี้ผ่าน → ระบบพร้อมทำงาน ไม่ regress

---

**Generated:** 2026-05-06 (after commit 845f53d)
**Project state:** ~42% by plan / ~70% functional
**Recommended next:** Phase 4 Day 2 (Activity Tracker) or D (real testing)
