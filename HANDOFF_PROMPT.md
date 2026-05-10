# 🔄 Handoff Prompt — TPM AI Project

> Copy ทั้ง block ข้างล่างนี้ ไปใส่ AI ตัวใหม่เป็น first message
> หรือบันทึกใน `CLAUDE.md` / project memory ก็ได้

---

```markdown
You are continuing work on the TPM AI Assistant project. Read the context below carefully, then ask me what to work on next.

## Project identity
- Name: TPM AI (Total Productive Maintenance assistant)
- Repo (main): `D:\tpm_workspace` → https://github.com/Noppadon69/tpm-ai-framework (PUBLIC, pushed 2026-05-10)
- Repo (private knowledge): `D:\tpm_workspace\.tpm_context` → https://github.com/Noppadon69/tpm-knowledge-private (PRIVATE — CONFIDENTIAL data, separate git repo)
- OS: Windows 11 + WSL2 + Git Bash + PowerShell available
- Maintainer: TPM intern — 4th-year Mechanical Engineering student (GitHub: Noppadon69)
- Goal: local-first LLM helper for maintenance reports/calc/lookups — built during Toshiba internship (Mold & Die / washing machine division), portable to senior project afterward
- Language: replies in Thai (mixed with English tech terms) — match the user's tone
- Date context: today is 2026-05-10 (or later); training cutoff differs

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
- **OPENSSL_Uplink crash on Windows (Bug #7)** — **root cause REVISED 2026-05-10** (deeper than originally documented): NOT a user-package issue. Crashes on bare `python -c 'import ssl; ssl.create_default_context()'` — bug is at **Python's stdlib `_ssl.pyd` level**, where the loaded OpenSSL DLL doesn't expose Applink that the calling .pyd expects. Likely cause: Windows DLL hijacking (Defender or other security agent pre-loads incompatible OpenSSL into process address space). **Reboot is band-aid only** — recurs every ~2-7 days. **Permanent fix = reinstall Python 3.12 from python.org official installer** (refreshes `_ssl.pyd` + bundled OpenSSL DLLs together). Confirmed NOT fixed by: cryptography downgrade 47→45 (still crashes), httpx avoidance (urllib stdlib also crashes), socket-only works fine. Conditional task: when Bug #7 recurs next time, do Python reinstall as Phase 0.5 priority. **NEW CHECKLIST:** if Bug #7 occurs → reboot to unblock immediate work → schedule Python reinstall ASAP. Diagnostic one-liner: `python -c "import ssl; ssl.create_default_context()"` → crashes if Bug #7 active.
- **INTENT_PARSER_SYSTEM size** keep under 2000 chars (audit budget); current 1834 chars after shrink (commit 363dff2)
- **gh CLI PATH after winget install** → existing PowerShell sessions don't see `gh` until restarted. One-line fix: `$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")` — or call full path `& "C:\Program Files\GitHub CLI\gh.exe"`. From Bash use `"/c/Program Files/GitHub CLI/gh.exe"`
- **NEVER paste PAT in chat** → GitHub Personal Access Tokens get logged in transcripts + Anthropic API + LLM context. If accidentally pasted → revoke immediately at https://github.com/settings/tokens. Use `gh auth login` → "Paste an authentication token" flow in LOCAL terminal (token never leaves machine). `.gh_token` / `*.token` / `gh_token*` already gitignored as defense (commit 239eccc)
- **winget install --silent** can hang for minutes silently → drop `--silent` to see progress, or fall back to direct MSI download from GitHub releases. msstore source has SSL cert issues — use `--source winget` to skip
- **gh repo create --push** pushes only the current branch (= main), NOT worktree branches (`claude/*`) → safe to use even when worktrees exist

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
- **docling / whisper.cpp / yt-dlp** → evaluated 2026-05-10, on `.tpm_context/tool_watchlist.md`. docling = Phase 1 A/B candidate vs markitdown (better tables/layout). whisper.cpp + yt-dlp = future video-knowledge pipeline (Phase 4.5+); whisper handles Thai+Japanese (Toshiba context). yt-dlp has TOS caveats — per-video consent only. **Combo:** yt-dlp → whisper.cpp → docling/markitdown → ChromaDB = video → searchable RAG.
- **huashu-design** (Claude Skill for HTML/PPTX/animation generation) → **NOW on watchlist** (commit d8c1c29 era). User pragmatic call 2026-05-10: green-light for intern personal use (2-month internship + Toshiba now Chinese-owned = low scrutiny). Wire as one of multiple slide options when Phase 3 Day 5 Tool Registry built. Senior project = free academic license.

## ✅ Recently resolved (session 2026-05-10)
**GitHub push complete** — ทั้ง 2 repos pushed สำเร็จ:
1. `tpm-ai-framework` PUBLIC — 11 commits pushed (รวม v6 bible, gap patches G-01/G-04/G-06/G-09, security gitignore)
2. `tpm-knowledge-private` PRIVATE — 8 commits pushed
3. gh CLI v2.92.0 ติดตั้งที่ `C:\Program Files\GitHub CLI\gh.exe`, auth via Windows keyring (Noppadon69)

**v6 gap patches ที่ค้างจาก session 2026-05-09 ตอนนี้ commit แล้ว:**
- `8f8c588` docs: add MASTER_PLAN_v6.md (5814 lines, 26 sections)
- `3deb406` chore(deps): G-01/G-06/G-09 (markitdown + llama-index, version bounds, mem0→chromadb)
- `83c191c` fix(night): G-04 prevent Windows sleep
- `8175712` chore(models): scaffold dirs (coder, embedding, vision, writer, heavy_*)
- `239eccc` chore(security): gitignore PAT/token files

