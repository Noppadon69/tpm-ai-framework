# Phase 0 — Next Steps สำหรับคุณ (User Actions)

> สิ่งที่ผม (AI) ทำให้แล้ว → ทุกไฟล์ config + scripts + git init เสร็จ
> สิ่งที่คุณต้องทำต่อ → ติดตั้ง Ollama + Python 3.11/3.12 + pull models + GitHub repos

---

## 🟢 สถานะปัจจุบัน (สิ่งที่ผมทำให้แล้ว)

```
✅ โครงสร้างโฟลเดอร์ครบตาม § 5.1 (60+ subdirs)
✅ Config files: AGENTS.md / SCHEMA.md / RUNBOOK.md / MIGRATION.md
✅ data_classification.yaml (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED)
✅ logger_consent.json (default = ทุกอันยังไม่ consent)
✅ tool_registry.json (empty — Phase 3 จะ populate)
✅ Safety scripts: thermal_guard / power_monitor / health_check
✅ Launchers: start.sh / stop.sh / start.bat / stop.bat
✅ requirements.txt (~50 OSS packages)
✅ .env.example
✅ README.md
✅ .gitignore (ปลอดภัย — ไม่ commit secrets/models/raw_data)
✅ Git repos init แล้ว 2 อัน:
   - tpm_workspace/.git/         (framework — public OK)
   - tpm_workspace/.tpm_context/.git/  (knowledge — private)
✅ commits แรกทั้ง 2 repos
✅ health_check.py ผ่าน syntax check
```

Health check สรุป:
```
OK=4   WARN=2   FAIL=1   SKIP=3
- WARN: Python 3.14 (bleeding edge), Docker daemon ไม่ run
- FAIL: Ollama ยังไม่ install
- SKIP: psutil/GPUtil/audit_chain (รอ pip install)
```

---

## 🔴 สิ่งที่คุณต้องทำต่อ (เรียงตามลำดับ)

### Step 1 — ติดตั้ง Python 3.11 หรือ 3.12 (ไม่ใช่ 3.14/3.15)

Python 3.14/3.15 **ใหม่เกินไป** — packages อย่าง chromadb, numpy, scipy บางทีไม่มี wheel ทำให้ pip install ช้ามากหรือพัง

**Option A — ติดตั้ง Python 3.12 native (แนะนำ):**
```
ดาวน์โหลด Python 3.12 จาก https://www.python.org/downloads/release/python-3128/
ตอน install: ✅ "Add Python to PATH"
ตอน install: ✅ "Install for all users"
จะได้ launcher py -3.12
```

**Option B — ใช้ uv (เร็วที่สุด, แนะนำที่สุด):**
```powershell
# Windows PowerShell (run as admin):
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# จากนั้นใน Git Bash หรือ PowerShell:
uv python install 3.12
```

### Step 2 — สร้าง venv + ติดตั้ง deps

```bash
cd D:/tpm_workspace

# ถ้าใช้ Python native:
py -3.12 -m venv venv
source venv/Scripts/activate          # Git Bash
# หรือ
venv\Scripts\activate.bat              # CMD
# หรือ
venv\Scripts\Activate.ps1              # PowerShell

# ถ้าใช้ uv (เร็วกว่า 10x):
uv venv --python 3.12
source .venv/Scripts/activate

# ติดตั้ง deps
pip install --upgrade pip
pip install -r requirements.txt
# หรือด้วย uv:
uv pip install -r requirements.txt
```

⚠️ บาง packages อาจ install ช้า/พัง — ถ้าเจอให้ skip ก่อน:
- `arize-phoenix` — optional Phase 4
- `playwright` — ต้องรัน `playwright install chromium` หลัง install
- `weasyprint` — ต้องการ GTK บน Windows (skip ได้ ใช้ reportlab แทน)
- `pageindex` / `openkb` — อาจไม่อยู่บน PyPI, ต้อง install จาก source (Phase 1)

### Step 3 — ติดตั้ง Ollama

```
ดาวน์โหลด Ollama for Windows: https://ollama.com/download/windows
ติดตั้งปกติ → restart terminal
ตรวจ: ollama --version
```

### Step 4 — Pull core models (ใช้ disk ~6 GB)

```bash
ollama pull qwen3:8b-instruct-q4_K_M
ollama pull qwen3:1.7b-instruct-q4_K_M
ollama pull bge-m3
```

⚠️ ถ้า Ollama ยังไม่มี Qwen3 (อาจ release หลังจากที่แผนเขียน) ให้ใช้ fallback:
```bash
ollama pull qwen2.5:7b-instruct-q4_K_M
ollama pull qwen2.5:1.5b-instruct-q4_K_M
ollama pull bge-m3
```

ทดสอบ:
```bash
ollama run qwen3:8b "สวัสดี ทำงานได้ไหม?"
# ควรตอบเป็นภาษาไทย
```

### Step 5 — สร้าง GitHub repos (private) สำหรับ backup

ติดตั้ง gh CLI ก่อน: https://cli.github.com/

```bash
gh auth login        # browser flow

# Repo 1: framework (โค้ด — public OK ถ้าจะแชร์)
gh repo create tpm-ai-framework --private --description "TPM AI assistant framework"
git -C D:/tpm_workspace remote add origin <URL ที่ gh ให้>
git -C D:/tpm_workspace push -u origin main

# Repo 2: knowledge (private บังคับ — มี wiki/skills/anti-patterns)
gh repo create tpm-knowledge-private --private --description "TPM AI knowledge backup"
git -C D:/tpm_workspace/.tpm_context remote add origin <URL>
git -C D:/tpm_workspace/.tpm_context push -u origin main
```

