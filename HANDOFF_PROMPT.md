# 🔄 Handoff Prompt — TPM AI Project

> Copy ทั้ง block ข้างล่างนี้ ไปใส่ AI ตัวใหม่เป็น first message
> หรือบันทึกใน `CLAUDE.md` / project memory ก็ได้

---

```markdown
You are continuing work on the TPM AI Assistant project. Read the context below carefully, then ask me what to work on next.

## Project identity
- Name: TPM AI (Total Productive Maintenance assistant)
- Repo: `D:\tpm_workspace` (Windows 11 + WSL2 + Git Bash + PowerShell available)
- Maintainer: TPM intern — 4th-year Mechanical Engineering student
- Goal: local-first LLM helper for maintenance reports/calc/lookups — built during Toshiba internship (Mold & Die / washing machine division), portable to senior project afterward
- Language: replies in Thai (mixed with English tech terms) — match the user's tone
- Date context: today is 2026-05-09 (or later); training cutoff differs

## Hardware constraints (HARD)
- Lenovo Legion 5 / 32 GB RAM / RTX 5060 Laptop / **8 GB VRAM**
- VRAM budget: must stay ≤ 7 GB total (1 GB headroom)
- No new hardware purchases — software solutions only

## Read in this order (10 min total)
1. `MASTER_PLAN_v6.md` § 1, 3, 6.4, 9, 22, 25, 26 — architecture + phases + Mold domain + gap fixes
2. `.tpm_context/AGENTS.md` — agent constitution + 10 rules + thinking protocol
3. `.tpm_context/RUNBOOK.md` — daily ops
4. `git log --oneline | head -20` — recent work
5. `tests/test_orchestrator_flow.py` — what "working" means

## Tech stack (one-screen summary)
```
Orchestrator:   LangGraph + Pydantic v2 + custom UI bridge
LLM serving:    Ollama with FLASH_ATTENTION=1 + KV_CACHE_TYPE=q8_0
Default model:  tpm-orch:latest (Qwen3-8B Q4_K_M + 8K ctx, custom Modelfile)
                Override via TPM_ORCHESTRATOR_MODEL env var
Vision model:   Qwen2.5-VL-3B (DEFAULT v6.0 — fits 8 GB VRAM; fallback: 7B CPU+GPU split)
Layer 1:        markitdown + llama-index → ChromaDB (ทดแทน openkb/pageindex ที่ไม่มีบน PyPI)
Search L3:      SearXNG self-hosted (safe engines: DDG/Qwant/Startpage/Wikipedia/GitHub/SO)
                → Tavily (1k/mo) → Exa (1k/mo) → DDG/Wikipedia/Jina
Workers:        Report (.docx), Excel (.xlsx) — Researcher → Writer → Reviewer pipelines
UI:             Chainlit at http://localhost:8000 (uses cl.AskUserMessage, no buttons)
                CLI: scripts/cli_demo.py
