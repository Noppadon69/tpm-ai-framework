# TPM AI — The Open-Source Sentinel

> ผู้ช่วยวิศวกรซ่อมบำรุง (Total Productive Maintenance) ที่รันบน laptop
> ขับเคลื่อนด้วย LangGraph + ทีม local LLM (Qwen3-8B + Qwen3-1.7B + Vision/Coder swap)
> Open-source first · Free tier · Portable · GitHub backup

---

## 60-Second Overview

```
[Input: PDF/Excel/Image/Prompt]
        ↓
[Clarification] ← "คุณหมายถึง... ใช่ไหม?"
        ↓
[Inquiry-First] ← ขาดข้อมูล? ถาม user ก่อน → ค้นถ้าไม่รู้
        ↓
[Recon: Wiki → ChromaDB → SearXNG/Brave/Tavily]
        ↓
[Workers: Report / Excel / PPTX / Vision / Calc]
        ↓
[Auditor: 8-layer + CoVe verify]
        ↓
[Human Gate: Diff View + Approve]
        ↓
[Output + Decision Log + Audit Trail]

ทุกคืน: replay งานวันนี้ → ตรวจ → แก้ตัวเอง → morning brief
```

---

## หลักเหล็ก 10 ข้อ

1. **Open-Source First** — ทุก capability หา OSS ก่อน
2. **Tool > AI** — ไม่ให้ AI คิดเลข ใช้ SymPy/numpy
3. **Ask Before Search** — ถาม user ก่อนค้น web
4. **Confirm Before Act** — clarify intent ก่อนเริ่ม
5. **Explain Everything** — what / why this / why not / what failed
6. **Night Self-Check** — replay + diagnose + fix ทุกคืน
7. **VRAM ≤ 7 GB** — ตลอดเวลา (1 GB headroom)
8. **Free or Cheap** — free tier ก่อน
9. **Portable Knowledge** — ย้ายโปรเจคต่อไปได้
10. **Learning Together** — educational mode

---

## Hardware

```
Laptop:  Lenovo Legion 5
RAM:     32 GB DDR5
GPU:     NVIDIA RTX 5060 Laptop (8 GB GDDR7)
OS:      Windows 11 + WSL2 (Ubuntu 24)
```

ห้ามซื้อฮาร์ดแวร์เพิ่ม — ใช้ software solution (thermal_guard, power_monitor, GitHub backup)

---

## Quick Start

### Phase 0 setup (one-time)

```bash
# 1. Install Ollama (Windows or WSL2)
#    https://ollama.com/download

# 2. Pull core models (~6 GB total)
ollama pull qwen3:8b-instruct-q4_K_M
ollama pull qwen3:1.7b-instruct-q4_K_M
ollama pull bge-m3

# 3. Create Python 3.11 venv (avoid 3.14 — packages may lack wheels)
python3.11 -m venv venv
source venv/bin/activate     # Linux/WSL
# venv\Scripts\activate.bat  # Windows

# 4. Install deps
pip install -r requirements.txt

# 5. Copy env template
cp .env.example .env
# edit .env to add API keys (optional in Phase 0)

# 6. Health check
python scripts/health_check.py
```

### Daily usage

```bash
# Start
bash start.sh           # WSL/Linux
start.bat               # Windows native

# Open Chainlit UI (Phase 4+)
# http://localhost:8000

# Stop
bash stop.sh            # or stop.bat
```

---

## Folder Structure

```
tpm_workspace/
├── raw_data/               # input: PDF, Excel, images
├── .tpm_context/           # the brain (knowledge + skills + logs)
│   ├── AGENTS.md           # constitution
│   ├── SCHEMA.md           # wiki structure
│   ├── RUNBOOK.md          # user guide
│   ├── data_classification.yaml
│   ├── domain_knowledge/   # FMEA, RCM, KPI, TRIZ
│   ├── wiki/               # OpenKB-compiled
│   ├── skills/             # workflow templates
│   ├── anti_patterns/      # lessons learned
│   ├── local_tools/        # OSS-first tools
│   ├── prompts/            # versioned
│   ├── activity_log/       # 3-tier tracking
│   ├── decision_log/       # explanation trail
│   └── night_cycle/        # self-correction
├── chroma_db/              # Layer 2 vector cache
├── models/                 # GGUF files (~40 GB)
├── services/               # Docker (SearXNG, Langfuse, Phoenix)
├── scripts/                # safety nets + helpers
├── output/                 # final reports
├── logs/                   # rotated
└── tests/golden_dataset/   # regression
```

---

## Documentation

- **MASTER_PLAN_v5.md** — full architecture (~5,000 lines)
- **.tpm_context/AGENTS.md** — agent constitution + thinking protocol
- **.tpm_context/SCHEMA.md** — wiki structure
- **.tpm_context/RUNBOOK.md** — daily operations + emergency

---

## Status

```yaml
phase: 0           # Workspace + Models + Safety Nets
date: 2026-05-01
ready: false       # need to install Ollama + venv + pull models
```

ดู `.tpm_context/RUNBOOK.md` § 1 สำหรับ daily operations

---

## License

MIT — framework code
Knowledge repo (`.tpm_context/`) is private (separate repo)