ใส่ URL ใน .env:
```
KNOWLEDGE_REPO_REMOTE=git@github.com:YOU/tpm-knowledge-private.git
FRAMEWORK_REPO_REMOTE=git@github.com:YOU/tpm-ai-framework.git
```

### Step 6 — Setup .env

```bash
cp .env.example .env
```

แก้ `.env` ใส่ API keys (เรียงตาม priority):

```yaml
must_have:
  - TAVILY_API_KEY    # สมัครฟรีที่ https://tavily.com (1,000/mo)

recommended:
  - EXA_API_KEY       # สมัครฟรีที่ https://dashboard.exa.ai (1,000/mo)
                      # OR ข้ามแล้วใช้ MCP OAuth:
                      # claude mcp add --transport http exa https://mcp.exa.ai/mcp

phase_1_later:
  - SEARXNG_URL       # default localhost:8888 — Docker compose ใน Phase 1

phase_3_later:
  - MS_TENANT_ID, MS_CLIENT_ID, MS_CLIENT_SECRET   # Microsoft Copilot
  - AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT       # Azure OpenAI fallback

dropped:
  - ❌ BRAVE_API_KEY  # Brave EOL'd free tier ก.พ. 2026 — ไม่ใช้แล้ว
```

**ไม่ต้องสมัคร** (ใช้ฟรี ไม่มี key):
- DuckDuckGo Instant Answer (`duckduckgo-search` package)
- Wikipedia REST (`wikipedia-api` package)
- Jina Reader (`https://r.jina.ai/<url>`)

### Step 7 — Re-run health_check

```bash
cd D:/tpm_workspace
python scripts/health_check.py
```

เป้าหมาย: `OK >= 8, FAIL = 0` (WARN ที่เหลือเป็น Phase 1+ ไม่ block)

### Step 8 — Test runs

```bash
# Test thermal_guard (one-shot)
python scripts/thermal_guard.py --check

# Test power_monitor (one-shot)
python scripts/power_monitor.py --check

# Test start (จะ launch daemons + ollama)
bash start.sh         # Git Bash
# หรือ
start.bat             # CMD/PowerShell

# Test stop
bash stop.sh
```

---

## ✅ Acceptance Criteria สำหรับจบ Phase 0

ตาม § 22.2.2 ของ MASTER_PLAN_v5.md:

- [ ] `python scripts/health_check.py` → exit code 0 (ไม่มี FAIL)
- [ ] VRAM idle (orchestrator + scavenger loaded) ≤ 6.5 GB → ทดสอบด้วย `nvidia-smi`
- [ ] thermal_guard pause heavy task เมื่อ CPU > 80°C → manual stress test
- [ ] power_monitor switch mode เมื่อถอดปลั๊ก → ถอดปลั๊กดู
- [ ] LangGraph checkpoint save ทุก 30s → จะทดสอบใน Phase 2
- [ ] GitHub auto-commit ทำงาน → manual trigger `python scripts/github_backup.py` (Phase 1 จะเขียน)

---

## 🐛 Common Issues + Fixes

### "pip install ช้ามาก/ค้าง"
- ใช้ uv แทน: `uv pip install -r requirements.txt` (เร็วกว่า 10x)
- หรือ `pip install -r requirements.txt --no-cache-dir --prefer-binary`

### "ChromaDB install fail"
- ปกติ Python 3.14 ไม่มี wheel — ลด เป็น 3.12
- หรือ skip Phase 0: comment chromadb ใน requirements.txt → install ใน Phase 1

### "Ollama serve ช้า / ไม่ตอบ"
- ตรวจ port 11434: `netstat -an | findstr 11434`
- restart Ollama service
- ถ้าใช้ WSL2 + Windows Ollama: ตั้ง `OLLAMA_HOST=http://172.x.x.1:11434` (IP gateway WSL)

### "git push ช้า / fail"
- ใช้ SSH key แทน HTTPS: `gh auth refresh -s admin:public_key`
- หรือ HTTPS + token ใน Git Credential Manager

### "Python 3.14 พังเยอะ"
- กลับไปใช้ 3.12 — uv ทำให้ติดตั้ง Python ใหม่เร็วมาก:
  ```
  uv python install 3.12
  uv venv --python 3.12
  ```

---

## 📋 เมื่อเสร็จ Phase 0 → ถัดไป

ถ้า health_check ผ่าน + Ollama ตอบได้ + git push ขึ้น GitHub แล้ว → **Phase 1: Knowledge 3-Layer**

ดู § 22.3 ของ MASTER_PLAN_v5.md:
1. วางเอกสาร PDF/Excel ใน `raw_data/`
2. ติดตั้ง OpenKB + PageIndex
3. รัน `openkb compile` ครั้งแรก (กลางคืน 2-8 ชม.)
4. ติดตั้ง Obsidian → Open `.tpm_context/wiki/` as vault
5. Setup ChromaDB (Layer 2)
6. Setup SearXNG ผ่าน Docker (Layer 3 primary)
7. สมัคร Brave + Tavily free tier

---

**Generated:** 2026-05-01
**ref:** MASTER_PLAN_v5.md § 22.2 (Phase 0)