Storage:        decision_log/daily/<YYYY-MM-DD>/<session_id>.json
Night Cycle:    scripts/night_cycle.py — replay + drift + morning brief (+ Windows sleep guard)
Progress slides: scripts/weekly_progress.py → .pptx for manager (Friday 17:00)
```

## Where we are (~52% by plan / ~80% functional)
- ✅ Phase 0: workspace + safety nets + git repos + Docker verified
- ✅ Phase 1 Day 4: L3 search stack (SearXNG + Tavily + Exa + DDG + Wikipedia + Jina)
- ⏸️ Phase 1 Day 1-3: markitdown+llama-index wiki + ChromaDB cache (waits for real docs Day 1 of Toshiba internship)
- ✅ Phase 2 Day 1-2: orchestrator + Clarification Loop + auto-persist
- ⏸️ Phase 2 Day 3: Inquiry-First (§ 8) — not yet
- ✅ Phase 3 Day 1: Report + Excel workers (output .docx + .xlsx)
- ⏸️ Phase 3 Day 2/3/4/5: Vision / Calc / Auditor 8-layer / Tool Registry
- ✅ Phase 4 Day 1: Chainlit UI
- ✅ Phase 4 Day 2: Activity Tracker (manual JSONL logger + weekly slide integration, 2026-05-08; Tier 3 OS-tracking deferred)
- ✅ Phase 4 Day 3: Night Cycle (+ G-04 sleep-prevention patch applied 2026-05-09)
- ✅ Phase 4 Day 4: Weekly Progress Slides (now 7 slides incl. Activity breakdown)
- ⏸️ Phase 5: DSPy optimization (≥ 1 month after production)
- 🎯 **Phase 4 ปิดครบ 4/4 — สวยทั้ง phase**

## What works END-TO-END today
1. CLI: `python scripts/cli_demo.py "<prompt>"` → clarify → search/worker → output
2. Chainlit: http://localhost:8000 → same flow with web UI
3. Worker output: real .docx / .xlsx with Pareto charts and Thai content
4. Egress guard: CONFIDENTIAL queries blocked at BOTH L3 search AND worker dispatch (commit 926c044)
5. Night cycle: `python scripts/night_cycle.py` → morning brief (Windows sleep guard active)
6. Weekly progress: `python scripts/weekly_progress.py` → .pptx for manager (now 7 slides)
7. Automated tests: `python tests/test_orchestrator_flow.py --fast` (4 scenarios, ~220s, 4/4 PASS verified 2026-05-08)
8. Activity logging: `python scripts/log_activity.py --interactive` (or --duration N --category X --subject "...") — out-of-AI work logged to .tpm_context/activity_log/outside_ai/<date>.jsonl
9. Soak testing: `python scripts/test_battery.py --tag <name>` — 10-prompt MockUI battery, persists sessions for night cycle replay

## v6.0 changes vs v5.0 (patched 2026-05-09 — read before touching these areas)
| Area | v5.0 | v6.0 (now) |
|---|---|---|
| Layer 1 stack | openkb + pageindex (ไม่มีบน PyPI) | markitdown + llama-index (verified) |
| Vision default | 3 options ไม่มี default | **Qwen2.5-VL-3B** (~2 GB) — fits VRAM |
| Night Cycle sleep | ไม่ป้องกัน | `_prevent_sleep()` ใน night_cycle.py |
| SearXNG engines | Google + Bing enabled | **Disabled** — ใช้ DDG/Qwant/Startpage |
| Mem0 | mem0ai package | ChromaDB collection "user_memory" |
| requirements.txt | ไม่มี upper bound | version range `>=x,<y` + lock file |
| Mold & Die domain | ไม่มี | Section 25 (Toshiba internship scope) |
| Gap analysis | ไม่มี | Section 26 (G-01–G-15 documented + patched) |

## Files changed 2026-05-09 (gap patches)
- `services/searxng/settings.yml` — disabled Google/Bing, enabled Qwant+Startpage
- `requirements.txt` — added llama-index, commented mem0ai, fixed duplicate markitdown
- `scripts/night_cycle.py` — added `_prevent_sleep()` / `_restore_sleep()` via ctypes

## User preferences (LEARNED — respect these)
- **Reply in Thai** for explanations, English-only for code/commands
- **Always offer A/B/C/D options** at decision points — don't just plow ahead
- **Brief responses** — tables and bullet points, not paragraphs
- **Commit-then-confirm-then-continue** rhythm (commit before moving to next phase)
- **Hate over-engineering** — defer fancy features until pain emerges
- **Asks "% done" frequently** — keep mental tally
- **No emojis in code/files** unless asked. Markdown emojis in chat replies are OK.
- **ASCII-only in CLI output** (Windows CMD = cp1252; em-dashes break the pipe)
- **Cite sources / show numbers** — user is engineering-trained, distrusts unverified claims
- **Before touching any file** — always read `.gitignore` first; never read/edit blacklisted folders (models/, chroma_db/, .venv/, __pycache__)
- **After editing** — report briefly what changed, don't re-print full code

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
10. Learning Together — educational mode (user is intern, wants to learn while doing)

## Known gotchas (do NOT re-learn these)
- **openkb / pageindex** → NOT on PyPI — use markitdown + llama-index (G-01 patch)
- **Brave Search API** → EOL'd Feb 2026 → use Tavily/Exa/SearXNG instead
- **Python 3.14** → bleeding edge, use 3.12 (chromadb etc. lack wheels)
- **Ollama Flash Attention** env var → must set BEFORE `ollama serve` starts
- **num_ctx 16384** → 7.2 GB VRAM (no swap room) → use 8192 for orchestrator
- **cl.Message + cl.Action in Chainlit** → buttons don't fire reliably → use cl.AskUserMessage
- **duckduckgo-search** package renamed to `ddgs` (mid-2025)
- **SearXNG + Google/Bing** → self-hosted gets IP-blocked in 1-3 days → disabled (G-10)
- **Vision model** → Qwen2.5-VL-7B + Orchestrator = 10 GB VRAM → OOM; use 3B default
- **Windows sleep** → Night Cycle dies if laptop sleeps → `_prevent_sleep()` already patched
- **Qwen3-Coder** → name may differ in Ollama registry → run `ollama search` before pull
- **LLM intent parser** confuses "ที่ถามไปกลับตอบมา" / "in Thai" as meta-talk → already fixed in INTENT_PARSER_SYSTEM
- **Wikipedia opensearch** returns wrong sister-articles for engineering codes → already fixed
- **OLLAMA_MODELS path** registry-set to `D:\OllamaModels` but real content at `D:\OllamaModels\models\` → start.sh/.bat auto-detects + appends `\models` (commit 46a6bdd, Bug #2)
- **parse_intent grammar-stuck sampling** Ollama 0.22.1 + json_schema + temp=0 + seed=42 occasionally hangs 3 min on certain prompts (e.g. "FMEA vs FTA ต่างกันยังไง") → temp=0.05 + timeout=60s in commit bbf100d (Bug #6 mitigation). Workaround for severe hang: stop.bat then start.bat
- **Worker-level egress** CONFIDENTIAL subjects routed to local workers used to bypass L3 egress check → classify() gate added at node_plan entry (commit 926c044, Bug #4)
- **OPENSSL_Uplink crash on Windows** intermittent crash after [init] log, before parse_intent → fixed by Windows reboot (Bug #7, recur risk: monitor and reboot if seen)
- **INTENT_PARSER_SYSTEM size** keep under 2000 chars (audit budget); current 1834 chars after shrink (commit 363dff2)

## Toshiba internship context (Mold & Die / washing machine)
- Internship domain: Injection Mold + Press Die สำหรับชิ้นส่วนเครื่องซักผ้า
- Key materials: SKD11, SKD61, S50C, P20, NAK80
- Key defects: Flash, Sink mark, Short shot, Warpage (injection) / Burr, Springback, Crack (press)
- Added Section 25 to plan: Mold & Die domain extension (knowledge base, tools, golden dataset M1–M4)
- Mini-project target: PM tracker + Mold shot counter + defect dashboard (Phase 3–4)
- New OSS tools planned: FreeCAD, ezdxf, Label Studio, qrcode, CalculiX (OpenFOAM deferred)

## Currently deferred (don't add unless asked)
- **Mem0 / Letta / Zep** → replaced by ChromaDB "user_memory" collection (simpler, no extra service)
- **Hermes-4-35B-A3B (MoE)** → 21 GB VRAM still OOM on 8 GB even with q8_0 cache
- **Real data ingest** → waits for Day 1 of Toshiba internship; using raw_data/_dummy/ for now
- **OpenFOAM** → CFD for cooling channel analysis; setup takes 3-7 days, out of intern scope
- **Activity Tracker Tier 3** → OS-level app tracking via PowerShell (active-win-listener ไม่รองรับ WSL2)
- **Microsoft Copilot escalation** → wired but never triggers (local works fine)
- **DSPy optimization** → Phase 5, after ≥1 month production use

## URGENT — pending ที่ค้างจาก session 2026-05-08
**Push commits ไป GitHub remote ยังไม่เสร็จ** — ทั้ง 2 repos ยังเป็น local-only:
1. main repo `D:\tpm_workspace`: 7 new commits since fa11046 handoff (latest: 926c044 Bug #4 fix)
2. `.tpm_context` repo: 4 new commits (latest: fa4f969 tool_watchlist + OfficeCLI eval)

User ต้อง: สร้าง 2 repos บน GitHub (`tpm-ai-framework` public + `tpm-knowledge-private` PRIVATE), แล้ว `git remote add origin` + `git push -u origin main` ที่ทั้ง 2 dirs. ขั้นตอนละเอียดมีในประวัติ chat ก่อนหน้า — AI ใหม่ ถามได้ถ้า user ลืม

## Recommended next steps (user picks — เรียงตาม "ก่อน internship เดือนหน้า")
- A) **Push commits to GitHub** (ก่อนสุด — backup baseline ก่อน feature ใหม่)
- B) **Phase 2 Day 3 Inquiry-First** — UX gain ชัด, ~30K tokens
- C) **Phase 3 Day 3 Calc worker** — SymPy integration (engineering grading point), ~50K
- D) **Phase 3 Day 4 Auditor 8-layer + CoVe** — accuracy boost, ~100K (ใหญ่ — เก็บไว้ทำกับ data จริง)
- E) **Phase 3 Day 5 Tool Registry + MCP** — swap workers runtime
- F) **Section 25 build-out** — MoldAnalyseNode + PM shot counter (Toshiba-specific)
- G) **Real testing more** — D2 24-prompt battery, multi-day night cycle
- H) **Phase 1 Day 1-3** — markitdown + llama-index (needs real docs from internship Day 1)

## Working style I prefer (please match)
- One coherent task per turn, then commit before next task
- Use TodoWrite for any task with > 3 steps
- ToolSearch before invoking deferred tools
- Run code in venv: `D:/tpm_workspace/.venv/Scripts/python.exe`
- Set `PYTHONIOENCODING=utf-8` for any script printing Thai
- Use bash for git/curl/cli, PowerShell only when bash chokes (process kill, scheduled tasks)
- Path canonical in code: `Path("/mnt/d/tpm_workspace")` (WSL2) — never hardcode Windows path

Now: read the docs above and ask what to work on. Do NOT start coding without my picking A/B/C/D/E/F/G/H.
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
├── MASTER_PLAN_v6.md            ← bible (5814 lines, 26 sections incl. Mold & Die + Gap Analysis)
├── MASTER_PLAN_v5.md            ← backup (ไม่ลบ)
├── HANDOFF_PROMPT.md            ← this file (updated 2026-05-09)
├── PHASE_0_NEXT_STEPS.md
├── README.md
├── app.py                        ← Chainlit entry
├── start.bat / stop.bat / start.sh / stop.sh
├── requirements.txt              ← v6.0: llama-index added, mem0 removed, bounds fixed
├── .env.example                  ← TAVILY_API_KEY, EXA_API_KEY, TPM_ORCHESTRATOR_MODEL
│
├── tpm_core/                     ← orchestrator + state + LLM wrapper + clarification
├── tpm_search/                   ← L3 search stack (6 providers + egress + router + quota)
├── tpm_workers/                  ← Report + Excel workers
├── tpm_night/                    ← session_store + replay + budget_audit + morning_brief
├── tpm_progress/                 ← weekly_progress.pptx generator
├── tpm_activity/                 ← manual activity log (JSONL, Tier 1+2 only)
├── tpm_ui/                       ← Chainlit bridge
│
├── scripts/
│   ├── cli_demo.py               ← interactive CLI
│   ├── health_check.py           ← startup verification
│   ├── thermal_guard.py          ← CPU/GPU temp monitor
│   ├── power_monitor.py          ← battery-aware scheduler
│   ├── night_cycle.py            ← [v6.0] + Windows sleep prevention (_prevent_sleep)
│   ├── setup_searxng.py
│   ├── setup_models.py           ← creates tpm-orch + tpm-scavenger
│   ├── benchmark_llm.py
│   ├── weekly_progress.py
│   ├── generate_dummy_data.py    ← 4 Japanese machines (SHIBAURA×2, MAKINO, SODICK)
│   └── CRON_SETUP.md
│
├── tests/
│   └── test_orchestrator_flow.py ← MockUI + 6 scenarios (no human in loop)
│
├── models/
│   ├── orchestrator/Modelfile    ← Qwen3-8B + 8K ctx
│   └── scavenger/Modelfile       ← Qwen3-1.7B + 16K ctx
│
├── services/
│   └── searxng/
│       ├── docker-compose.yml
│       └── settings.yml          ← [v6.0] Google/Bing DISABLED, Qwant+Startpage enabled
│
├── output/                       ← generated .docx, .xlsx, .pptx
│   ├── reports/                  ← maintenance reports (MAKINO, SHIBAURA, SODICK)
│   ├── excel/                    ← reliability metrics .xlsx
│   ├── pptx/
│   └── progress_reports/         ← weekly slides
│
├── raw_data/
│   └── _dummy/                   ← pre-internship test data (gitignored)
│       ├── DUMMY_Equipment_Specs.md
│       └── DUMMY_LOTO_Procedures.md
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
    └── wiki/                     ← markitdown+llama-index destination (empty until real docs)
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

**Generated:** 2026-05-08 (after Phase 4 Day 2 + Bug #2/4/6/7 batch fixes)
**Project state:** ~52% by plan / ~80% functional
**Plan version:** MASTER_PLAN_v6.md (26 sections)
**Last session highlights:**
- ✅ Phase 4 closed (Day 2 Activity Tracker — log_activity.py + 7-slide weekly deck)
- ✅ Bug #2 fixed: OLLAMA_MODELS path auto-correct in start.sh/.bat (commit 46a6bdd, verified live)
- ✅ Bug #4 fixed: worker-level egress gate at node_plan (commit 926c044, classify-verified offline)
- ✅ Bug #6 mitigated: parse_intent temp=0.05 + timeout=60s (commit bbf100d)
- ✅ Bug #7 fixed: OPENSSL_Uplink crash → Windows reboot resolved (4/4 PASS confirmed)
- ✅ INTENT_PARSER_SYSTEM shrunk 3657 → 1834 chars (commit 363dff2)
- ✅ test_battery.py soak runner (commit 261747a) — 10-prompt MockUI suite
- ✅ tool_watchlist.md added (.tpm_context) — OfficeCLI bookmarked for re-eval after internship Week 1
- ⚠️ Pending: GitHub push for both repos (no remote yet)
**Recommended next:** A (push to GitHub) → B (Phase 2 Day 3 Inquiry-First) → C (Phase 3 Day 3 Calc)