## ✅ Spec session complete (session 2026-05-10)
**Consolidated spec landed in MASTER_PLAN_v6** (commit 867882e):
- § 15.7 Reflexion N-round Extension — extends existing § 15.2-15.4 from 1 round → N (not new system, refactor)
- § 15.8 Vision-RAG Cross-Check — independent verifier; 9 loopholes mapped + mitigated
- § 15.9 Updated schedule (when implemented) + § 15.9.1 CloakBrowser out-of-scope note
- `.tpm_context/tool_watchlist.md` — CloakBrowser SKIP entry (commit f7cb84b) with 5 alternatives + revisit gates

ทั้ง 2 spec มี: design questions answered (4 + 9), pseudocode, risks/mitigations, dependencies, acceptance criteria, implementation plan estimates (~15 hr + ~36 hr).

**Important:** Both clearly marked **NOT YET IMPLEMENTED**. Dependencies blocked on:
- Phase 1 Day 1 (real Toshiba data) — for meaningful failure mode reflection
- Phase 3 Day 2 (Vision worker) — § 15.8 needs Qwen2.5-VL-3B + Tesseract integration
- Phase 3 Day 4 (Auditor 8-layer + CoVe) — should be **re-scoped to BE the § 15.7 judge backend** (avoid building 2 separate judging systems)

## Recommended next steps (user picks — เรียงตาม "ก่อน internship เดือนหน้า")
- ~~A) Push commits to GitHub~~ ✅ DONE 2026-05-10 (11 main + 8 .tpm_context commits backed up)
- ~~A2) Spec session — Reflexion + Vision-RAG + CloakBrowser-watchlist~~ ✅ DONE 2026-05-10 (commits 867882e + f7cb84b)
- B) **Phase 2 Day 3 Inquiry-First** — UX gain ชัด, ~30K tokens. **เด่นสุด** ที่ทำได้ก่อน internship เพราะไม่รอ data จริง
- C) **Phase 3 Day 3 Calc worker** — SymPy integration (engineering grading point), ~50K
- D) **Phase 3 Day 4 Auditor 8-layer + CoVe** — **RE-SCOPED 2026-05-10**: Auditor ควรเป็น judge backend ของ § 15.7 Reflexion, ไม่ใช่ระบบแยก. ~80K (ลดจาก 100K เดิม)
- E) **Phase 3 Day 5 Tool Registry + MCP** — swap workers runtime
- F) **Section 25 build-out** — MoldAnalyseNode + PM shot counter (Toshiba-specific)
- G) **Real testing more** — D2 24-prompt battery, multi-day night cycle
- H) **Phase 1 Day 1-3** — markitdown + llama-index (needs real docs from internship Day 1; blocks § 15.8 Vision-RAG cross-check)
- I) **Update § 15.1 schedule** when § 15.7 + § 15.8 actually implemented (currently § 15.9 has the proposed updated schedule)

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
├── HANDOFF_PROMPT.md            ← this file (updated 2026-05-10)
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

**Generated:** 2026-05-10 (after GitHub push + security gitignore + spec session complete)
**Project state:** ~52% by plan / ~80% functional (no phase progress this session — focus was meta: backup + spec drafts)
**Plan version:** MASTER_PLAN_v6.md (26 top-level sections; § 15 expanded with 15.7 + 15.8 + 15.9 v6.1 spec drafts)
**Last session highlights (2026-05-10):**
- ✅ GitHub push complete — both repos backed up (no longer single-point-of-failure on local disk)
  - PUBLIC: https://github.com/Noppadon69/tpm-ai-framework (12 commits)
  - PRIVATE: https://github.com/Noppadon69/tpm-knowledge-private (9 commits)
- ✅ Committed 5 v6 gap patches that were dirty in working tree (8f8c588, 3deb406, 83c191c, 8175712 + .tpm_context 1f96d0b)
- ✅ Reverted MASTER_PLAN_v5.md to frozen backup (was accidentally modified with §25 mirror)
- ✅ Security: gitignore for `.gh_token`/`*.token`/`gh_token*` (commit 239eccc); workflow learning that PAT must NEVER be pasted in chat
- ✅ Bootstrap memory system at `C:\Users\Lenovo\.claude\projects\D--tpm-workspace\memory\` (6 files: index + user + 2× feedback + project + paths)
- ✅ Spec session complete: § 15.7 Reflexion N-round + § 15.8 Vision-RAG + § 15.9 schedule (commit 867882e, 333 lines); CloakBrowser SKIP entry to tool_watchlist (commit f7cb84b)
- ✅ Sanity check: health_check.py 8 OK / 0 FAIL — gap patches don't regress at env level
- ✅ Bug #7 deep-debugged — revised root cause (Python stdlib _ssl.pyd + DLL hijack), permanent fix = Python reinstall (deferred per user "ถ้าเกิดขึ้นอีกค่อยแก้")
- ⚠️ test_orchestrator_flow --fast NOT verified (blocked by Bug #7 recurrence) — reboot needed to unblock; gap patches presumed OK from health_check signal
- ⚠️ cryptography downgraded 47.0.0 → 45.0.7 in venv (~harmless cleanup; did NOT fix Bug #7)
- ⚠️ Security incident: user pasted PAT in chat → revoked + regenerated; lesson committed to gotchas list
**Recommended next:** B (Phase 2 Day 3 Inquiry-First, ~30K) → C (Phase 3 Day 3 Calc, ~50K) → D (Phase 3 Day 4 Auditor — re-scoped to BE judge for § 15.7)
**Conditional next (if Bug #7 recurs):** Phase 0.5 Python reinstall — agreed with user 2026-05-10 to defer permanent fix until next recurrence
