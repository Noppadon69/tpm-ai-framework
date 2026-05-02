# TPM AI MASTER PLAN v5.0
## "The Open-Source Sentinel" — แผนที่จะรันได้จริงและโตไปกับคุณ

> เอกสารนี้ออกแบบมาให้ป้อนเข้า AI ตัวอื่นได้ทันที (Claude, ChatGPT, Gemini, local LLM)
> โดยไม่ต้องอ่าน v4.0 ก่อน — self-contained ทุกอย่างอยู่ในไฟล์นี้
>
> **เวอร์ชัน:** 5.0 | **วันที่:** 1 พฤษภาคม 2026 | **สถานะ:** พร้อมเริ่ม Phase 0
> **เปลี่ยนจาก v4.0:** แก้ช่องโหว่ P0 ทั้ง 6 จุด + เพิ่ม 7 ระบบใหม่

---

## 📑 สารบัญ

1. [Executive Summary](#1-executive-summary)
2. [วิสัยทัศน์และหลักการพื้นฐาน](#2-วิสัยทัศน์และหลักการพื้นฐาน)
3. [Hardware Reality (ไม่ซื้อเพิ่ม)](#3-hardware-reality)
4. [ทีม AI (Revised Model Lineup)](#4-ทีม-ai-revised-model-lineup)
5. [โครงสร้างโฟลเดอร์ทั้งระบบ](#5-โครงสร้างโฟลเดอร์)
6. [ระบบ Knowledge 3 ชั้น (พร้อม search ฟรี)](#6-ระบบ-knowledge-3-ชั้น)
7. [🆕 Prompt Clarification System (ก่อนเริ่มงาน)](#7-prompt-clarification-system)
8. [🆕 Inquiry-First Pattern (ถามก่อนค้น)](#8-inquiry-first-pattern)
9. [Engineering Mind Protocol](#9-engineering-mind-protocol)
10. [Pipeline หลัก — LangGraph Architecture](#10-pipeline-หลัก)
11. [Worker Subgraphs](#11-worker-subgraphs)
12. [Auditor + Quality Control](#12-auditor--quality-control)
13. [🆕 Tool Registry & Auto-Discovery](#13-tool-registry--auto-discovery)
14. [🆕 Activity Tracking (ในและนอก AI)](#14-activity-tracking)
15. [🆕 Night Cycle (Self-Correction)](#15-night-cycle-self-correction)
16. [🆕 Explanation & Transparency System](#16-explanation--transparency-system)
17. [🆕 Open-Source First Catalog](#17-open-source-first-catalog)
18. [Microsoft Copilot Integration](#18-microsoft-copilot-integration)
19. [🆕 Portable AI Team (สำหรับโปรเจคต่อไป)](#19-portable-ai-team)
20. [🆕 GitHub Backup Strategy](#20-github-backup-strategy)
21. [Security & Selective Egress](#21-security--selective-egress)
22. [Implementation Phases (ค่อยๆ ทำ)](#22-implementation-phases)
23. [Risk Register](#23-risk-register)
24. [Quick Reference สำหรับ AI ที่จะอ่านต่อ](#24-quick-reference)

---

# 1. Executive Summary

## 1.1 ระบบนี้คืออะไร

ผู้ช่วยวิศวกรซ่อมบำรุง (TPM = Total Productive Maintenance) ที่ขับเคลื่อนด้วย LangGraph + ทีม Local LLM บน laptop โดยมี 4 หน้าที่หลัก:

1. **อ่านเอกสารวิศวกรรม** (PDF, Excel, รูปภาพรอยร้าว) → สรุป + วิเคราะห์
2. **เขียนรายงาน + สไลด์** ตาม template มาตรฐาน TPM
3. **เรียนรู้จากคุณ** — สังเกตว่าคุณทำอะไรบ่อย → สร้าง tool ให้กดปุ่มเดียวรันได้
4. **ตรวจตัวเองตอนกลางคืน** — replay งานวันนี้ ดูว่าผิดไหม → แก้ไขก่อนเช้า

## 1.2 อะไรเปลี่ยนจาก v4.0

| ประเด็น | v4.0 | v5.0 |
|---|---|---|
| Orchestrator | Hermes 4 35B A3B (ใช้ VRAM 22 GB ❌) | **Qwen3-8B + Hermes-3-8B (5 GB ✓)** |
| Search L3 | Perplexity ($5/1k) | **SearXNG ฟรีไม่จำกัด → Tavily 1000 ฟรี/เดือน** |
| Enterprise API | "Enterprise/Corporate API" (ไม่ระบุ) | **Microsoft Copilot Student (ฟรี) + Azure OpenAI fallback** |
| ก่อนเริ่มงาน | รับ prompt → run ทันที | **🆕 Clarification: "คุณหมายถึง... ใช่ไหม?"** |
| ขาดข้อมูล | ค้นทันที | **🆕 ถามผู้ใช้ก่อน → ค้นถ้าไม่ได้** |
| Night Routine | Auto-Dev เฉยๆ | **🆕 Replay all daytime tasks → ตรวจ + แก้ตัวเอง** |
| Tracking | passive_logger ใน workspace | **🆕 Tracking + นอก workspace (เมื่อไม่ได้ใช้ AI)** |
| Tool | AI สร้างเอง | **🆕 Open-source first → AI สร้างเองเป็นทางสุดท้าย** |
| Explanation | บางครั้ง | **🆕 ทุกครั้ง — explain ทำอะไร เลือกอะไร อะไรพังบ้าง** |
| Hardware | แนะให้ซื้อ UPS | **❌ ไม่ซื้อ — ใช้ software solution แทน** |
| Backup | external HDD encrypted | **GitHub repo (ฟรี) — ไม่ต้องซื้อ HDD** |

## 1.3 สรุปกฎเหล็ก 10 ข้อ

```yaml
core_rules:
  1. "Open-Source First" : ทุก capability หา open-source tool ก่อน เขียนโค้ดเองเป็นทางสุดท้าย
  2. "Tool > AI"          : ถ้ามี library/tool ที่ทำได้ดีอยู่แล้ว → ใช้ tool ไม่ใช้ AI
  3. "Ask Before Search"  : ถาม user ก่อน → ค้นถ้า user ไม่รู้
  4. "Confirm Before Act" : ทุก prompt → AI ถาม "คุณหมายถึง..." ก่อนเริ่ม
  5. "Explain Everything" : ทุก decision มี "ทำอะไร / เลือกอะไร / ไม่เลือกอะไร / เพราะอะไร"
  6. "Night Self-Check"   : ทุกคืน replay งานวันนี้ → หา error → propose fix
  7. "VRAM Budget Locked" : รวมแล้ว ≤ 7 GB ตลอดเวลา (เหลือ 1 GB headroom)
  8. "Free or Cheap"      : ใช้ free tier ทุก service ก่อน → จ่ายต่อเมื่อจำเป็น
  9. "Portable Knowledge" : Wiki + Skills + Tools ย้ายไปโปรเจคต่อไปได้ทั้งหมด
  10. "Learning Together"  : ระบบอธิบายให้ user เรียนรู้ไปด้วย (educational mode)
```

---

# 2. วิสัยทัศน์และหลักการพื้นฐาน

## 2.1 ปัญหาที่กำลังแก้

วิศวกร TPM เผชิญ 4 ปัญหาทุกวัน:

1. **ข้อมูลกระจัดกระจาย** — คู่มือ PDF, Excel log, ระบบ ERP, ภาพถ่าย, มาตรฐาน ISO ทั้งหมดไม่เชื่อมกัน
2. **งานเอกสารกินเวลา** — รายงาน maintenance, สไลด์ progress, work order ใช้เวลามากกว่างานจริง
3. **ความรู้ไม่ส่งต่อ** — คนเก่าออก = ความรู้หายไปด้วย
4. **AI generic ไม่เข้าใจ context** — ChatGPT/Claude ทำงานทั่วไปได้ แต่ไม่รู้ภาษา TPM, ไม่อ่านคู่มือเครื่องของเรา, ไม่อ่านภาษาไทย/อังกฤษผสม

## 2.2 5 หลักการที่ขับเคลื่อนทุกการตัดสินใจ

### 🔵 หลักที่ 1: Open-Source First (ย้ำที่สุด)

```
Sequence ของการตัดสินใจเมื่อต้องการ capability ใหม่:

1. มี open-source library / tool ที่ทำได้แล้วไหม?  → ใช้ทันที
2. มี open-source service ที่ self-host ได้ไหม?    → setup self-host
3. มี free API tier ที่พอใช้ไหม?                   → ใช้ free tier
4. ต้องเขียนเองจริงๆ?                              → AI ช่วยร่าง → human review → bandit scan
```

**เหตุผล:**
- โค้ดที่ AI สร้างเองมี bug rate สูงกว่า ~3-5x
- Open-source มี community fix bug ให้ฟรี
- ลด maintenance burden — ไม่ต้องดูแลโค้ดเอง

### 🟢 หลักที่ 2: Tool > AI

```python
# ❌ Don't do this:
result = llm.generate("คำนวณ stress = F/A เมื่อ F=1000N, A=0.05m²")

# ✅ Do this:
import sympy
F, A = sympy.symbols('F A')
stress_eq = F / A
result = stress_eq.subs({F: 1000, A: 0.05})
```

**เหตุผล:**
- Tool ผลถูกต้อง 100% (deterministic)
- AI ผลผิด 5-20% ในงาน arithmetic
- Tool เร็วกว่า AI 100-1000x
- Tool reproducible — ใช้กี่ครั้งก็ได้ผลเดิม

**กฎ:** AI **ห้ามคิดเลขเอง** — ทุกตัวเลขต้องผ่าน Python/SymPy/library

### 🟡 หลักที่ 3: Ask Before Acting

ก่อน AI **ทำอะไร** (ค้น, เรียก tool, เขียนรายงาน) ต้องผ่าน 2 ด่าน:

1. **Clarification** — "คุณหมายถึง [การตีความของฉัน] ใช่ไหม?"
2. **Inquiry-First** — ถ้าขาดข้อมูล → ถาม user ก่อน → ค้น web เป็นทางสุดท้าย

**เหตุผล:**
- ป้องกัน AI ทำงานผิดทิศทาง (ประหยัดเวลา + token)
- ป้องกัน hallucination จากข้อมูลที่ AI "เดาเอง"
- ทำให้ user มีส่วนร่วม → output ตรงใจมากขึ้น

### 🟠 หลักที่ 4: Self-Correction at Night

ทุกคืน 23:00–05:00 ระบบ:

1. **Replay** ทุก task ของวันนี้ด้วย model ใหญ่กว่า (ที่ run ช้าได้เพราะกลางคืน)
2. **Compare** ผลกับ output จริง — หาความแตกต่าง
3. **Diagnose** ทำไมต่างกัน (model bug? data missing? prompt อ่อน?)
4. **Propose fix** — แก้ prompt, เพิ่ม anti-pattern, สร้าง tool ใหม่
5. **Morning brief** — เช้ามาเห็นรายการ "เรื่องที่อยากให้คุณ approve"

**เหตุผล:**
- กลางวัน: เร็ว = ดี (ผู้ใช้รอ)
- กลางคืน: ลึก = ดี (ไม่มีใครรอ ใช้ model 2-3x ใหญ่กว่าได้)
- ระบบโตขึ้นทุกวันโดยไม่รบกวนงานหลัก

### 🟣 หลักที่ 5: Educational Transparency

ทุก decision ของ AI ต้องอธิบายได้ใน 4 มุม:

1. **What** — ทำอะไรบ้าง (steps + tools used)
2. **Why this** — เลือกแนวทางนี้เพราะอะไร
3. **Why not that** — ทำไม**ไม่**เลือกแนวทางอื่น
4. **What failed** — ลองอะไรแล้วไม่ได้ผล + เพราะอะไร

**เหตุผล:**
- User เป็นนักศึกษาฝึกงาน → อยาก**เรียน**ไปด้วย
- ใช้เป็น material สำหรับรายงาน/สไลด์ progress
- ทำให้ trust AI ขึ้น (เห็น reasoning)
- อนาคต: user สามารถทำเองได้โดยไม่พึ่ง AI

## 2.3 หลัก "ไม่" ที่บังคับ

ห้ามทำเด็ดขาด:
- ❌ ใช้ AI คำนวณตัวเลขโดยไม่ผ่าน library
- ❌ เริ่มงานโดยไม่ confirm intent ก่อน
- ❌ ค้น web ก่อนถาม user
- ❌ Reject งานโดยไม่อธิบายว่าทำไม
- ❌ Approve งาน safety-critical โดยไม่มี Human Gate
- ❌ ส่งข้อมูล CONFIDENTIAL ออก external API
- ❌ เขียนโค้ดใหม่ก่อนเช็คว่ามี library ที่ทำได้แล้วไหม

---

# 3. Hardware Reality (ไม่ซื้อเพิ่ม)

## 3.1 ฮาร์ดแวร์ที่มี

```yaml
laptop: Lenovo Legion 5
RAM: 32 GB DDR5
GPU: NVIDIA RTX 5060 Laptop
VRAM: 8 GB GDDR7
iGPU: AMD Radeon 780M (ไม่ใช้สำหรับ AI)
OS: Windows 11 + WSL2 (Ubuntu 24)
storage: ใช้ที่มี (ระบบประมาณ ≥100 GB)
```

## 3.2 ทำไม v4.0 ใช้ไม่ได้กับ hardware นี้

แผน v4.0 บอกให้ใช้ **Hermes 4 35B A3B Q4_K_M** เป็น orchestrator โดยอ้างว่าใช้ VRAM แค่ 5.5 GB

**ความจริง (ตรวจสอบจาก HuggingFace + Unsloth + benchmark เม.ย. 2026):**

> Hermes 4 35B A3B Q4_K_M ใช้ VRAM ~22 GB
> เพราะ MoE architecture ต้องโหลด **ทุก expert** เข้า memory พร้อมกัน
> "MoE saves COMPUTE, not MEMORY" — ที่บันทึกคือเวลา ไม่ใช่ VRAM

→ 22 GB VRAM ขั้นต่ำที่ Q4_K_M, 32 GB ที่ Q8_0 ซึ่งเกินกว่า RTX 5060 Laptop 8 GB ทำได้ทาง physical

## 3.3 Strategy ใหม่ (ไม่ต้องซื้อฮาร์ดแวร์)

### กฎ VRAM Budget (≤ 7 GB ตลอดเวลา, เหลือ headroom 1 GB)

| State | สิ่งที่อยู่ใน VRAM | VRAM ใช้ | VRAM เหลือ |
|---|---|---|---|
| Idle | OS + Orchestrator (Qwen3-8B) + Scavenger (Qwen3-1.7B) | ~6 GB | ~2 GB |
| + Vision swap | Unload Scavenger → load Qwen2.5-VL-7B | ~7 GB | ~1 GB |
| + Coder swap | Unload Vision → load Qwen3-Coder-8B | ~6 GB | ~2 GB |
| + Heavy on CPU | Hermes 35B/Qwen 27B รันบน RAM 32GB | ~6 GB GPU + 22 GB RAM | ~2 GB GPU + 10 GB RAM |

**กฎ Swap:** มีแค่ 3 slots — **lockable orchestrator + lockable scavenger + 1 swappable**

### Power Management (แทนการซื้อ UPS)

```python
# software-only power monitoring
import psutil

def power_aware_scheduling():
    battery = psutil.sensors_battery()
    if battery is None:
        return "desktop_mode"

    if not battery.power_plugged:
        # ทำงานบน battery
        if battery.percent > 50:
            return "normal_mode"
        elif battery.percent > 20:
            return "conservative_mode"  # หยุด night cycle, postpone heavy
        elif battery.percent > 10:
            return "emergency_mode"     # checkpoint everything, ready to shutdown
        else:
            return "shutdown_now"       # graceful shutdown ก่อนไฟดับ
```

**กฎ:**
- ทุก node Save state ทุก 30 วินาที (LangGraph checkpoint)
- ถ้าเครื่องดับกลางคันจริงๆ → resume จาก checkpoint ล่าสุด (เสียงานไม่เกิน 30 วิ)
- Night cycle รันต่อเมื่อ "ปลั๊กไฟเสียบอยู่" เท่านั้น

### Storage Management (แทนการซื้อ external HDD)

```yaml
storage_strategy:
  total_required: ~80 GB

  breakdown:
    models: ~40 GB (8 models × 5 GB เฉลี่ย)
    knowledge_base: ~10 GB (wiki + raw_data)
    vector_db: ~3 GB (ChromaDB)
    checkpoints: ~5 GB (rotated)
    logs: ~3 GB (rotated)
    output: ~5 GB
    cache: ~5 GB
    buffer: ~10 GB

  cleanup_schedule:
    daily: rotate logs, clean cache
    weekly: archive old checkpoints
    monthly: review wiki for stale content

  backup: GitHub (ฟรี — ดู Section 20)
```

## 3.4 Thermal Management (สำคัญมากบน laptop)

```python
# /home/claude/scripts/thermal_guard.py
import psutil
import time
import GPUtil

THRESHOLDS = {
    "cpu_warn": 75,      # °C
    "cpu_throttle": 80,
    "cpu_critical": 85,
    "gpu_warn": 75,
    "gpu_throttle": 82,
    "gpu_critical": 87,
}

def monitor_temps():
    while True:
        cpu_temp = psutil.sensors_temperatures().get('coretemp', [{}])[0].get('current', 0)
        gpu_temp = GPUtil.getGPUs()[0].temperature

        if cpu_temp > THRESHOLDS["cpu_critical"] or gpu_temp > THRESHOLDS["gpu_critical"]:
            pause_all_heavy_tasks()
            notify("🔥 อุณหภูมิสูงผิดปกติ — หยุดงานหนักทันที กรุณาพักเครื่อง 5 นาที")
            wait_until_cool()
        elif cpu_temp > THRESHOLDS["cpu_throttle"] or gpu_temp > THRESHOLDS["gpu_throttle"]:
            slow_down_tasks(factor=0.5)
        elif cpu_temp > THRESHOLDS["cpu_warn"] or gpu_temp > THRESHOLDS["gpu_warn"]:
            log_warning(cpu_temp, gpu_temp)

        time.sleep(10)
```

**กฎ:** Heavy task (model swap, OpenKB compile) เริ่มได้เมื่อ CPU < 70°C เท่านั้น


---

# 4. ทีม AI (Revised Model Lineup)

## 4.1 หลักการเลือก Model

```yaml
selection_criteria:
  must_haves:
    - GGUF Q4_K_M format (compatible with llama.cpp + Ollama)
    - Apache 2.0 / MIT license (ใช้ commercial ได้)
    - VRAM fit ที่ Q4_K_M ≤ 6 GB หรือ run บน CPU/RAM ได้
    - มี community ที่ active (Bug fixes มาเรื่อยๆ)

  nice_to_haves:
    - Tool calling support (สำหรับ orchestrator)
    - Multilingual ดีโดยเฉพาะภาษาไทย
    - Long context (≥ 32K)
    - Thinking mode / chain-of-thought
```

## 4.2 ทีมหลัก (Core Team) — ติดตั้งใน Phase 0

### 🔴 1. Orchestrator (Locked in VRAM)

**ตัวเลือก A — Conservative (แนะนำเริ่มต้นด้วย):**
```bash
ollama pull qwen3:8b-instruct-q4_K_M
# หรือ
huggingface-cli download Qwen/Qwen3-8B-Instruct-GGUF \
  --include "Qwen3-8B-Instruct-Q4_K_M.gguf" \
  --local-dir ./models/orchestrator
```
- VRAM: ~5 GB Q4_K_M
- Speed: 30-55 tok/s บน RTX 5060
- Tool calling: ดี (ใหม่กว่า Qwen2.5)
- ภาษาไทย: ดี
- License: Apache 2.0

**ตัวเลือก B — Uncensored (สำหรับงานวิศวกรรมไม่มี false refusal):**
```bash
ollama pull huihui_ai/qwen3-abliterated:8b-q4_K_M
```
- บางครั้ง Qwen3 จะ refuse คำถามเกี่ยวกับ chemical, explosion (แม้เป็นบริบทวิศวกรรม legitimate)
- Abliterated version: refuse น้อยลง 90%
- **ระวัง:** ใช้ใน controlled environment เท่านั้น — มี Auditor ตรวจ output ก่อน user เห็น
- **เหตุผลที่อาจต้องการ:** maintenance ของระบบที่มี hazardous material เช่น H2S, NH3, ก๊าซระเบิด — model ปกติบางครั้งไม่ตอบ

**ตัวเลือก C — Hermes 3 8B (ดีสำหรับ tool calling จัดๆ):**
```bash
ollama pull hermes3:8b-llama3.1-q4_K_M
```
- เทรนพิเศษบน agent traces — tool calling ไม่หลุดหลัง 100+ steps
- VRAM: ~5 GB
- **trade-off:** ภาษาไทยอ่อนกว่า Qwen3

**บทบาท:**
- รับคำสั่งจาก user
- Clarification + Inquiry-First ก่อนเริ่ม
- แบ่ง task → ส่งให้ workers
- รวมผล → ส่ง Auditor → Human Gate
- Tool selection จาก registry

### 🔴 2. Scavenger (Locked in VRAM)

```bash
ollama pull qwen3:1.7b-instruct-q4_K_M
```
- VRAM: ~1 GB
- Speed: 80-120 tok/s
- บทบาท: SQL query, RAG retrieval, web scraping cleanup, file metadata

**ทำไมต้องล็อกใน VRAM?**
- ใช้บ่อยมาก (ทุก task เกือบ)
- โหลด/ unload เปลือง 30 วินาที
- เล็กพอที่ไม่กิน VRAM มาก

### 🟡 3. Vision (Swappable)

```bash
ollama pull qwen2.5-vl:7b-q4_K_M
```
- VRAM: ~5 GB ตอน loaded (vision encoder กิน ~1.4 GB เพิ่ม)
- บทบาท: อ่านรูปภาพรอยร้าว, OCR nameplate, อ่านแบบ P&ID
- Swap rule: ตอนใช้ → unload Scavenger → load VL → ทำงาน → unload VL → reload Scavenger

### 🟡 4. Coder (Swappable)

```bash
ollama pull qwen3-coder:8b-q4_K_M
# หรือถ้ายังไม่มี Qwen3 ให้ใช้:
ollama pull qwen2.5-coder:7b-q4_K_M
```
- VRAM: ~5 GB
- บทบาท: เขียน Python, Excel formula, openpyxl code, SQL
- ตอน night cycle: ใช้สำหรับ code review + auto-tool generation

### 🟡 5. Writer (Swappable หรือ CPU+GPU split)

```bash
ollama pull qwen3:14b-instruct-q4_K_M
```
- VRAM: ~9 GB → **ต้อง CPU+GPU split** (ไม่พอ VRAM 8 GB)
- llama.cpp config: `-ngl 25` (offload 25/40 layers to GPU)
- Speed: 8-15 tok/s (ช้าแต่คุณภาพดี)
- บทบาท: เขียนรายงานยาว, เขียน slide content

**ทางเลือกที่เร็วกว่า:** ใช้ Qwen3-8B (orchestrator) เป็น writer ด้วย
- ไม่ต้อง swap
- เร็วกว่า 3-4x
- คุณภาพ ~80% ของ 14B (ในความเห็น community เม.ย. 2026)

## 4.3 ทีมสำรอง (Heavy Team) — ใช้กลางคืนเป็นหลัก

### 🟢 6. Heavy Reasoning (CPU mode)

```bash
ollama pull qwen3:27b-instruct-q4_K_M
# หรือ
huggingface-cli download unsloth/Qwen3.6-27B-GGUF \
  --include "Qwen3.6-27B-UD-Q4_K_XL.gguf" \
  --local-dir ./models/heavy_reasoning
```
- RAM: ~17 GB (CPU mode) หรือ ~10 GB GPU + ~7 GB RAM (split)
- Speed: 3-5 tok/s (CPU only) หรือ 8-12 tok/s (split)
- บทบาท: Root cause analysis, deep stress/strain reasoning, night replay

### 🟢 7. Heavy Agent (CPU mode, optional)

```bash
huggingface-cli download NousResearch/Hermes-4-35B-A3B-GGUF \
  --include "Hermes-4-35B-A3B-Q4_K_M.gguf" \
  --local-dir ./models/heavy_agent
```
- RAM: ~22 GB (CPU mode)
- Speed: 3-5 tok/s
- **ห้ามรันบน GPU** ที่ 8 GB (ไม่พอ)
- บทบาท: Devil's Advocate, complex agent loops, night audit replay

**Note:** ไม่จำเป็นต้องโหลดเลยตอน Phase 0 — โหลดเมื่อ Night Cycle ต้องการเท่านั้น

### 🟢 8. Embedding Model

```bash
# Multilingual ที่รองรับภาษาไทยดี
ollama pull bge-m3
# หรือ
ollama pull dengcao/Qwen3-Embedding-8B:Q4_K_M  # ใหม่ Apr 2026
```
- ขนาด: 567 MB (BGE-M3) / 4.5 GB (Qwen3-Embedding)
- รันบน CPU
- บทบาท: ChromaDB embedding, semantic search

**กฎ:** ห้ามใช้ all-MiniLM-L6-v2 ที่ v4.0 แนะนำ — ภาษาไทยอ่อน

## 4.4 ตารางสรุป VRAM/RAM Budget

```
┌─────────────────────────────────────────────────────────────┐
│  STATE: Idle (ระหว่างรอ user)                                │
├─────────────────────────────────────────────────────────────┤
│  GPU 8 GB:                                                   │
│    OS + background           ~0.5 GB                         │
│    Qwen3-8B (Orchestrator)   ~5.0 GB                         │
│    Qwen3-1.7B (Scavenger)    ~1.0 GB                         │
│    ────────────────────────                                  │
│    Used:                     ~6.5 GB                         │
│    Free (KV cache + headroom): ~1.5 GB                       │
│                                                              │
│  RAM 32 GB:                                                  │
│    Used: ~4 GB (system)      Free: ~28 GB                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  STATE: Vision Task                                          │
├─────────────────────────────────────────────────────────────┤
│  GPU: Unload Scavenger temporarily                           │
│    Qwen3-8B                  ~5.0 GB                         │
│    Qwen2.5-VL-7B             ~5.0 GB ← swap in              │
│  ❌ เกิน 8 GB! → ต้องเลือก:                                  │
│    A) Unload Orchestrator ระหว่าง vision (slow)             │
│    B) Run VL on CPU+GPU split                               │
│    C) Use Qwen3-VL-2B (เล็กกว่า, ~2 GB) - ลอง               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  STATE: Night Cycle (ไม่มี user รอ)                          │
├─────────────────────────────────────────────────────────────┤
│  GPU: Unload all                                             │
│  RAM: Load Heavy 27B (~17 GB)                                │
│    Replay daytime tasks at 3-5 tok/s                         │
│    OK เพราะไม่มีใครรอ                                       │
└─────────────────────────────────────────────────────────────┘
```

## 4.5 Decision Matrix: Model ไหนสำหรับ Task ไหน

| Task | Model | Mode | เหตุผล |
|---|---|---|---|
| Clarification dialog | Qwen3-8B | Locked GPU | ตอบเร็ว, tool calling |
| RAG retrieval | Qwen3-1.7B | Locked GPU | เล็ก เร็ว ค้นได้ดี |
| Read engineering PDF | Qwen3-8B | Locked GPU | ภาษาไทย+อังกฤษดี |
| Image analysis (รอยร้าว) | Qwen2.5-VL-7B | Swap GPU | vision เฉพาะทาง |
| Excel formula generation | Qwen3-Coder-8B | Swap GPU | code SOTA ระดับนี้ |
| Stress/Strain calc | **SymPy** (NOT AI!) | CPU | deterministic + ถูก 100% |
| Long report writing | Qwen3-8B หรือ 14B | Locked / Split | คุณภาพ + speed balance |
| Slide content (PPTX) | Qwen3-8B | Locked GPU | ไม่ต้องยาวมาก |
| Root cause (high stake) | Qwen3-27B | CPU+RAM | reasoning depth |
| Night replay | Qwen3-27B หรือ Hermes 35B | CPU | quality > speed |
| Auditor (CoVe) | Qwen3-8B | Locked GPU | rule-based ไม่ต้องใหญ่ |
| Devil's Advocate (debate) | Qwen3-8B (different prompt) | Locked GPU | ใช้ตัวเดิมต่างบทบาท |

---

# 5. โครงสร้างโฟลเดอร์

## 5.1 Tree เต็ม

```
~/tpm_workspace/                        # หรือ /mnt/d/tpm_workspace บน Windows
│
├── 📥 raw_data/                        # ไฟล์ input ทั้งหมด
│   ├── pdf_manuals/                   # คู่มือผู้ผลิต PDF
│   ├── excel_logs/                    # maintenance log Excel
│   ├── images/                        # รูปถ่ายอุปกรณ์
│   ├── word_specs/                    # spec sheets Word
│   ├── standards/                     # มอก. ISO ASME PDF
│   └── triz/                          # TRIZ Matrix + Principles
│
├── 🧠 .tpm_context/                    # สมองของระบบ
│   ├── AGENTS.md                      # บุคลิก + Engineering Mind Protocol
│   ├── SKILL.md                       # System-level skills
│   ├── SCHEMA.md                      # Wiki structure for LLM
│   ├── RUNBOOK.md                     # คู่มือสำหรับคนอื่นใช้แทน
│   ├── MIGRATION.md                   # 🆕 คู่มือย้ายไปโปรเจคต่อไป
│   │
│   ├── data_classification.yaml       # 🆕 ระดับข้อมูล (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED)
│   ├── domain_knowledge/              # 🆕 TPM domain
│   │   ├── fmea/                      # FMEA template + scales
│   │   ├── rcm/                       # RCM decision tree
│   │   ├── kpis/                      # MTBF, MTTR, OEE calculations
│   │   ├── criticality/               # ABC classification, SIL levels
│   │   └── work_orders/               # WO classification schema
│   │
│   ├── wiki/                          # OpenKB compiled wiki (Obsidian vault)
│   │   ├── sources/                   # สรุปแต่ละเอกสาร
│   │   ├── entities/                  # อุปกรณ์, supplier, person
│   │   ├── concepts/                  # TRIZ, แนวคิด, วิธีแก้
│   │   ├── synthesis/                 # การสังเคราะห์ข้ามหัวข้อ
│   │   ├── index.md                   # catalog
│   │   └── log.md                     # ingest log
│   │
│   ├── skills/                        # Workflow templates (gold standard)
│   │   ├── erp_login.md
│   │   ├── submit_work_order.md
│   │   ├── ppt_guidelines.md
│   │   ├── report_template.md
│   │   ├── triz_matrix.yaml           # 🆕 Structured (ไม่ใช่ markdown)
│   │   └── triz_principles.yaml       # 🆕
│   │
│   ├── anti_patterns/                 # สุสานความล้มเหลว
│   │
│   ├── local_tools/                   # 🆕 Open-source tools first
│   │   ├── installed/                 # OSS libraries ที่ใช้
│   │   ├── wrappers/                  # thin wrapper รอบ OSS
│   │   ├── ai_generated/              # AI สร้าง (เป็นทางสุดท้าย)
│   │   └── scripts/                   # one-click scripts
│   │
│   ├── tool_registry.json             # registry ของ tools ทั้งหมด
│   ├── tool_search_index/             # 🆕 ChromaDB index ของ tools
│   │
│   ├── prompts/                       # 🆕 Prompt templates (versioned)
│   │   ├── orchestrator/
│   │   ├── workers/
│   │   └── auditor/
│   │
│   ├── golden_dataset/                # 50+ test cases สำหรับ regression
│   │
│   ├── activity_log/                  # 🆕 Activity tracking
│   │   ├── inside_ai/                 # tracking ระหว่าง AI session
│   │   ├── outside_ai/                # 🆕 tracking ตอนไม่ใช้ AI
│   │   └── patterns/                  # detected patterns
│   │
│   ├── decision_log/                  # 🆕 Explanation system
│   │   ├── daily/YYYY-MM-DD/
│   │   └── for_reports/               # ใช้สร้าง progress report
│   │
│   ├── night_cycle/                   # 🆕 Night audit system
│   │   ├── replays/                   # ผลการ replay
│   │   ├── discrepancies/             # ความแตกต่าง
│   │   ├── proposed_fixes/            # AI เสนอแก้
│   │   └── morning_brief/             # สรุปสำหรับเช้า
│   │
│   ├── audit_log.db                   # SQLite + hash chain (tamper-evident)
│   ├── event_log.db                   # SQLite events
│   ├── confidence_calibration.db      # 🆕 calibration tracking
│   ├── langgraph_checkpoint.db        # state checkpoint
│   ├── logger_consent.json            # consent for activity logger
│   └── .git/                          # 🆕 Git repo (auto-commit + push to GitHub)
│
├── 💾 chroma_db/                       # Vector DB (web cache)
│
├── 🤖 models/                          # GGUF model files (~80 GB)
│   ├── orchestrator/                  # Qwen3-8B
│   ├── scavenger/                     # Qwen3-1.7B
│   ├── vision/                        # Qwen2.5-VL-7B
│   ├── coder/                         # Qwen3-Coder-8B
│   ├── writer/                        # (optional) Qwen3-14B
│   ├── heavy_reasoning/               # Qwen3-27B (lazy load)
│   ├── heavy_agent/                   # Hermes-35B (lazy load, optional)
│   └── embedding/                     # BGE-M3
│
├── 🔧 services/                        # 🆕 Self-hosted services
│   ├── searxng/                       # SearXNG meta-search (Docker)
│   ├── langfuse/                      # LLM observability (Docker)
│   ├── arize_phoenix/                 # Eval (Docker)
│   └── docker-compose.yml             # ทุก service ในไฟล์เดียว
│
├── 📤 output/                          # ผลลัพธ์สุดท้าย
│   ├── reports/
│   ├── excel/
│   ├── pptx/
│   └── progress_reports/              # 🆕 สำหรับส่งหัวหน้า
│
├── 🌙 logs/                            # System logs (rotated)
│
├── activity_tracker.py                 # 🆕 Tracking inside + outside
├── thermal_guard.py                    # Thermal monitoring
├── power_monitor.py                    # 🆕 Battery-aware scheduling
├── start.sh                            # ปุ่มเริ่มระบบ
├── stop.sh                             # ปุ่มหยุดระบบ
└── README.md                           # โปรเจคนี้คืออะไร
```

## 5.2 จุดสำคัญที่เปลี่ยน

| ของใหม่ใน v5.0 | เพื่ออะไร |
|---|---|
| `domain_knowledge/` | เพิ่ม FMEA, RCM, KPIs, Criticality |
| `data_classification.yaml` | กำหนดข้อมูลระดับไหนออกได้/ไม่ได้ |
| `local_tools/installed/` | OSS libraries ที่ใช้ — แยกจาก ai_generated |
| `tool_search_index/` | ChromaDB ค้น tool ด้วย semantic |
| `prompts/` versioned | rollback prompt ได้เมื่อพัง |
| `activity_log/outside_ai/` | tracking ตอนไม่ใช้ AI |
| `decision_log/for_reports/` | สร้าง progress report อัตโนมัติ |
| `night_cycle/` | self-correction system |
| `audit_log.db` (hash chain) | tamper-evident |
| `confidence_calibration.db` | track self-reported vs actual |
| `services/` | Docker compose self-hosted |
| `.git/` | GitHub backup |
| `MIGRATION.md` | ย้ายไปโปรเจคต่อไป |


---

# 6. ระบบ Knowledge 3 ชั้น

## 6.1 ภาพรวม

```
┌──────────────────────────────────────────────────────────────────┐
│ Layer 1: Local Knowledge (OpenKB Wiki)                            │
│   - คู่มือ PDF, Excel log, Word spec, Standard, TRIZ, Domain       │
│   - 100% trusted, 0% egress                                       │
│   - PageIndex tree navigation (98.7% accuracy)                    │
│   - ใช้สำหรับ: spec, safety, standard, internal procedures        │
├──────────────────────────────────────────────────────────────────┤
│ Layer 2: Web Cache (ChromaDB)                                    │
│   - ราคาอะไหล่, spec ผู้ผลิต, technical bulletin                  │
│   - Cached results from Layer 3                                   │
│   - BM25 + multilingual embedding hybrid                          │
│   - Auto-refresh based on TTL                                     │
├──────────────────────────────────────────────────────────────────┤
│ Layer 3: Live Web Search (NEW: Free-First)                       │
│   - 🆕 SearXNG self-hosted (FREE, UNLIMITED) ← primary           │
│   - 🆕 Brave Search API (2,000 free/mo) ← fallback               │
│   - 🆕 Tavily API (1,000 free/mo) ← AI-optimized fallback         │
│   - ❌ NOT Perplexity (expensive + slow per benchmarks)          │
└──────────────────────────────────────────────────────────────────┘
```

## 6.2 Layer 1: OpenKB + PageIndex (เหมือน v4.0)

**Setup:**
```bash
# OpenKB
pip install openkb

# PageIndex
pip install pageindex

# Multilingual embedding (ภาษาไทย)
ollama pull bge-m3
```

**Workflow:**
1. วางไฟล์ดิบใน `raw_data/`
2. รัน `openkb compile --vault .tpm_context/wiki/` (ครั้งแรก 2-8 ชม.)
3. PageIndex สร้าง tree navigation
4. Query ผ่าน PageIndex API
5. Incremental update เมื่อเพิ่มเอกสาร (เร็ว)

**กฎ Safety-Critical:**
```yaml
forced_l1_only:
  - LOTO procedures
  - Pressure limits
  - Hazmat handling
  - Confined space entry
  - Hot work permits
```
Topics เหล่านี้ **ห้าม** query ผ่าน Layer 2/3 เด็ดขาด — เฉพาะ Layer 1

## 6.3 Layer 2: ChromaDB (Web Cache)

**Setup:**
```bash
pip install chromadb
# Embedding ผ่าน Ollama
```

**Schema:**
```python
chroma_collection.add(
    documents=[chunk_text],
    metadatas=[{
        "source_url": url,
        "crawl_date": "2026-04-30",
        "freshness_ttl_days": 30,
        "category": "supplier_spec",
        "data_classification": "PUBLIC",
        "language": "th",
    }],
    ids=[chunk_id]
)
```

**Update Schedule:**
- ราคาอะไหล่: ทุก 7 วัน
- Safety bulletin: ทุก 3 วัน
- Spec ผู้ผลิต: ทุก 30 วัน
- ตรวจ TTL ใน night cycle

## 6.4 🆕 Layer 3: Free-First Search Strategy

> **อัปเดต พ.ค. 2026:** Brave Search API ยกเลิก Free Tier ตั้งแต่ ก.พ. 2026 → ตัดออก
> เปลี่ยนเป็น stack ที่มี **lane assignment ชัดๆ** ใช้ Exa.ai (structured + grounding) + Tavily (AI-clean) + DuckDuckGo + Wikipedia + Jina Reader

### 6.4.0 Lane Assignment (ใครรับ query ไหน)

```
┌──────────────────────────────────────────────────────────────────┐
│ Query Type                       → Service             Free Tier  │
├──────────────────────────────────────────────────────────────────┤
│ ทั่วไป (workhorse 80%)           → SearXNG              ∞         │
│ ต้องการ AI-clean สำหรับ LLM       → Tavily              1,000/mo  │
│ ต้องการ structured + citations    → Exa.ai              1,000/mo  │
│ Simple lookup (no key)            → DuckDuckGo IA       ∞         │
│ Reference / definition            → Wikipedia REST      ∞         │
│ ดึงเนื้อหา URL (Crawl4AI พัง)     → Jina Reader         free tier │
└──────────────────────────────────────────────────────────────────┘
```

### Routing decision

```python
async def search_layer3(query: str, intent: Intent, classification: str):
    """
    Lane-based routing — ใช้ provider ที่เด่นในงานนั้น
    เรียงตามต้นทุน + lane (specialized > generic)
    """
    # Egress guard ก่อนเสมอ
    if classification in ["CONFIDENTIAL", "RESTRICTED"]:
        raise EgressBlocked(f"Cannot search externally: {classification}")

    # Lane 1: definition / reference → Wikipedia (ฟรีไม่ต้อง key)
    if intent.is_definition or intent.is_standard_reference:
        try:
            return await wikipedia_search(query)
        except Exception:
            pass  # fall through

    # Lane 2: structured + grounding → Exa
    if intent.needs_grounding or intent.has_output_schema:
        if quota_available("exa"):
            try:
                return await exa.search(
                    query,
                    type="deep" if intent.is_research else "auto",
                    output_schema=intent.output_schema,
                    contents={"highlights": True},
                )
            except QuotaExceeded:
                pass

    # Lane 3: AI-optimized for LLM context (recent, current)
    if intent.feed_to_llm and intent.is_recent:
        if quota_available("tavily"):
            try:
                return await tavily.search(query, search_depth="advanced")
            except QuotaExceeded:
                pass

    # Lane 4: workhorse — SearXNG (∞)
    try:
        results = await searxng.search(query, max_results=10)
        if quality_score(results) >= 0.7:
            return results
    except Exception as e:
        log.warning(f"SearXNG failed: {e}")

    # Lane 5: simple lookup fallback (no key)
    try:
        return await duckduckgo_search(query)
    except Exception:
        pass

    # Last resort: insufficient
    return InsufficientResults(
        query=query,
        tried=["wikipedia", "exa", "tavily", "searxng", "duckduckgo"],
    )
```

### 6.4.1 SearXNG Setup (Primary, FREE Unlimited)

**ทำไมเลือก SearXNG:**
- ✅ FREE 100% ไม่จำกัด query
- ✅ Self-hosted — query ไม่ออก database ภายนอก
- ✅ Aggregate จาก 70+ search engines (Google, Bing, DuckDuckGo, ฯลฯ)
- ✅ JSON API พร้อมใช้กับ LangChain/LiteLLM
- ✅ Open-source 15k+ stars บน GitHub
- ⚠️ Trade-off: ต้อง self-host (Docker setup)

**Setup ด้วย Docker (5 นาที):**

```yaml
# services/searxng/docker-compose.yml
version: '3.7'
services:
  searxng:
    image: searxng/searxng:latest
    container_name: searxng
    ports:
      - "8888:8080"
    volumes:
      - ./settings.yml:/etc/searxng/settings.yml:ro
    environment:
      - BASE_URL=http://localhost:8888/
      - INSTANCE_NAME=tpm_searxng
    restart: unless-stopped
    depends_on:
      - redis

  redis:
    image: redis:alpine
    container_name: searxng-redis
    restart: unless-stopped
```

**settings.yml สำคัญ:**
```yaml
# services/searxng/settings.yml
use_default_settings: true

server:
  secret_key: "CHANGE_THIS_TO_RANDOM_STRING"  # openssl rand -hex 32
  limiter: false  # for single-user local
  bind_address: "0.0.0.0"

search:
  formats:
    - html
    - json   # IMPORTANT: enable JSON for API access

engines:
  # เปิดเฉพาะที่ต้องการ
  - name: google
    disabled: false
  - name: bing
    disabled: false
  - name: duckduckgo
    disabled: false
  - name: wikipedia
    disabled: false
  - name: github
    disabled: false
  # ปิดที่ไม่ต้องการเพื่อลด CAPTCHA
```

**การใช้งาน:**
```python
import requests

def searxng_search(query, format="json"):
    response = requests.get(
        "http://localhost:8888/search",
        params={"q": query, "format": format, "language": "th-TH"}
    )
    return response.json()
```

**LangChain integration:**
```python
from langchain_community.utilities import SearxSearchWrapper

search = SearxSearchWrapper(searx_host="http://localhost:8888")
results = search.run("ราคา bearing SKF 6205 ล่าสุด")
```

### 6.4.2 Tavily API (AI-optimized, 1,000 FREE/mo)

**ทำไม Tavily:**
- ✅ Free tier 1,000 credits/เดือน
- ✅ AI-optimized — return cleaned content for LLM
- ✅ LangChain native integration (1 line)
- ✅ Latency 998ms median (เร็วกว่า Perplexity 11s)
- ✅ Result มี relevance score ในตัว

**Setup:**
```bash
pip install tavily-python
echo "TAVILY_API_KEY=tvly-xxxxxxxx" >> .env
```

```python
from tavily import TavilyClient

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
result = client.search(
    query="latest pressure vessel ASME standard 2026",
    search_depth="advanced",
    max_results=5,
    include_raw_content=True
)
```

### 6.4.3 Exa.ai (Structured + Grounding, 1,000 FREE/mo)

**ทำไม Exa เด่น:**
- ✅ Free tier 1,000 requests/เดือน
- ✅ **`outputSchema` + grounding** — คืน JSON ตาม schema พร้อม **citation per field + confidence** → ตรงกับ AGENTS.md "ทุก claim มี pointer" + Auditor CoVe
- ✅ MCP server ผ่าน OAuth (ไม่ต้อง API key สำหรับ Claude Code)
- ✅ Search types หลากหลาย: instant (250ms), fast (450ms), auto (~1s), deep (4-15s), deep-reasoning (12-40s)
- ✅ Neural/semantic search — เจอ concept ที่ keyword search หา
- ✅ `/contents` endpoint — ดึง URL ที่รู้แล้ว (ทดแทน Crawl4AI บางกรณี)

**Pricing (สำคัญ — ตรวจล่าสุดที่ exa.ai/pricing):**

| Endpoint | Free | Paid |
|---|---|---|
| Search API | 1,000/mo | $7 / 1,000 (รวม contents 10 ผลแรก) |
| Answer API | 1,000/mo | $5 / 1,000 |
| Exa Deep | 1,000/mo | $12-15 / 1,000 (4-50s reasoning) |
| Contents | 1,000/mo | $1 / 1,000 pages |

**ใช้กรณีไหน:**
```python
# Case A: research ที่ต้องการ structured + cited
results = exa.search(
    "ASME Section VIII Div 1 MAWP formula 2026",
    type="deep",
    output_schema={
        "type": "object",
        "properties": {
            "formula": {"type": "string"},
            "applicable_temperature_range": {"type": "string"},
            "safety_factor_min": {"type": "number"},
        },
        "required": ["formula"],
    },
    contents={"highlights": True},
)
# → results.output.content = {"formula": "P = (2*S*E*t)/(D-1.2*t)", ...}
# → results.output.grounding = [{field, citations: [URL+title], confidence: "high"}]
```

**Setup (3 ทาง):**

```bash
# Option 1: pip + API key
pip install exa-py
echo "EXA_API_KEY=xxxx" >> .env
```

```bash
# Option 2: MCP via OAuth (no API key — for Claude Code dev)
claude mcp add --transport http exa https://mcp.exa.ai/mcp
# จะเปิด browser ให้ login ครั้งแรก
```

```python
# Option 3: ใช้ใน LangGraph orchestrator (production)
from exa_py import Exa
exa = Exa(api_key=os.getenv("EXA_API_KEY"))
```

**Lane: ใช้เมื่อต้องการ structured output + citations** (engineering reports, RCA findings, standards lookup) — ไม่ใช่สำหรับ general lookup

### 6.4.4 No-Key Free Services (DuckDuckGo + Wikipedia + Jina)

#### DuckDuckGo Instant Answer (no API key, ∞)

```bash
pip install duckduckgo-search
```

```python
from duckduckgo_search import DDGS

with DDGS() as ddgs:
    results = list(ddgs.text("TPM total productive maintenance", max_results=5))
```

**Lane:** simple lookup ที่ไม่ต้อง grounding — fallback ตอน SearXNG พัง

#### Wikipedia REST API (no API key, ∞)

```bash
pip install wikipedia-api
```

```python
import wikipediaapi

wiki = wikipediaapi.Wikipedia(user_agent="tpm-ai/1.0", language="en")
page = wiki.page("ASTM A106")
print(page.summary)
```

**Lane:** definition / standard reference ("ASTM A106 คืออะไร", "Wat is ISO 14224")

#### Jina Reader (free tier, page fetch)

```python
import httpx

# ดึงเนื้อหา URL clean — ทดแทน Crawl4AI ตอน JS-heavy
async def jina_fetch(url: str) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://r.jina.ai/{url}")
        return r.text  # markdown ที่ clean แล้ว
```

**Lane:** backup web fetch ตอน Crawl4AI/Trafilatura พัง

### 6.4.5 ทำไม **ไม่** ใช้ Perplexity / Brave

| Service | สถานะ | เหตุผล |
|---|---|---|
| **Perplexity Sonar Pro** | ❌ ไม่ใช้ | $5/1k req + $3/1M input + $15/1M output, latency 11s+ vs Tavily 998ms, vendor lock-in |
| **Brave Search API** | ❌ EOL | ก.พ. 2026 ยกเลิก Free Tier — ต้องจ่ายแล้วเท่านั้น |
| **Bing Web Search API** | ❌ EOL | Microsoft retired ส.ค. 2025 |
| **Kagi Search** | ❌ paid only | คุณภาพดีสุดแต่ไม่มี free |

**สรุป:** ฟรี first → จ่ายต่อเมื่อจำเป็นจริงๆ

### 6.4.6 Web Fetch (อ่านเนื้อหาเต็ม)

หลัง search ได้ URL → ต้องการอ่านเนื้อหาเต็ม

**Options (Open-Source First):**

| Tool | License | คุณสมบัติ | สถานะ |
|---|---|---|---|
| **Crawl4AI** | MIT | Headless browser + AI cleaning | ✅ ใช้ |
| **Trafilatura** | Apache 2.0 | Extract main content + metadata | ✅ Backup |
| **BeautifulSoup4** | MIT | Parse HTML | ✅ Helper |
| **Playwright** | Apache 2.0 | Full browser (สำหรับ JS-heavy) | ✅ ใช้ |
| Firecrawl | Open core | API + self-host | ⚠️ มี cloud variant |

```python
from crawl4ai import AsyncWebCrawler

async def fetch_clean_content(url: str) -> str:
    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(url=url)
        return result.markdown  # เนื้อหาที่ clean แล้ว
```

## 6.5 Router Logic (ปรับจาก v4.0)

```python
def route_query(query: str, classification: str) -> List[str]:
    """
    คืน list ของ layer ที่ควรค้น (ตามลำดับ)
    """
    keywords = analyze_keywords(query)

    # Safety-critical: L1 only
    if any(k in query for k in ["LOTO", "lockout", "ความดันสูงสุด",
                                  "hazmat", "ก๊าซระเบิด", "confined space"]):
        return ["L1_FORCED"]

    # Spec/standard internal: L1 first
    if any(k in keywords for k in ["spec", "คู่มือ", "manual", "มาตรฐาน",
                                     "ISO", "ASME", "มอก."]):
        return ["L1", "L2"]  # L1 หลัก, L2 ถ้าไม่พอ

    # Real-time data: L3 first
    if any(k in keywords for k in ["ราคา", "วันนี้", "ล่าสุด", "2026", "current"]):
        return ["L3"]  # ข้าม L1/L2

    # Mixed: parallel
    if "ราคา" in query and "spec" in query:
        return ["L1_PARALLEL", "L2_PARALLEL", "L3_PARALLEL"]

    # Default: L1 → L2 → L3
    return ["L1", "L2", "L3"]
```

## 6.6 Conflict Resolution

```python
def merge_results(l1, l2, l3) -> MergedResult:
    """
    รวมผลจาก 3 layer พร้อมตรวจ conflict
    """
    weights = {"L1": 0.6, "L2": 0.3, "L3": 0.1}

    # ตรวจตัวเลขที่เป็น numeric
    numbers_l1 = extract_numbers(l1)
    numbers_l2 = extract_numbers(l2)

    for n1 in numbers_l1:
        for n2 in numbers_l2:
            if same_topic(n1, n2):
                diff_pct = abs(n1.value - n2.value) / n1.value
                if diff_pct > 0.10:  # ต่างกัน > 10%
                    return ConflictDetected(
                        l1_value=n1, l2_value=n2,
                        topic=n1.topic,
                        force_human_gate=True
                    )

    return weighted_merge([l1, l2, l3], weights)
```


---

# 7. Prompt Clarification System

> **🆕 ใหม่ใน v5.0 — ก่อน AI ทำอะไรต้องผ่านระบบนี้ทุกครั้ง**

## 7.1 ปัญหาที่กำลังแก้

User พิมพ์ prompt → AI ตีความ → ทำงานผิดทิศ → เสียเวลา + token

**ตัวอย่างจริงที่เกิดบ่อย:**
```
User: "ทำรายงานให้หน่อย"
❌ AI ทำรายงานทั่วไป → ไม่ตรงที่ user ต้องการ
✅ AI ถาม:
   "คุณหมายถึงรายงานเกี่ยวกับ:
    A) Maintenance ของอุปกรณ์ที่คุณเพิ่งวิเคราะห์
    B) Progress การทำงานของระบบ AI สัปดาห์นี้
    C) Root cause analysis ของ incident เมื่อวาน
    D) อื่นๆ — กรุณาระบุ"
```

## 7.2 Architecture

```
[User Input]
    ↓
[Intent Parser] ← Qwen3-8B
    ├── Extract: action_verbs, objects, constraints, time_refs
    └── Identify: required_slots that need filling
    ↓
[Ambiguity Detector]
    ├── confidence < 80% → must clarify
    ├── multiple_interpretations → must clarify
    └── missing_critical_slot → must clarify
    ↓
┌──────────────────────────────────────────┐
│ [Clarification Dialog]                    │
│                                            │
│ AI: "คุณหมายถึง [interpretation_1] ใช่ไหม?  │
│      ถ้าใช่กด ✓                          │
│      ถ้าไม่ใช่ ตัวเลือกอื่น:              │
│      [interpretation_2]                    │
│      [interpretation_3]                    │
│      หรือพิมพ์อธิบายเพิ่ม"                │
│                                            │
│ User: [select / type more]                 │
│                                            │
│ Loop จนกระทั่ง: confidence ≥ 90%          │
└──────────────────────────────────────────┘
    ↓
[Confirmed Intent JSON]
    ↓
[Inquiry-First Phase] (ดู Section 8)
    ↓
[Task Planning]
```

## 7.3 Pseudocode

```python
class ClarificationLoop:
    """
    บังคับ confirm intent ก่อน AI ทำงานจริง
    """

    MIN_CONFIDENCE = 0.90

    async def clarify(self, user_input: str) -> ConfirmedIntent:
        max_iterations = 5
        history = [user_input]

        for iteration in range(max_iterations):
            # 1. Parse intent
            intent = await self.parse_intent(history)

            # 2. ตรวจ ambiguity
            if intent.confidence >= self.MIN_CONFIDENCE:
                # ถาม user confirm 1 ครั้งก่อน proceed
                confirmed = await self.final_confirm(intent)
                if confirmed:
                    return ConfirmedIntent(
                        action=intent.action,
                        slots=intent.slots,
                        constraints=intent.constraints,
                        history=history
                    )

            # 3. สร้าง clarification question
            question = await self.generate_clarification_question(intent, history)

            # 4. ส่งให้ user (Chainlit UI)
            user_response = await self.ui.ask_clarification(question)
            history.append(user_response)

            # 5. ถ้า user หงุดหงิด ("เอาแบบนี้แหละ") → proceed กับ best guess + warning
            if self.user_frustrated(user_response):
                return ConfirmedIntent(
                    action=intent.action,
                    slots=intent.slots,
                    confidence=intent.confidence,
                    user_override=True,
                    warning="User overrode clarification — proceed with current understanding"
                )

        # ครบ max iterations แล้วยังไม่ชัด → escalate
        raise ClarificationFailure("Cannot determine user intent after 5 iterations")

    async def generate_clarification_question(self, intent, history):
        # ใช้ structured prompt เพื่อให้ Qwen3-8B output JSON
        prompt = f"""
        User said: {history[-1]}

        Your current understanding:
        - Action: {intent.action} (confidence: {intent.confidence})
        - Subject: {intent.subject}
        - Constraints: {intent.constraints}

        ขาดข้อมูลในส่วน: {intent.missing_slots}
        การตีความที่เป็นไปได้:
        {intent.alternatives}

        ออกคำถาม clarification (Thai) ให้ user เลือก:
        - Format: ABC choice + "อื่นๆ"
        - ใช้ภาษาง่ายๆ ไม่ technical
        - ไม่เกิน 3 ตัวเลือก
        """
        return await self.llm.generate(prompt, format="json")
```

## 7.4 ตัวอย่าง Dialog (เต็ม)

### กรณี 1: คำสั่งคลุมเครือ

```
User:  "ตรวจของเครื่อง"

AI:    "เพื่อให้ผมเข้าใจถูกต้อง คุณหมายถึงงานไหน?

       A) ตรวจสภาพปัจจุบันของเครื่อง (current state inspection)
          → ผมจะอ่านล่าสุดจาก maintenance log + รูปจาก vision
       B) ตรวจตามแผน PM (preventive maintenance scheduled)
          → ผมจะดู PM schedule + checklist
       C) ตรวจหาสาเหตุที่เครื่องเสีย (root cause investigation)
          → ผมจะวิเคราะห์จากที่บันทึกอาการ + เชื่อมโยงกับ historical data

       หรือพิมพ์อธิบายเพิ่ม"

User:  "B"

AI:    "เครื่องไหนครับ? (หรือทุกเครื่อง?)
       เห็นใน wiki มีเครื่อง:
       - Boiler #1, #2, #3
       - Compressor A, B
       - Pump P-101, P-102, P-103

       หรือระบุ tag number ก็ได้"

User:  "Boiler #2"

AI:    "เข้าใจแล้ว สรุปคำสั่ง:
       - งาน: Preventive Maintenance check
       - อุปกรณ์: Boiler #2
       - ขอบเขต: ตรวจ PM schedule + checklist + รวมถึง maintenance log ย้อนหลัง 3 เดือน

       เริ่มเลยไหม? [✓ เริ่ม]  [แก้ไข]"

User:  [✓ เริ่ม]

→ AI proceed with confirmed_intent = {
    action: "preventive_maintenance_check",
    target: "Boiler #2",
    scope: "PM_schedule + checklist + recent_history_3mo"
  }
```

### กรณี 2: User หงุดหงิดจะข้าม

```
User:  "อย่ามาถาม ทำไปเลย"

AI:    "เข้าใจครับ ผมจะใช้การตีความล่าสุด:
       - งาน: ตรวจสภาพ
       - อุปกรณ์: ตามที่ระบุล่าสุด (Boiler #2)
       - ขอบเขต: รายงานสถานะปัจจุบัน

       ⚠️ เนื่องจากข้ามขั้นตอน confirm → จะ flag output เพื่อให้คุณตรวจก่อน approve
       เริ่มเลย..."
```

## 7.5 Skip Clarification เมื่อใด

ไม่ทุกกรณีต้อง clarify — กฎการ skip:

```yaml
skip_clarification_when:
  - prompt_already_specific:
      example: "วิเคราะห์รอยร้าวในรูปนี้แล้วเขียน maintenance report พร้อม pointer"
      reason: action + object + format ครบ
  - continuation_of_session:
      example: "ทำต่อ" หลัง AI ทำ Boiler #2 PM check แล้ว
      reason: context ชัดจาก session
  - user_explicitly_said_skip:
      keywords: ["skip clarify", "ไม่ต้องถาม", "go ahead"]
      action: warn user แล้ว proceed
  - low_stakes_routine:
      example: "ดูราคา bearing 6205"
      reason: simple lookup, ตีความผิดเสียหายน้อย
```

## 7.6 UI Mockup (Chainlit)

```
┌─────────────────────────────────────────────────────────┐
│ 🤖 TPM Assistant                                  [─][□][×]│
├─────────────────────────────────────────────────────────┤
│                                                          │
│ You: "ทำรายงานให้หน่อย"                                  │
│                                                          │
│ ✋ ก่อนเริ่มขอ confirm นิดหนึ่ง                            │
│                                                          │
│ คุณหมายถึงรายงานเกี่ยวกับ:                                │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ A) Maintenance ของ Boiler #2 (ล่าสุดที่คุย)       │   │
│  │    📊 จะรวม: PM check + log + recommendation     │   │
│  │    ⏱️ ใช้เวลาประมาณ: 3-5 นาที                    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ B) Progress รายสัปดาห์ของระบบ AI                 │   │
│  │    📊 จะรวม: tasks ที่ทำ + tools ที่สร้าง        │   │
│  │    ⏱️ ใช้เวลาประมาณ: 1-2 นาที                    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ C) อื่นๆ — พิมพ์อธิบายเพิ่ม                      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  [ A ]  [ B ]  [ C ]  [ Skip & ทำเลย ]                  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

# 8. Inquiry-First Pattern

> **🆕 ใหม่ใน v5.0 — ขาดข้อมูลให้ถาม user ก่อน เป็นทางสุดท้ายค่อยค้น**

## 8.1 ปัญหาที่กำลังแก้

User บอก task → AI พบว่าขาดข้อมูล → ค้น web ทันที → เสียเวลา + แพง + บางครั้ง user รู้คำตอบอยู่แล้ว!

## 8.2 Decision Tree

```
[AI พบว่าขาดข้อมูล X]
    ↓
[ตรวจ: X อยู่ใน wiki ไหม?]
    ├── มี → ใช้ wiki
    └── ไม่มี → ↓
    ↓
[ตรวจ: X เป็น user-specific หรือไม่?]
    ├── ใช่ (เช่น "เครื่องไหน", "ใครรับผิดชอบ")
    │   → 🆕 ASK USER FIRST
    │     ├── User ตอบได้ → ใช้คำตอบ + บันทึกใน Mem0
    │     └── User บอกไม่รู้ → ค้น web ตามปกติ
    │
    └── ไม่ใช่ (technical fact ทั่วไป)
        → ค้น Layer 1 → 2 → 3 ตามปกติ
```

## 8.3 Pseudocode

```python
class InquiryFirstSearch:

    USER_SPECIFIC_PATTERNS = [
        r"เครื่องไหน",
        r"ของใคร",
        r"ที่ไหน.*โรงงาน",
        r"ของเรา",
        r"internal",
        r"company-specific",
    ]

    async def search_with_inquiry(self,
                                    query: str,
                                    context: SessionContext) -> SearchResult:
        # Step 1: ลอง wiki ก่อน (ฟรี + เร็ว + trusted)
        wiki_result = await self.search_wiki(query)
        if wiki_result.confidence > 0.8:
            return wiki_result

        # Step 2: ตรวจว่า user-specific?
        if self.is_user_specific(query):
            # 🆕 ASK USER FIRST
            user_answer = await self.ask_user(
                question=f"ผมต้องการข้อมูล: {query}",
                context_hint=f"เห็นใน wiki/log มี: {wiki_result.partial_hits}",
                options=[
                    "ตอบจากความจำ",
                    "ผมไม่รู้ — ค้น web ให้",
                    "ดูที่ ... (ระบุที่)",
                ]
            )

            if user_answer.has_answer:
                # บันทึกใน Mem0 สำหรับครั้งหน้า
                await self.memory.store(
                    fact=user_answer.text,
                    context=query,
                    source="user_provided"
                )
                return SearchResult(
                    content=user_answer.text,
                    source="user",
                    confidence=1.0
                )
            elif user_answer.points_to_location:
                return await self.search_specific_location(user_answer.location)

        # Step 3: ค้น web (ตามปกติ)
        return await self.search_web(query, context.classification)

    def is_user_specific(self, query: str) -> bool:
        # Pattern match
        for pattern in self.USER_SPECIFIC_PATTERNS:
            if re.search(pattern, query):
                return True

        # Semantic check via small model
        return self.scavenger.classify_user_specific(query) > 0.7
```

## 8.4 ตัวอย่าง Dialog

### Case A: User รู้คำตอบ → ประหยัดเวลา

```
[Confirmed intent: "ตรวจ PM ของ Boiler #2"]

AI ขณะ planning: "ผมต้องการ PM schedule ล่าสุดของ Boiler #2..."

[ตรวจ wiki: ไม่พบ schedule ปี 2026 — มีแค่ 2025]

AI:    "ผมหา PM schedule ปี 2026 ของ Boiler #2 ใน wiki ไม่เจอ
       (มีแค่ปี 2025) คุณช่วยบอกได้ไหม:

       A) ผมรู้ — schedule รอบล่าสุดคือ ...
       B) ดูใน file ... (ระบุ path)
       C) ฉันก็ไม่รู้ — ค้น web ให้

       (ถ้ามี file ให้ผมจะอ่านแล้วเก็บใน wiki ให้ครั้งหน้าใช้ได้)"

User:  "B - อยู่ใน Excel raw_data/excel_logs/PM_2026.xlsx tab 'Boiler'"

AI:    "ขอบคุณครับ กำลังเปิดไฟล์..."
       [openpyxl เปิด → อ่าน → extract → store ใน wiki]
       "เจอแล้ว: PM ครั้งสุดท้าย 15 เม.ย. 2026 → ครั้งถัดไป 15 ก.ค. 2026"
```

### Case B: User ไม่รู้ → ค้น web

```
AI:    "ผมต้องการราคา bearing SKF 6205 ปัจจุบัน คุณรู้ไหม?
       A) รู้ — ราคา ฿... (จากที่ซื้อล่าสุด)
       B) ไม่รู้ — ค้นให้
       C) ดูที่ supplier portal (ระบุ link)"

User:  "B"

AI:    "OK กำลังค้น..."
       [SearXNG → search "SKF 6205 ราคา"]
       "เจอ 3 ราคา: ฿180-250 (ขึ้นกับ supplier)"
```

### Case C: User ระบุ source

```
User:  "B - ดูที่ portal.skf-thailand.com"

AI:    "OK กำลังเข้า portal..."
       [Playwright → login (ถ้าต้อง) → navigate → extract]
       "ราคา: ฿198/ชิ้น (1 พ.ค. 2026), stock: 250 ชิ้น"
```

## 8.5 Memory Integration

ทุกครั้งที่ user ตอบ → บันทึกใน Mem0:

```python
# ในครั้งหน้าที่ AI ต้องการข้อมูลคล้ายกัน
memories = await self.memory.search(query="PM schedule Boiler #2")
# คืน: [{
#   "fact": "PM schedule 2026 Boiler#2 อยู่ใน raw_data/excel_logs/PM_2026.xlsx tab Boiler",
#   "source": "user_provided",
#   "date": "2026-05-01",
#   "valid_until": "2026-12-31"
# }]

# ใช้ memory นี้แทนการถาม user ซ้ำ
if memories and not is_stale(memories[0]):
    return self.read_from(memories[0].location)
```

## 8.6 กฎ: เมื่อใด **ไม่** ต้อง Inquiry-First

```yaml
skip_inquiry_when:
  - clearly_general_knowledge:
      examples:
        - "ASME boiler code คืออะไร"
        - "TRIZ principle 35 คือ"
      reason: ไม่ใช่ company-specific

  - user_explicitly_provided:
      example: User เพิ่งบอกข้อมูลเมื่อ 30 วินาทีที่แล้ว
      reason: ถามซ้ำ = annoying

  - emergency_mode:
      example: "ด่วน! เครื่องไหม้!"
      action: skip inquiry, ใช้ best guess + flag

  - night_cycle:
      reason: User หลับ → ไม่ควรปลุกถาม → ค้น/ใช้ default
```


---

# 9. Engineering Mind Protocol

> **โครงสร้างความคิดที่ทุก agent ต้องใช้** — เหมือน v4.0 แต่ปรับให้ใช้ได้จริง

## 9.1 Constitution Layer — 4 หลัก

### หลักที่ 1: ความซื่อสัตย์ต่อข้อมูล

```
✓ "คู่มือหน้า 42 ระบุ 245°C แต่ log บอก 247°C — ขัดแย้ง"
✗ "อุณหภูมิ 246°C" (เฉลี่ยเอง)

✓ "ยังไม่แน่ใจเพราะ source หลายตัวขัดแย้งกัน"
✗ "ตัวเลขนี้ถูกต้อง" (แต่จริงๆ ไม่ได้ verify)
```

### หลักที่ 2: แสดง reasoning ก่อน output

```
✓ "พิจารณา: log แสดงอุณหภูมิเพิ่ม 5°C ใน 2 ชม. + spec ระบุ max 250°C
   → สรุป: ใกล้ขีดจำกัด ควรลด load
   เพราะ: rate of rise + headroom ≤ 5°C เป็น early warning"
✗ "ลด load" (ไม่บอกที่มา)
```

### หลักที่ 3: Safety > Efficiency

```
✓ "หยุดและรอ approve เพราะพบว่า task ต้อง LOTO แต่ไม่มีบันทึก"
✗ "เขียนรายงานต่อโดยไม่แจ้ง"
```

### หลักที่ 4: รู้ขอบเขตตัวเอง

```
✓ "งานนี้ต้อง domain expertise ที่ผมไม่มี ควรถามวิศวกร"
✗ พยายามตอบทั้งที่ข้อมูลไม่ครบ
```

## 9.2 Thinking Protocol (10 Steps)

ทุก node ก่อนตอบให้ทำใน `<think>` tags:

```
<think>
STEP 1 - OBSERVE: ข้อมูลที่มีอยู่ทั้งหมด
STEP 2 - GAPS: อะไรขาด → trigger Inquiry-First (Section 8)
STEP 3 - CONSTRAINTS: Safety, budget, time, อะไหล่
STEP 4 - RULES: กฎ/มาตรฐาน/LOTO ที่เกี่ยวข้อง
STEP 5 - TRIZ CHECK: contradiction → ค้น TRIZ matrix
STEP 6 - HYPOTHESIS x3: H1, H2, H3
STEP 7 - REASON: ข้อมูล + กฎ + hypothesis → conclusion
STEP 8 - UNCERTAINTY:
  - measured_confidence (จาก self-consistency, ไม่ใช่ self-report)
  - high_because: [...]
  - uncertain_about: [...]
  - would_increase_if: [...]
STEP 9 - ACTION:
  - measured_confidence < 0.70 → Inquiry-First หรือ ค้น
  - measured_confidence ≥ 0.70 → proceed
STEP 10 - CONDITIONAL RECOMMEND:
  ไม่ตอบ "ทำ X" แต่:
  - ถ้า [A] → แนะ X เพราะ ...
  - ถ้า [B] → แนะ Y เพราะ ...
</think>
```

## 9.3 🆕 Measured Confidence (แก้ปัญหา P0-2 จาก v4.0)

**ปัญหา:** LLM "self-reported confidence" เชื่อไม่ได้

**วิธีแก้:**
```python
async def measured_confidence(prompt: str, model, n: int = 5) -> float:
    """
    แทนที่จะถาม model ว่ามั่นใจกี่ %
    ให้ตอบหลายรอบที่ temperature ต่างกัน
    confidence = agreement ระหว่างคำตอบ
    """
    answers = []
    for temp in [0.3, 0.5, 0.7, 0.9, 1.1]:
        ans = await model.generate(prompt, temperature=temp)
        answers.append(ans)

    # ใช้ embedding คำนวณ similarity
    embeddings = [embed(a) for a in answers]
    similarities = pairwise_cosine(embeddings)
    avg_similarity = mean(similarities)

    return {
        "confidence": avg_similarity,           # 0-1 จาก agreement จริง
        "answers": answers,
        "outliers": find_outliers(answers),
    }
```

**กฎ:**
- Self-consistency > 0.85 → confidence ใช้ได้
- Self-consistency < 0.70 → flag uncertain → trigger Human Gate
- ไม่ใช้ self-reported confidence ในการ gate ใดๆ

## 9.4 Self-Critique Loop (ก่อน Auditor)

ทุก draft ต้องผ่าน self-check 4 ข้อ:

```python
class SelfCritiqueChecklist:
    questions = [
        "□ ทุก claim มี pointer (PDF page / source URL) ไหม?",
        "□ มีตัวเลขที่ AI 'คิดเอง' โดยไม่ผ่าน calculator ไหม?",
        "□ มี safety concern ที่ยังไม่ flag ไหม?",
        "□ ส่วนที่ไม่แน่ใจได้บอกไหม?",
    ]

    async def check(self, draft: str) -> CritiqueResult:
        results = []
        for q in self.questions:
            ans = await self.llm.generate(
                prompt=f"Review draft: {draft}\nQuestion: {q}\nAnswer JSON: {{passed: bool, reason: str}}"
            )
            results.append(ans)

        if not all(r.passed for r in results):
            return CritiqueResult(
                passed=False,
                fixes_needed=[r for r in results if not r.passed],
                must_revise=True
            )
        return CritiqueResult(passed=True)
```

## 9.5 TRIZ Integration (ปรับจาก v4.0)

**🆕 v4.0 ผิด:** ใช้ TRIZ matrix เป็น RAG document → semantic search ผิด

**v5.0 ถูก:** ใช้เป็น structured lookup

```python
# triz_matrix.yaml (39x39 grid)
matrix:
  14_strength:
    1_weight_moving:  [40, 26, 27, 1]
    27_reliability:   [3, 17, 35, 40]
    # ... 39 columns

# triz_principles.yaml
principles:
  40:
    name_th: "วัสดุประกอบ Composite Materials"
    name_en: "Composite Materials"
    description: "เปลี่ยนวัสดุเดี่ยวเป็นวัสดุประกอบ"
    examples: [...]
```

```python
def triz_resolve(improving: str, worsening: str) -> List[Principle]:
    # 1. แปลง natural language → TRIZ parameter ID
    imp_id = map_to_triz(improving)
    wor_id = map_to_triz(worsening)

    # 2. Exact lookup (ไม่ใช่ semantic)
    principle_ids = MATRIX[imp_id][wor_id]

    # 3. ดึงคำอธิบาย
    return [PRINCIPLES[pid] for pid in principle_ids]
```

---

# 10. Pipeline หลัก

## 10.1 Master Flow

```
[USER INPUT]
   ↓
[CLARIFICATION] ← 🆕 Section 7
   ├── Confirmed → ↓
   └── Iterate
   ↓
[INQUIRY-FIRST PHASE] ← 🆕 Section 8
   ├── Has internal/user info → use it
   └── Need external → ↓
   ↓
[RECON MASTER]
   ├── Check wiki first
   ├── Trigger Search Loop if gap
   ↓
[SEARCH LOOP]
   ├── Round 1: L1 (wiki) + L2 (cache) parallel
   │   └── quality ≥ 0.7? → merge
   ├── Round 2: + L3 SearXNG (FREE)
   ├── Round 3: + Brave/Tavily (Free tier)
   ↓
[QUALITY CHECK]
   ├── pass → planner
   └── fail → user fallback ("ผมหาไม่เจอ คุณทราบไหม?")
   ↓
[TASK PLANNER]
   ↓
[WORKER SUBGRAPHS] ← 🆕 Tools-first (Section 13)
   ↓
[AUDITOR + CoVe]
   ├── pass → ↓
   └── fail → Hell Loop (max 3) → escalate
   ↓
[HUMAN GATE]
   ├── 🆕 Decision Trace View (Section 16)
   ├── 🆕 Multiple action options (not just A/R)
   ↓
[DEPLOY / SAVE]
   ↓
[🆕 LOG TO DECISION_LOG] (Section 16)
   ↓
[🆕 LOG TO TAMPER-EVIDENT AUDIT] (hash chain)
```

## 10.2 State Schema (Pydantic v2)

```python
from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime

class TPMState(BaseModel):
    # === INPUT ===
    user_request: str
    session_id: str
    user_id: str = "default"

    # === 🆕 CLARIFICATION ===
    raw_input: str
    clarification_history: list[dict] = []
    confirmed_intent: dict | None = None
    intent_confidence: float = 0.0

    # === 🆕 INQUIRY-FIRST ===
    user_provided_facts: dict = {}  # ที่ user บอกเอง
    inquiry_log: list[dict] = []

    # === RECON ===
    recon_queries: list[dict] = []
    recon_results_l1: list[dict] = []
    recon_results_l2: list[dict] = []
    recon_results_l3: list[dict] = []
    recon_merged: str | None = None
    recon_quality: float = 0.0
    recon_complete: bool = False

    # === 🆕 DATA CLASSIFICATION ===
    data_classifications: dict = {}  # field_name → level
    egress_log: list[dict] = []

    # === PLANNING ===
    subtasks: list[dict] = []
    task_plan_reasoning: str | None = None

    # === EXECUTION ===
    subtask_results: dict = {}
    tools_used: list[dict] = []  # 🆕 บันทึกทุก tool call

    # === QUALITY ===
    audit_passed: bool = False
    audit_failures: list[str] = []
    retry_count: int = 0
    anti_patterns_hit: list[str] = []
    measured_confidences: dict = {}  # 🆕 measured ไม่ใช่ self-reported

    # === HUMAN GATE ===
    human_action: str | None = None  # APPROVE / APPROVE_WITH_EDITS / etc.
    human_feedback: str | None = None

    # === 🆕 DECISION TRACE (Section 16) ===
    decisions_made: list[dict] = []
    alternatives_considered: list[dict] = []
    failed_attempts: list[dict] = []

    # === CONTROL ===
    frozen: bool = False
    final_output: dict | None = None
    error: str | None = None

    # === LINEAGE ===
    model_versions: dict = {}
    prompt_hashes: list[str] = []
    langgraph_trace_id: str | None = None
    generated_at: datetime = Field(default_factory=datetime.now)
```

## 10.3 Handoff Packet (ระหว่าง nodes)

```python
class HandoffPacket(BaseModel):
    # Source/Destination
    from_node: str
    to_node: str

    # Status
    stage: str
    success: bool
    measured_confidence: float  # ไม่ใช่ self-reported!
    confidence_breakdown: dict

    # Reasoning
    reasoning: str  # ทำไมตัดสินใจแบบนี้
    alternatives_considered: list[dict]  # 🆕 อะไรที่พิจารณาแล้วไม่เลือก
    failed_attempts: list[dict]  # 🆕 อะไรที่ลองแล้วไม่ได้ผล

    # Data
    payload: dict
    classification: str  # PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED

    # Audit trail
    retry_count: int = 0
    error_msg: str | None = None
    timestamp: datetime
    prompt_hash: str  # SHA256[:8] ของ prompt ที่ใช้
```

## 10.4 LangGraph Implementation Sketch

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

def build_graph():
    workflow = StateGraph(TPMState)

    # Nodes
    workflow.add_node("clarify", clarification_node)
    workflow.add_node("inquiry_first", inquiry_first_node)
    workflow.add_node("recon", recon_master_node)
    workflow.add_node("search_loop", search_loop_node)
    workflow.add_node("quality_check", quality_check_node)
    workflow.add_node("planner", task_planner_node)
    workflow.add_node("workers", worker_dispatch_node)
    workflow.add_node("auditor", auditor_node)
    workflow.add_node("hell_loop", hell_loop_node)
    workflow.add_node("human_gate", human_gate_node)
    workflow.add_node("save", save_output_node)
    workflow.add_node("log_decision", decision_log_node)  # 🆕
    workflow.add_node("log_audit", tamper_evident_log_node)  # 🆕

    # Entry
    workflow.set_entry_point("clarify")

    # Edges
    workflow.add_conditional_edges(
        "clarify",
        lambda s: "inquiry_first" if s.confirmed_intent else "clarify",
    )
    workflow.add_edge("inquiry_first", "recon")
    workflow.add_edge("recon", "search_loop")
    workflow.add_edge("search_loop", "quality_check")
    workflow.add_conditional_edges(
        "quality_check",
        lambda s: "planner" if s.recon_complete else "inquiry_first",
    )
    workflow.add_edge("planner", "workers")
    workflow.add_edge("workers", "auditor")
    workflow.add_conditional_edges(
        "auditor",
        lambda s: "human_gate" if s.audit_passed else (
            "hell_loop" if s.retry_count < 3 else "log_audit"
        ),
    )
    workflow.add_edge("hell_loop", "workers")
    workflow.add_conditional_edges(
        "human_gate",
        lambda s: "save" if s.human_action == "APPROVE" else "workers",
    )
    workflow.add_edge("save", "log_decision")
    workflow.add_edge("log_decision", "log_audit")
    workflow.add_edge("log_audit", END)

    # Checkpoint
    checkpointer = SqliteSaver.from_conn_string(".tpm_context/langgraph_checkpoint.db")
    return workflow.compile(checkpointer=checkpointer)
```


---

# 11. Worker Subgraphs

## 11.1 หลักการ: Tool-First (ไม่ใช่ AI-First)

แต่ละ Worker เลือก tool ก่อนใช้ AI:

```
[Worker received task]
   ↓
[Tool Registry Search]  ← Section 13
   ├── มี tool ที่ทำได้แล้ว → ใช้ tool โดยตรง
   ├── มี tool ที่ทำได้ส่วนหนึ่ง → ใช้ tool + AI สำหรับส่วนที่เหลือ
   └── ไม่มี tool → AI สร้างเฉพาะกิจ + เสนอเพิ่มใน registry คืนนี้
   ↓
[Execute]
   ↓
[Self-Critique]
   ↓
[Send to Auditor]
```

## 11.2 Worker Subgraphs ทั้ง 5

### A. Report Worker

```
INPUT: Confirmed task + recon results
   ↓
[Researcher (Qwen3-1.7B Scavenger)]
   ├── ดึงข้อมูลจาก wiki + recon merged
   ├── จัดกลุ่มตาม report sections
   ↓
[Tool Search] → reportlab/python-docx/markdown?
   ├── markdown report → md2pdf tool (OSS)
   ├── docx report → python-docx (OSS)
   └── pdf report → reportlab (OSS)
   ↓
[Writer (Qwen3-8B)]
   ├── เขียนเฉพาะ "เนื้อหา" (text)
   ├── ทุก claim มี pointer
   ├── Tool ทำ formatting/layout (ไม่ใช่ AI)
   ↓
[Self-Critique] (4 questions)
   ↓
[Reviewer (Qwen3-8B different system prompt)]
   ├── ตรวจ 4 checklist
   ├── ตรวจ TPM standard formatting
   ↓
[Output: report file + lineage metadata]
```

### B. Excel Worker

```
INPUT: Data + computation requirements
   ↓
[Researcher] → ดึง spec + formula reference จาก wiki
   ↓
[Calculator (NOT AI!)]
   ├── ใช้ SymPy สำหรับ symbolic math
   ├── ใช้ NumPy สำหรับ numeric
   ├── ใช้ Pandas สำหรับ DataFrame ops
   ↓
[Coder (Qwen3-Coder-8B)]
   ├── เขียน openpyxl code (สำหรับ formula cells)
   ├── เขียน chart specifications
   ├── 🆕 ตรวจกับ Excel skill template ใน skills/
   ↓
[Tool: openpyxl] → render .xlsx
   ↓
[Validator]
   ├── eval ทุก formula ด้วย dummy data
   ├── ตรวจ circular reference
   ├── ตรวจ #REF! errors
   ↓
[Output: .xlsx + validation report]
```

### C. PPTX Worker

```
INPUT: Outline + content requirements
   ↓
[Writer (Qwen3-8B)]
   ├── สร้าง slide structure JSON
   ├── เนื้อหาแต่ละ slide (ไม่ใช่ formatting!)
   ↓
[Tool: python-pptx]
   ├── ใช้ template ใน skills/ppt_guidelines.md
   ├── render JSON → .pptx
   ├── apply Master Slide จาก company template
   ↓
[Reviewer]
   ├── ตรวจ slide count = outline?
   ├── bullets ≤ 5/slide?
   ├── ไม่มี text overflow?
   ├── มี title ทุก slide?
   ↓
[Output: .pptx]
```

### D. Vision Worker

```
INPUT: รูปภาพ + analysis goal
   ↓
[Image Preprocessing]
   ├── Magika: ตรวจประเภทไฟล์จริง
   ├── OpenCV: contrast/resize/denoise
   ↓
[Tool-based detection (run first - ฟรี + เร็ว)]
   ├── YOLO (ultralytics): bounding boxes
   ├── PaddleOCR: nameplate text
   ├── (ทำขนาน บน CPU+GPU split)
   ↓
[Vision LLM (Qwen2.5-VL-7B)]
   ├── ใช้ผล YOLO+OCR เป็น hint
   ├── เขียน structured report
   ├── ✓ Self-verify: confidence ≥ 0.8?
   ↓
[Reviewer]
   ├── ตรวจ pointer (PDF page reference)
   ├── ตรวจ severity grade
   ├── ตรวจ measured_confidence
   ↓
[Output: vision report + confidence breakdown]
```

### E. Calc Worker (สำคัญ — high stakes)

```
INPUT: Engineering problem
   ↓
[Problem Classifier]
   ├── routine? → Sequential mode
   └── high-stakes? → Hybrid Debate mode
   ↓

┌─────── Sequential Mode ─────────┐
│ [Researcher] dig wiki             │
│    ↓                              │
│ [Formula Selector (Qwen3-8B)]     │
│    ├── เลือกจาก library ที่ verify│
│    └── return formula_id          │
│    ↓                              │
│ [Calculator (SymPy)] ← NOT AI!    │
│    └── execute + unit check       │
│    ↓                              │
│ [Interpreter (Qwen3-8B)]          │
│    └── ตีความผลลัพธ์ให้ user      │
└──────────────────────────────────┘

┌─────── Hybrid Debate Mode ─────────┐
│ [Round 1: Proposer (Qwen3-8B)]      │
│   "วิศวกรเสนอ root cause             │
│    + assumptions ทั้งหมด"           │
│    ↓                                │
│ [Round 2: Devil's Advocate]         │
│   (Qwen3-8B different prompt)       │
│   "QC เจ้าหาช่องโหว่"                │
│    ↓                                │
│ [Round 3: Synthesis (Qwen3-27B CPU)]│
│   รับ + ปฏิเสธ → final + disputes   │
│    ↓                                │
│ [Calculator (SymPy)] for any math   │
└────────────────────────────────────┘
   ↓
[Output: analysis + resolved_disputes]
```

## 11.3 Hybrid Debate Pattern

**เมื่อใช้ Debate (high-stakes only):**
- Root cause analysis ที่ไม่ชัดเจน
- Safety-critical decision
- Cost of error สูง
- ข้อมูลขัดแย้งกันมาก

**เมื่อใช้ Sequential:**
- งาน routine (ดึง → แปลง → บันทึก)
- งานที่มีกฎ explicit (LOTO, standard formula)
- ต้องการความเร็ว

```python
def should_use_debate(task: Task) -> bool:
    return any([
        task.safety_critical,
        task.has_conflicting_data,
        task.cost_of_error > threshold,
        task.confidence < 0.6,
    ])
```


---

# 12. Auditor + Quality Control

## 12.1 Auditor (8-Layer Defense)

```python
class Auditor:
    """
    ทุก output ของ Worker ผ่าน 8 layers
    """

    async def audit(self, output: WorkerOutput) -> AuditResult:
        results = {}

        # Layer 1: Pydantic schema (structure)
        results["schema"] = self.validate_schema(output)

        # Layer 2: 🆕 Multi-strategy CoVe (fix P0-3 from v4)
        results["cove"] = await self.multi_strategy_cove(output)

        # Layer 3: Quality checker
        results["quality"] = await self.quality_check(output)

        # Layer 4: Format-specific (PPT/Excel/Doc)
        results["format"] = self.format_specific_check(output)

        # Layer 5: Safety inspector
        results["safety"] = self.safety_check(output)

        # Layer 6: Arize Phoenix semantic eval
        results["semantic"] = await self.phoenix_eval(output)

        # Layer 7: 🆕 Measured confidence (fix P0-2)
        results["confidence"] = await self.measured_confidence_check(output)

        # Layer 8: 🆕 Egress check (data classification)
        results["egress"] = self.egress_check(output)

        return AuditResult(
            passed=all(r.passed for r in results.values()),
            details=results
        )
```

## 12.2 🆕 Multi-Strategy CoVe (แก้ P0-3 จาก v4)

```python
async def multi_strategy_cove(self, claim: Claim, source: Source) -> VerifyResult:
    """
    OCR PDFs มี errors → ห้ามใช้ regex strict match อย่างเดียว
    """
    # Strategy 1: Numeric extraction + tolerance
    claimed_nums = extract_numbers_with_units(claim.text)
    source_nums = extract_numbers_with_units(source.page_text)

    for cn in claimed_nums:
        match = find_closest(cn, source_nums, tolerance_pct=0.5)
        if match:
            if not units_compatible(cn.unit, match.unit):
                return VerifyResult(
                    passed=False,
                    reason=f"Unit mismatch: {cn.unit} vs {match.unit}",
                    severity="conflict"  # ไม่ใช่ reject — flag conflict
                )
            return VerifyResult(passed=True, confidence=0.95,
                                 ocr_drift=cn.value - match.value)

    # Strategy 2: Fuzzy string match
    if fuzzy_match(claim.text, source.page_text, threshold=0.85):
        return VerifyResult(passed=True, confidence=0.75)

    # Strategy 3: Semantic match
    sim = embed_similarity(claim.text, source.page_text)
    if sim > 0.80:
        return VerifyResult(
            passed="semantic",
            confidence=0.60,
            warning="Verified by meaning - human check recommended"
        )

    # Strategy 4: All failed
    return VerifyResult(
        passed=False,
        candidates=top_3_similar(claim.text, source.page_text)
    )
```

## 12.3 🆕 Egress Check

```python
async def egress_check(self, output: dict) -> EgressResult:
    """
    ก่อน output ถูก save/sent → ตรวจไม่มีข้อมูล CONFIDENTIAL ที่จะรั่ว
    """
    text = serialize(output)

    # Detection patterns
    patterns = {
        "personnel_id": r"\b\d{13}\b",  # Thai ID
        "salary_data": r"(เงินเดือน|salary|baht/month).*\d+",
        "internal_codes": r"INT-\d{6}",
        "phone": r"0\d{8,9}",
    }

    findings = []
    for category, pattern in patterns.items():
        matches = re.findall(pattern, text)
        if matches:
            findings.append((category, matches))

    # ถ้าพบ + destination ของ output คือ external → block
    if findings and output.destination in ["external_api", "shared_drive"]:
        return EgressResult(
            passed=False,
            block=True,
            findings=findings,
            recommendation="Sanitize before egress"
        )

    return EgressResult(passed=True)
```

## 12.4 Hell Loop (เหมือน v4 แต่ปรับ escalation)

```python
async def hell_loop(state: TPMState):
    if state.retry_count == 0:
        # First retry: same worker + Auditor feedback
        return await retry_with_feedback(state)

    elif state.retry_count == 1:
        # Second retry: + anti_patterns context
        anti_patterns = load_relevant_anti_patterns(state.subtask)
        return await retry_with_context(state, anti_patterns)

    elif state.retry_count == 2:
        # Third retry: bigger model
        return await retry_with_heavy_model(state)  # Qwen3-27B CPU

    elif state.retry_count == 3:
        # 🆕 Last resort: structured human help
        await save_to_dlq(state)  # Dead Letter Queue
        await notify_user(
            urgency="high",
            message=f"AI ทำ task '{state.user_request}' ไม่สำเร็จหลัง 3 รอบ\n"
                    f"ขอความช่วยเหลือ: ดู DLQ ที่ .tpm_context/dlq/{state.session_id}.json"
        )
        return state.with_status("ESCALATED_TO_HUMAN")
```

---

# 13. Tool Registry & Auto-Discovery

> **🆕 ใหม่ใน v5.0 — ระบบให้ AI เลือก tool ก่อนเขียนโค้ดเอง**

## 13.1 หลักการ

> **"ก่อนให้ AI สร้าง tool ใหม่ ให้ค้นว่ามี tool ที่ทำได้แล้วไหม"**

## 13.2 Tool Registry Schema

```yaml
# .tpm_context/tool_registry.json
tools:
  - id: "openpyxl_excel_writer"
    type: "oss_library"
    package: "openpyxl"
    version: "3.1.5"
    license: "MIT"
    capabilities:
      - "create_xlsx"
      - "write_formula"
      - "create_chart"
      - "conditional_format"
    input_schema: {...}
    output_schema: {...}
    example_code: |
      from openpyxl import Workbook
      wb = Workbook()
      ws = wb.active
      ws['A1'] = 'Hello'
      wb.save('out.xlsx')
    success_rate_7d: 0.98
    avg_duration_ms: 250
    usage_count_7d: 47
    bandit_passed: true
    approved_by_human: true
    approved_at: "2026-04-15T10:00:00"
    last_used: "2026-05-01T09:30:00"

  - id: "stress_calc_sympy"
    type: "ai_generated_wrapper"
    package: "sympy"
    wrapper_path: ".tpm_context/local_tools/wrappers/stress_calc.py"
    capabilities:
      - "calculate_stress"
      - "calculate_strain"
    success_rate_7d: 1.0
    bandit_passed: true
    approved_by_human: true

  - id: "searxng_search"
    type: "self_hosted_service"
    endpoint: "http://localhost:8888"
    capabilities:
      - "web_search"
      - "image_search"
    cost_per_call: 0.0  # FREE
```

## 13.3 Tool Search Index (Semantic)

```python
# ChromaDB collection สำหรับ tool search
class ToolSearchIndex:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.create_collection("tools")

    def index_tools(self, tools: list[Tool]):
        for t in tools:
            doc = f"""
            Name: {t.id}
            Type: {t.type}
            Capabilities: {', '.join(t.capabilities)}
            Description: {t.description}
            Example: {t.example_code[:200]}
            """
            self.collection.add(
                documents=[doc],
                metadatas=[{
                    "id": t.id,
                    "type": t.type,
                    "license": t.license,
                    "success_rate": t.success_rate_7d,
                    "approved": t.approved_by_human,
                }],
                ids=[t.id]
            )

    async def find_for_task(self, task_description: str) -> list[Tool]:
        results = self.collection.query(
            query_texts=[task_description],
            n_results=5,
            where={
                "approved": True,
                "success_rate": {"$gte": 0.8}
            }
        )
        return results
```

## 13.4 Tool Selection Flow

```python
async def select_tool_for_task(task: str) -> ToolDecision:
    # 1. ค้นใน registry
    candidates = await tool_index.find_for_task(task)

    if not candidates:
        return ToolDecision(
            decision="NO_TOOL_FOUND",
            recommendation="Check if AI should generate one tonight"
        )

    # 2. ถ้ามี OSS exact match → ใช้ทันที
    oss_match = [c for c in candidates if c.type == "oss_library"]
    if oss_match:
        best = max(oss_match, key=lambda c: c.success_rate_7d)
        return ToolDecision(
            decision="USE_OSS",
            tool=best,
            reasoning=f"OSS library {best.package} ทำงานนี้ได้ตรง"
        )

    # 3. ถ้ามี AI-generated wrapper ที่ approve แล้ว → ใช้
    approved_wrappers = [c for c in candidates
                          if c.type == "ai_generated_wrapper"
                          and c.approved_by_human]
    if approved_wrappers:
        return ToolDecision(
            decision="USE_WRAPPER",
            tool=approved_wrappers[0]
        )

    # 4. ไม่มีอะไรพร้อมใช้ → AI สร้างเฉพาะกิจ + เพิ่มใน night queue
    await night_queue.add(
        action="create_tool",
        for_task=task,
        priority="medium"
    )
    return ToolDecision(
        decision="AI_INLINE_FALLBACK",
        warning="No mature tool — using AI inline. Tool creation queued for tonight."
    )
```

## 13.5 Auto-Preload (เร่งความเร็ว)

```python
# ทุกเช้าตอน startup
def auto_preload():
    # ดึง tool ที่ใช้บ่อย ≥ 3 ครั้งใน 7 วัน
    frequently_used = registry.query(
        "SELECT * FROM tools WHERE usage_count_7d >= 3 ORDER BY usage_count_7d DESC LIMIT 10"
    )

    for tool in frequently_used:
        if tool.type == "oss_library":
            # Import ค้างไว้ใน memory
            importlib.import_module(tool.package)

        elif tool.type == "ai_generated_wrapper":
            # Load wrapper module
            spec = importlib.util.spec_from_file_location(tool.id, tool.wrapper_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            preloaded[tool.id] = mod

    log.info(f"Preloaded {len(preloaded)} tools")
```

## 13.6 Tool Creation Pipeline (สำหรับ Night Cycle)

```
[Morning detection: tool needed for task X]
   ↓
[Add to night_queue with priority]
   ↓
═══════════════════ Night Time ═══════════════════
   ↓
[Step 1: Search OSS first]
   ├── PyPI search
   ├── GitHub search (top stars + recent)
   ├── npm search (if JS task)
   ↓
[Step 2: ถ้าเจอ OSS → wrap with thin wrapper]
   ↓
[Step 3: ถ้าไม่เจอ → AI generate]
   ├── Coder (Qwen3-Coder-8B) สร้าง code
   ├── Self-test ด้วย dummy input
   ├── Bandit security scan
   ├── Ruff lint
   ├── Pytest (ถ้ามี test cases)
   ↓
[Step 4: Save to .tpm_context/local_tools/wrappers/]
   ↓
[Step 5: Add to morning_brief]
   "เช้าวันนี้ผมสร้าง tool X — กรุณา review + approve"
```

---

# 14. Activity Tracking

> **🆕 ใหม่ใน v5.0 — Track ทั้งใน workspace และ "ตอนไม่ได้ใช้ AI"**

## 14.1 Architecture

```
┌────────────────────────────────────────────────────────┐
│  TIER 1: Inside AI Session (continuous)                 │
│    - ทุก AI tool call                                  │
│    - ทุก decision                                       │
│    - ทุก file read/write                                │
│    Storage: event_log.db                                │
├────────────────────────────────────────────────────────┤
│  TIER 2: Workspace Activity (when not in AI session)   │
│    - File events ใน tpm_workspace/                     │
│    - Terminal commands                                  │
│    - Clipboard (opt-in only)                           │
│    Storage: activity_log/inside_ai/                    │
├────────────────────────────────────────────────────────┤
│  🆕 TIER 3: Outside Activity (with explicit consent)   │
│    - Application focus time                             │
│    - File operations outside workspace                 │
│    - Web visits (browser extension)                    │
│    Storage: activity_log/outside_ai/                   │
│    Consent: explicit opt-in + can stop anytime         │
└────────────────────────────────────────────────────────┘
```

## 14.2 Tier 1: AI Session Tracking

```python
# wrap ทุก tool call
class AITrackingWrapper:
    def wrap(self, tool):
        async def wrapped(*args, **kwargs):
            start = time.time()
            try:
                result = await tool(*args, **kwargs)
                self.log_call(
                    tool=tool.__name__,
                    args=sanitize(args, kwargs),
                    duration_ms=(time.time() - start) * 1000,
                    success=True,
                    result_preview=str(result)[:200]
                )
                return result
            except Exception as e:
                self.log_call(
                    tool=tool.__name__,
                    args=sanitize(args, kwargs),
                    duration_ms=(time.time() - start) * 1000,
                    success=False,
                    error=str(e)
                )
                raise
        return wrapped
```

## 14.3 Tier 2: Workspace Activity Tracker

```python
# /home/claude/scripts/activity_tracker.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class WorkspaceTracker(FileSystemEventHandler):
    def __init__(self, db):
        self.db = db
        self.workspace = Path("~/tpm_workspace").expanduser()

    def on_created(self, event):
        self.log(action="create", path=event.src_path, type=event.event_type)

    def on_modified(self, event):
        if not event.is_directory:
            self.log(action="modify", path=event.src_path)

    def on_moved(self, event):
        self.log(action="move", src=event.src_path, dst=event.dest_path)

    def log(self, **kwargs):
        kwargs["timestamp"] = datetime.now().isoformat()
        kwargs["session_in_progress"] = is_ai_session_active()
        self.db.execute(
            "INSERT INTO workspace_events (data) VALUES (?)",
            (json.dumps(kwargs),)
        )

# Terminal command tracking via shell hook
# .bashrc / .zshrc:
# trap 'tpm-track-cmd "$BASH_COMMAND"' DEBUG
```

## 14.4 🆕 Tier 3: Outside-AI Activity Tracker

**สำคัญ: Explicit consent + ระยะเวลาจำกัด**

```python
# /home/claude/scripts/outside_tracker.py

CONSENT_FILE = "~/.tpm_context/outside_consent.json"

def request_consent():
    print("""
    🔒 Outside-AI Activity Tracking — ขออนุญาต

    ระบบจะ track:
    ✓ application ที่เปิดและเวลาที่ใช้
    ✓ file operations ทุกที่ในเครื่อง
    ✓ ⚠️ browser visits (เฉพาะถ้าติดตั้ง browser extension)

    เพื่ออะไร:
    - ดูว่าคุณทำอะไรซ้ำๆ ตอนไม่ใช้ AI
    - คืนนี้สร้าง tool ให้กดปุ่มเดียวรัน

    ระบบจะไม่ track:
    ✗ password, banking
    ✗ private messages
    ✗ ข้อมูลส่วนตัวอื่นๆ

    Auto-stop: 30 วันต้อง renew consent
    Stop anytime: rm ~/.tpm_context/outside_consent.json
    """)

    answer = input("ยินยอม? [y/N]: ")
    if answer.lower() == 'y':
        # บันทึก consent
        json.dump({
            "agreed_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
            "scope": ["app_focus", "file_ops_global"],
            "exclude_patterns": [
                "*password*", "*banking*",
                "**/Documents/Personal/*",
                "*.kdbx", "*.gpg"
            ]
        }, open(CONSENT_FILE, 'w'))
```

**Application focus tracking (Linux + WSL2):**

```python
# ใช้ wmctrl + xdotool บน Linux/X11
# หรือ active-win-listener บน WSL2 (ผ่าน WSLg)

import subprocess
import time

def track_active_app():
    if not has_consent():
        return

    last_app = None
    last_switch = time.time()

    while has_consent() and not_expired():
        # ดู active window title
        try:
            result = subprocess.run(
                ['xdotool', 'getactivewindow', 'getwindowname'],
                capture_output=True, text=True, timeout=1
            )
            current_app = parse_app_name(result.stdout)
        except:
            current_app = "unknown"

        if current_app != last_app:
            duration = time.time() - last_switch
            log_app_focus(
                app=last_app,
                start=last_switch,
                duration_sec=duration
            )
            last_app = current_app
            last_switch = time.time()

        time.sleep(5)  # poll ทุก 5 วินาที (ลด overhead)
```

**File ops global tracking (with exclusion):**

```python
# ใช้ inotify (Linux) หรือ ReadDirectoryChangesW (Windows)
class GlobalFileTracker:
    def __init__(self, exclude_patterns):
        self.exclude = exclude_patterns

    def should_track(self, path):
        for pattern in self.exclude:
            if fnmatch.fnmatch(path, pattern):
                return False
        return True

    def on_event(self, event):
        if not self.should_track(event.path):
            return

        log_file_op(
            action=event.type,
            path=event.path,
            timestamp=datetime.now()
        )
```

## 14.5 Pattern Detection (รันทุกคืน)

```python
async def detect_patterns_nightly():
    """
    รันใน Night Cycle ดูว่ามี pattern อะไรซ้ำ
    """
    # Pattern A: copy/move file ซ้ำ
    file_copies = analyze_file_ops_for_repeating_copies(
        timeframe_days=7,
        min_repetitions=3
    )
    if file_copies:
        for pattern in file_copies:
            await propose_tool(
                type="file_copy_automation",
                trigger=pattern.trigger,
                action=pattern.action
            )

    # Pattern B: เปิด apps เดิมตามลำดับ
    app_sequences = analyze_app_focus_for_sequences(
        timeframe_days=7,
        min_repetitions=5
    )
    if app_sequences:
        for seq in app_sequences:
            await propose_tool(
                type="workspace_setup_macro",
                apps=seq.apps,
                description=f"Open {seq.apps} in order — saves {seq.time_saved} sec"
            )

    # Pattern C: AI ทำ task เดิมซ้ำ (Tier 1)
    repeated_ai_tasks = analyze_ai_calls_for_patterns(
        timeframe_days=7,
        min_repetitions=3
    )
    for task in repeated_ai_tasks:
        await propose_tool(
            type="ai_task_to_oss_replacement",
            task_signature=task.signature,
            search_for_oss_alternative=True
        )

    # Pattern D: User edit file แล้ว AI ค่อยเข้ามา → automate edit
    edit_then_ai = analyze_edit_then_ai_patterns(timeframe_days=7)
    for pattern in edit_then_ai:
        await propose_macro(
            edit_steps=pattern.edits,
            ai_call=pattern.ai_request
        )
```

## 14.6 Morning Brief Format

```markdown
# Morning Brief — 1 พ.ค. 2026

## 🔍 Patterns ที่พบเมื่อคืน

### 1. คุณเปิด Excel แล้ว PDF แล้ว Word ตามลำดับ 6 ครั้ง/สัปดาห์
**ข้อเสนอ:** สร้าง shortcut "เปิด workspace แบบ daily inspection"
- เปิด: maintenance_log.xlsx + manual_boiler.pdf + report_template.docx
- Time saved: ~30 วินาที/วัน × 5 = 2.5 นาที/สัปดาห์
- Status: ✓ สร้างไว้แล้ว — รอ approve
- File: `.tpm_context/local_tools/scripts/daily_inspection_workspace.sh`
- [ APPROVE ] [ REJECT ] [ EDIT ]

### 2. AI ทำ "อ่าน Excel + สรุป" ซ้ำ 8 ครั้งใน 7 วัน
**ข้อเสนอ:** ใช้ pandas + tabulate แทน AI สำหรับ task นี้
- พบ OSS: `pandas` + `tabulate` ทำได้ดีกว่า AI
- Reduce token cost: ~80%
- Speed up: 10x
- Status: ✓ Wrapper สร้างแล้ว
- File: `.tpm_context/local_tools/wrappers/excel_summarize.py`
- Test passed: 5/5 cases
- [ APPROVE ] [ REJECT ] [ EDIT ]

### 3. คุณ rename file pattern เดิม 4 ครั้ง
- old → new pattern: `report_*.pdf` → `2026-MM-DD_report.pdf`
- ข้อเสนอ: bulk rename script
- File: `.tpm_context/local_tools/scripts/auto_rename_reports.py`
- [ APPROVE ] [ REJECT ]

## 📊 ระบบทำงานเมื่อคืน

- Replayed 12 daytime tasks
- Found 2 discrepancies (ดูส่วนถัดไป)
- Created 3 tool proposals
- Backed up to GitHub: ✓
- Audit log integrity: ✓
```


---

# 15. Night Cycle (Self-Correction)

> **🆕 ใหม่ใน v5.0 — ทุกคืนระบบตรวจตัวเอง**

## 15.1 ภาพรวม

```
┌──────────────────────────────────────────────────────────┐
│  Night Cycle Schedule (22:00 - 06:00)                     │
├──────────────────────────────────────────────────────────┤
│  22:00  Activity Pattern Analysis (Section 14.5)          │
│  22:30  Tool Creation/Search Queue                         │
│  23:30  🆕 Daytime Task Replay (Self-Correction)          │
│  01:30  🆕 Discrepancy Analysis                           │
│  02:30  🆕 Self-Correction Proposals                      │
│  03:30  Wiki Updates (incremental OpenKB)                  │
│  04:00  Cache Refresh (ChromaDB Layer 2 staleness)        │
│  04:30  Code Quality (ruff + bandit + pytest)              │
│  05:00  GitHub Backup + Hash Chain Verify                 │
│  05:30  Generate Morning Brief                             │
│  06:00  Cleanup + Wait for User                           │
└──────────────────────────────────────────────────────────┘
```

**กฎเหล็ก:**
- รันต่อเมื่อปลั๊กไฟเสียบ (battery > 80% ก็ผ่านได้)
- ตัด night cycle ทันที ถ้า CPU temp > 75°C
- Resume ที่ 22:00 ของวันถัดไป

## 15.2 🆕 Daytime Task Replay (สำคัญที่สุด)

```python
async def daytime_replay():
    """
    Re-run ทุก task ของวันด้วย model ที่ใหญ่กว่า (ช้ากว่า)
    เปรียบเทียบกับ output จริง → หา discrepancy
    """

    # 1. ดึง tasks ของวันที่ approve แล้ว
    today_tasks = db.query("""
        SELECT * FROM completed_tasks
        WHERE DATE(completed_at) = DATE('now', '-1 day')
        AND human_action = 'APPROVE'
    """)

    # 2. โหลด heavy model (CPU mode)
    heavy_model = await load_model("qwen3-27b", mode="cpu")

    discrepancies = []

    for task in today_tasks:
        # 3. Replay ด้วย model ใหญ่
        replay_result = await heavy_model.execute(
            prompt=task.original_prompt,
            context=task.context,
            tools=task.tools_used,
        )

        # 4. Compare กับ original
        diff = compare(
            original=task.output,
            replay=replay_result,
            modes=[
                "structural",      # โครงสร้างต่างไหม
                "factual",         # ตัวเลข/fact ต่างไหม
                "semantic",        # ความหมายต่างไหม
                "completeness",    # ครบไหม
            ]
        )

        if diff.significant:
            discrepancies.append({
                "task_id": task.id,
                "type": diff.type,
                "original": task.output,
                "replay": replay_result,
                "diff": diff,
                "severity": diff.severity,
            })

    return discrepancies
```

## 15.3 🆕 Discrepancy Analysis

```python
async def analyze_discrepancies(discrepancies: list):
    """
    หาสาเหตุว่าทำไม daytime กับ replay ต่างกัน
    """
    causes = []

    for disc in discrepancies:
        # ใช้ Hermes 35B (ถ้าโหลดได้) สำหรับ deep analysis
        analysis = await deep_analyze(
            disc,
            questions=[
                "ตัวไหนน่าจะถูก daytime หรือ replay?",
                "ทำไม daytime ผิด (ถ้าผิด)?",
                "ป้องกันยังไง next time?",
                "ต้องเพิ่ม anti-pattern ไหม?",
                "ต้องสร้าง tool ใหม่ไหม?",
                "Prompt ต้องปรับไหม?",
            ]
        )

        causes.append({
            "discrepancy_id": disc.id,
            "likely_correct": analysis.likely_correct,  # daytime/replay/both/neither
            "root_cause": analysis.root_cause,
            "fix_proposals": analysis.fixes,
        })

    return causes
```

## 15.4 🆕 Self-Correction Proposals

```python
async def propose_corrections(causes: list):
    """
    สร้างข้อเสนอแก้ไขสำหรับ user approve เช้าวันถัดไป
    """
    proposals = []

    for cause in causes:
        for fix in cause.fix_proposals:
            if fix.type == "prompt_update":
                # ปรับ prompt template
                old_prompt = load_prompt(fix.target_prompt_id)
                new_prompt = fix.suggested_prompt

                proposal = {
                    "type": "PROMPT_UPDATE",
                    "what": f"แก้ prompt ของ {fix.target_node}",
                    "why": cause.root_cause,
                    "diff": generate_diff(old_prompt, new_prompt),
                    "test_results": await ab_test(old_prompt, new_prompt,
                                                    test_set=load_relevant_golden()),
                    "risk": fix.risk_level,
                }

            elif fix.type == "anti_pattern_add":
                proposal = {
                    "type": "ANTI_PATTERN_ADD",
                    "what": f"เพิ่ม anti-pattern: {fix.pattern_name}",
                    "why": cause.root_cause,
                    "pattern_file": create_anti_pattern_file(fix),
                }

            elif fix.type == "tool_creation":
                proposal = {
                    "type": "TOOL_CREATE",
                    "what": f"สร้าง tool: {fix.tool_name}",
                    "why": "AI ทำงานนี้ผิดบ่อย — ใช้ deterministic tool ดีกว่า",
                    "oss_search_results": await search_oss(fix.capability),
                    "fallback_code": fix.generated_code,
                }

            elif fix.type == "rag_enrichment":
                proposal = {
                    "type": "RAG_ENRICHMENT",
                    "what": "เพิ่มเอกสาร: " + fix.suggested_doc,
                    "why": "Wiki ขาดข้อมูลที่ทำให้ AI ตีความผิด",
                    "search_query_for_user": fix.what_to_find,
                }

            proposals.append(proposal)

    # Save สำหรับ morning brief
    save_to_morning_brief(proposals)
    return proposals
```

## 15.5 ตัวอย่าง Discrepancy & Correction

```yaml
discrepancy_001:
  task_id: "T20260430-142"
  task_summary: "วิเคราะห์ root cause Boiler #2 trip"
  daytime_result: "Root cause: low water level"
  replay_result: "Root cause: low water level + faulty level switch"

  diff:
    type: "incompleteness"
    severity: "medium"
    detail: "Replay พบ secondary cause ที่ daytime ตกหล่น"

  analysis:
    likely_correct: "replay"  # ลึกกว่า
    root_cause: "Daytime model (Qwen3-8B) ตอบเร็วเกินไป
                  ไม่ได้ explore secondary causes อย่างเต็มที่"

  fix_proposals:
    - type: "prompt_update"
      target: "calc_worker.root_cause_prompt"
      change: "เพิ่ม 'ระบุทุก contributing factor ไม่ใช่แค่ primary'"

    - type: "anti_pattern_add"
      pattern: "single_cause_bias"
      description: "เมื่อ AI ตอบ root cause เร็ว → มักตอบสาเหตุเดียว
                     ทั้งที่ส่วนใหญ่ความล้มเหลวมีหลายปัจจัย"

morning_brief_entry:
  title: "🔍 พบ task ที่อาจตอบไม่ครบ — Boiler #2 root cause"
  message: |
    เมื่อวานผมตอบว่า root cause = low water level
    เมื่อคืนผม replay ด้วย model ใหญ่ขึ้น → พบว่าน่าจะมี
    secondary cause: faulty level switch ด้วย

    คุณคิดว่ายังไง?
    [ A: เห็นด้วย — เพิ่ม secondary cause ใน report ]
    [ B: ไม่เห็นด้วย — primary อย่างเดียวพอ ]
    [ C: ต้องตรวจ field ก่อน ตอบไม่ได้ตอนนี้ ]
```

## 15.6 Other Night Tasks

### Code Quality
```bash
# ทุกคืน 04:30
ruff check .tpm_context/local_tools/
bandit -r .tpm_context/local_tools/ -ll  # low+high severity
pytest .tpm_context/local_tools/tests/ -v --tb=short
```
ถ้าพบ issue → flag in morning brief

### Cache Freshness Check
```python
async def check_chromadb_staleness():
    stale = []
    for chunk in chroma_collection.get_all():
        meta = chunk.metadata
        ttl_days = meta.get("freshness_ttl_days", 30)
        crawl_date = meta.get("crawl_date")
        if days_since(crawl_date) > ttl_days:
            stale.append(chunk)

    # Re-crawl stale chunks
    for chunk in stale:
        new_content = await crawl(chunk.metadata["source_url"])
        update_chunk(chunk, new_content)
```

### Hash Chain Integrity
```python
async def verify_audit_log():
    rows = audit_db.query("SELECT * FROM audit_log ORDER BY id")
    for i, row in enumerate(rows[1:], 1):
        prev = rows[i-1]
        expected_hash = sha256(f"{prev.current_hash}|{row.event_json}").hexdigest()
        if expected_hash != row.current_hash:
            raise TamperedAuditLog(f"Chain broken at row {i}")

    log.info("✓ Audit log integrity verified")
```

---

# 16. Explanation & Transparency System

> **🆕 ใหม่ใน v5.0 — สำหรับสร้าง progress report + ให้ user เรียนรู้**

## 16.1 Decision Log Schema

ทุก decision ของ AI บันทึก:

```yaml
decision_id: "D-20260501-001"
session_id: "S-20260501-morning"
task: "วิเคราะห์ Boiler #2 PM"

what: |
  ผมเลือกใช้ openpyxl สำหรับอ่าน maintenance log
  + Qwen3-8B สำหรับสรุป + python-pptx สำหรับ slide

why_this:
  - "openpyxl: OSS library เร็ว แม่น 100% สำหรับ Excel"
  - "Qwen3-8B: เร็วพอสำหรับ summary ภาษาไทย"
  - "python-pptx: ใช้ template ของบริษัทได้"

why_not_others:
  - alternative: "pandas"
    rejected_because: "ซับซ้อนเกินสำหรับ simple read"
  - alternative: "Qwen3-14B"
    rejected_because: "ช้ากว่า 3-4x โดยคุณภาพดีขึ้นเล็กน้อย"
  - alternative: "AI generate from scratch"
    rejected_because: "Tool > AI สำหรับงาน deterministic"

what_failed:
  - attempt: "ใช้ regex เพื่อ extract timestamps"
    failed_because: "format ไม่สม่ำเสมอ"
    fixed_by: "ใช้ dateparser library แทน"

  - attempt: "อ่าน sheet ที่ index 0"
    failed_because: "sheet 0 เป็น summary ไม่ใช่ raw data"
    fixed_by: "อ่าน sheet 'Boiler' โดยชื่อ"

confidence_journey:
  initial: 0.6  # ตอนได้ task แรก
  after_clarification: 0.85
  after_data_loaded: 0.9
  final: 0.92

tools_used:
  - openpyxl (read xlsx)
  - dateparser (parse timestamps)
  - tabulate (format output)
  - Qwen3-8B (summarize)
  - python-pptx (create slide)

duration_breakdown:
  clarification: 12s
  data_loading: 3s
  ai_summary: 18s
  slide_creation: 5s
  audit: 4s
  total: 42s

cost:
  ai_tokens_in: 4521
  ai_tokens_out: 1893
  external_api_calls: 0
  baht_estimate: 0  # all local
```

## 16.2 Progress Report Generator

```python
async def generate_progress_report(period_days: int = 7):
    """
    สร้างรายงานความคืบหน้าจาก decision_log
    สำหรับส่งหัวหน้าหรือใช้ใน internship report
    """
    decisions = load_decisions(period_days)

    report = {
        "period": f"{period_days} วันล่าสุด",
        "total_tasks": len(decisions),
        "task_categories": classify_tasks(decisions),
        "tools_used": aggregate_tools(decisions),
        "patterns_learned": load_anti_patterns_added(period_days),
        "tools_created": load_tools_created(period_days),
        "discrepancies_found": load_discrepancies(period_days),
        "self_corrections_made": load_self_corrections(period_days),
        "highlights": pick_top_examples(decisions),
        "challenges_overcome": load_failed_attempts(period_days),
    }

    # Generate Markdown + PPTX
    md_report = template_render("templates/progress_report.md", report)
    pptx_report = template_render_pptx("templates/progress_slide.pptx", report)

    return {
        "markdown": md_report,
        "pptx": pptx_report,
    }
```

## 16.3 Educational Mode

User สามารถเปิด "explain mode" สำหรับเรียนรู้:

```python
class EducationalExplainer:
    """
    อธิบายแต่ละ step ในระดับที่ user ต้องการเข้าใจ
    """

    LEVELS = {
        "beginner": {
            "show_steps": True,
            "show_tools": True,
            "show_code": False,
            "show_internals": False,
            "language": "casual",
        },
        "intermediate": {
            "show_steps": True,
            "show_tools": True,
            "show_code": True,
            "show_internals": False,
            "language": "technical_with_explanation",
        },
        "advanced": {
            "show_steps": True,
            "show_tools": True,
            "show_code": True,
            "show_internals": True,
            "language": "technical",
        }
    }

    async def explain_step(self, step, level="intermediate"):
        config = self.LEVELS[level]
        explanation = []

        if config["show_steps"]:
            explanation.append(f"📋 ขั้นตอน: {step.action}")

        if config["show_tools"]:
            explanation.append(f"🔧 ใช้ tool: {step.tool_used} เพราะ {step.why_tool}")

        if config["show_code"]:
            explanation.append(f"```python\n{step.code}\n```")

        if config["show_internals"]:
            explanation.append(f"🔍 Internals: prompt_hash={step.prompt_hash}")
            explanation.append(f"   measured_confidence={step.confidence}")

        return "\n".join(explanation)
```

**Example:**
```
User: "อธิบายให้ฟังหน่อย ทำไมเลือก openpyxl ไม่เลือก pandas"

AI (intermediate level):
📚 มาเริ่มจากตรงนี้:

ทั้งสอง library อ่าน Excel ได้ แต่:

🔧 openpyxl:
   - เน้น openxml format (Excel จริงๆ)
   - อ่านสูตรในเซลล์ได้ (.xlsx ที่มี formula)
   - เขียนกลับได้พร้อม chart, conditional format
   - เร็วสำหรับ task เดียว

📊 pandas:
   - เน้น DataFrame (data analysis)
   - ดีกว่าถ้าต้อง aggregate, pivot, merge
   - ช้ากว่าถ้าแค่อ่าน + เขียน cell

Task ของเราคือ "อ่าน maintenance log + ดูข้อมูล PM"
- ไม่ต้อง aggregation ซับซ้อน → openpyxl เพียงพอ
- ต้องอ่านสูตรในเซลล์ที่คนเขียนไว้ → openpyxl ทำได้ pandas ทำไม่ได้

นี่คือเหตุผลที่ผมเลือก openpyxl ครับ

อยากเห็น code ไหม? หรือต้องการเปรียบเทียบเพิ่ม?
```

## 16.4 Auto-Generate Slide for Progress Report

```python
async def auto_generate_progress_slides():
    """
    ทุกวันศุกร์ 17:00 generate progress slides สำหรับ weekly meeting
    """
    week_data = await collect_week_data()

    slides = [
        {
            "title": "📊 สัปดาห์ที่ผ่านมา",
            "content": f"""
            • Tasks ทำสำเร็จ: {week_data.tasks_completed}
            • Tools ที่สร้าง: {week_data.tools_created}
            • Anti-patterns ที่เรียนรู้: {week_data.anti_patterns}
            • Self-corrections: {week_data.corrections}
            """
        },
        {
            "title": "🎯 ตัวอย่าง Task เด่น",
            "content": render_top_3_tasks(week_data),
        },
        {
            "title": "🔧 Tools ใหม่ที่สร้าง",
            "content": render_tools_created(week_data),
        },
        {
            "title": "📈 Quality Metrics",
            "chart": create_chart({
                "approval_rate": week_data.approval_rate,
                "first_try_success": week_data.first_try_success,
                "avg_task_duration": week_data.avg_duration,
            }),
        },
        {
            "title": "💡 สิ่งที่เรียนรู้",
            "content": format_learnings(week_data.learnings),
        },
        {
            "title": "📅 สัปดาห์หน้า",
            "content": format_plan(week_data.next_week_plan),
        },
    ]

    pptx_file = create_pptx(slides, template="company_template.pptx")

    # Save to outputs
    return pptx_file
```


---

# 17. Open-Source First Catalog

> **🆕 ใหม่ใน v5.0 — กฎเหล็กข้อ 1: ทุก capability หา open-source ก่อน เขียนเองเป็นทางสุดท้าย**

## 17.1 หลักการ

```
ลำดับการตัดสินใจเมื่อต้องการ capability ใหม่:

1. มี OSS library / tool ที่ทำได้แล้วไหม?    → ใช้ทันที
2. มี OSS service ที่ self-host ได้ไหม?      → setup self-host
3. มี free API tier ที่พอใช้ไหม?              → ใช้ free tier
4. ต้องเขียนเองจริงๆ?                         → AI ช่วยร่าง → human review → bandit scan
                                              → บันทึกใน local_tools/ai_generated/
```

**กฎย้ำ:** AI **ห้าม** เขียน Python script ทำงานที่มี library standard ทำได้แล้ว (เช่น คำนวณ stress, อ่าน Excel, parse PDF) — เสียเวลา + bug rate สูง

## 17.2 Catalog ครบทุก Capability (อัปเดต เม.ย. 2026)

### A. Document Generation

| Capability | OSS Tool | License | สถานะ | หมายเหตุ |
|---|---|---|---|---|
| สร้าง .docx | **python-docx** | MIT | ✅ ใช้ | heading, table, image |
| สร้าง PDF | **reportlab** | BSD | ✅ ใช้ | chart + table วิศวกรรม |
| สร้าง PDF (Markdown→PDF) | **WeasyPrint** | BSD | ✅ Backup | สวยกว่าถ้ามี HTML/CSS |
| OCR PDF → Markdown | **zerox** + **marker** | MIT | ✅ ใช้ | marker ดีกว่าสำหรับ layout ซับซ้อน |
| Extract ตาราง PDF | **camelot-py** + **tabula-py** | MIT/Apache 2.0 | ✅ ใช้ | camelot lattice mode สำหรับตารางมีเส้น |
| Parse PDF metadata | **pypdf** | BSD | ✅ ใช้ | pure-Python ไม่มี dep |

### B. Excel / Data

| Capability | OSS Tool | License | สถานะ | หมายเหตุ |
|---|---|---|---|---|
| อ่าน/เขียน .xlsx | **openpyxl** | MIT | ✅ ใช้หลัก | สูตร + chart + conditional format |
| Excel chart ขั้นสูง | **xlsxwriter** | BSD | ✅ ใช้ | chart ซับซ้อนกว่า openpyxl |
| DataFrame manipulation | **pandas** + **polars** | BSD/MIT | ✅ ใช้ | polars เร็วกว่า 10-100x |
| คำนวณวิศวกรรม | **sympy** | BSD | ✅ ใช้ | symbolic + ผลถูก 100% |
| Numeric calc | **numpy** + **scipy** | BSD | ✅ ใช้ | base ของทุกอย่าง |
| Unit conversion | **pint** | BSD | ✅ ใช้ | บังคับ unit-aware (กัน N vs kgf bug) |

### C. PowerPoint / Slide

| Capability | OSS Tool | License | สถานะ |
|---|---|---|---|
| สร้าง/แก้ .pptx | **python-pptx** | MIT | ✅ ใช้หลัก |
| Convert pptx → img/pdf | **LibreOffice CLI** | MPL 2.0 | ✅ ใช้ (ส่ง preview ใน Chainlit) |

### D. Vision / Image

| Capability | OSS Tool | License | สถานะ | หมายเหตุ |
|---|---|---|---|---|
| Object detection (รอยร้าว) | **ultralytics (YOLOv8/v10)** | AGPL-3.0 | ⚠️ ใช้ — ระวัง license | AGPL = ต้อง share derivative ถ้า deploy public |
| Object detection (alternative) | **torchvision detection models** | BSD | ✅ ใช้ทดแทน | ถ้ากังวล AGPL |
| Image preprocess | **opencv-python** | Apache 2.0 | ✅ ใช้ |
| File type detection | **magika** (Google) | Apache 2.0 | ✅ ใช้ | ตรวจ MIME จริงๆ ก่อน process |
| Image hashing (dedup) | **imagehash** | BSD | ✅ ใช้ |
| Crack/Defect ML model | **CrackNet, DeepCrack** | MIT | 🔄 ลอง | trained บน concrete crack — เผื่อใช้ทดแทน YOLO custom |

### E. Web / Data Fetch

| Capability | OSS Tool | License | สถานะ |
|---|---|---|---|
| Meta-search (Layer 3) | **SearXNG** | AGPL-3.0 | ✅ ใช้หลัก (self-hosted) |
| Headless scraping + AI cleanup | **Crawl4AI** | MIT | ✅ ใช้ |
| Main content extraction | **trafilatura** | Apache 2.0 | ✅ Backup ของ Crawl4AI |
| Browser automation | **Playwright** + **playwright-cli** | Apache 2.0 | ✅ ใช้สำหรับ ERP web |
| HTML parser | **beautifulsoup4** + **lxml** | MIT/BSD | ✅ Helper |
| HTTP client | **httpx** | BSD | ✅ ใช้ (async-first) |
| Robots.txt respect | **urllib.robotparser** | PSF | ✅ ใช้ |

### F. Knowledge / RAG / Wiki

| Capability | OSS Tool | License | สถานะ |
|---|---|---|---|
| Compile docs → wiki | **OpenKB** | Apache 2.0 | ✅ ใช้หลัก (Layer 1) |
| Vectorless tree nav | **PageIndex** | MIT | ✅ ใช้หลัก |
| Vector DB (Layer 2) | **ChromaDB** | Apache 2.0 | ✅ ใช้ |
| BM25 hybrid retrieval | **rank_bm25** | Apache 2.0 | ✅ ใช้ร่วม |
| Reranker | **bge-reranker-v2-m3** (Ollama) | Apache 2.0 | ✅ ใช้ |
| Long-term memory | **Mem0** | Apache 2.0 | ✅ ใช้ (self-hosted) |
| Wiki viewer | **Obsidian** | proprietary (free desktop) | ⚠️ free แต่ไม่ open — เก็บ vault เป็น Markdown ธรรมดา ย้ายได้ทุกเมื่อ |

### G. Orchestration / Agent Framework

| Capability | OSS Tool | License | สถานะ |
|---|---|---|---|
| Workflow graph | **LangGraph** | MIT | ✅ ใช้หลัก |
| Base components | **langchain-core** | MIT | ✅ ใช้ |
| Type validation | **Pydantic v2** | MIT | ✅ บังคับ |
| Local LLM serving | **Ollama** + **llama.cpp** | MIT/MIT | ✅ ใช้ |
| OpenAI-compatible proxy | **LiteLLM** | MIT | ✅ ใช้ (router) |
| Model fallback chain | **LiteLLM router** | MIT | ✅ ใช้ |

### H. Observability / Eval

| Capability | OSS Tool | License | สถานะ |
|---|---|---|---|
| LLM trace + prompt versioning | **Langfuse** | MIT | ✅ ใช้ (self-hosted) |
| RAG eval + hallucination | **Arize Phoenix** | Apache 2.0 | ✅ ใช้ (self-hosted) |
| Prompt optimization (Phase 5) | **DSPy** | MIT | 🔄 Phase 5 |
| Confidence calibration | **Calibration library (custom)** | — | 🆕 ใน local_tools |

### I. Code Quality / DevSecOps

| Capability | OSS Tool | License | สถานะ |
|---|---|---|---|
| Lint Python | **ruff** | MIT | ✅ บังคับ |
| Security scan | **bandit** | Apache 2.0 | ✅ บังคับ |
| Type check | **mypy** หรือ **pyright** | MIT | ✅ ใช้ |
| Secret scan | **detect-secrets** | Apache 2.0 | ✅ pre-commit hook |
| Unit test | **pytest** | MIT | ✅ บังคับ |
| Coverage | **coverage.py** | Apache 2.0 | ✅ ใช้ |
| Dep vulnerability | **pip-audit** | Apache 2.0 | ✅ weekly cron |

### J. System / Monitoring

| Capability | OSS Tool | License | สถานะ |
|---|---|---|---|
| File event monitor | **watchdog** | Apache 2.0 | ✅ passive_logger |
| System info | **psutil** | BSD | ✅ thermal/power |
| GPU monitor | **GPUtil** + **nvidia-ml-py** | MIT/BSD | ✅ |
| Window/app tracking (WSL) | **active-win-listener** + **xdotool** | MIT/MIT | ✅ outside_tracker |
| File hashing | **xxhash** | BSD | ✅ ใช้ (เร็วกว่า MD5 5-10x) |

### K. UI / Control Center

| Capability | OSS Tool | License | สถานะ |
|---|---|---|---|
| Chat UI + Human Gate | **Chainlit** | Apache 2.0 | ✅ ใช้หลัก |
| Diff view component | **diff-match-patch** + Chainlit element | Apache 2.0 | ✅ |
| Markdown render | **markdown-it-py** | MIT | ✅ |

### L. Protocol / Integration

| Capability | OSS Tool | License | สถานะ |
|---|---|---|---|
| MCP server SDK | **@modelcontextprotocol/sdk** | MIT | ✅ ใช้ |
| MCP servers (community) | **mcp.so registry** | MIT มากที่สุด | ✅ ค้นก่อนเขียนเอง |
| A2A protocol (Phase 5) | **A2A reference impl** | Apache 2.0 | 🔄 Phase 5 |

## 17.3 Decision Tree: AI สร้างเองหรือใช้ Library?

```python
def decide_tool_source(capability: str) -> ToolSource:
    """
    Auto-decision tree ก่อน AI เขียนโค้ด
    """
    # 1. ค้น tool_registry (semantic via ChromaDB)
    existing = tool_registry.search_semantic(capability, top_k=5)
    if existing and existing[0].similarity > 0.85:
        return UseExisting(tool=existing[0])

    # 2. ค้น OSS catalog (จาก Section 17.2 + GitHub trending search)
    oss_match = oss_catalog.search(capability)
    if oss_match:
        return InstallOSS(
            package=oss_match.pip_name,
            license=oss_match.license,
            need_license_review=oss_match.is_copyleft  # AGPL/GPL ต้อง review
        )

    # 3. ค้น MCP registry
    mcp_match = mcp_registry.search(capability)
    if mcp_match:
        return UseMCP(server=mcp_match)

    # 4. ค้น Free API tier
    api_match = free_api_catalog.search(capability)
    if api_match:
        return UseFreeAPI(provider=api_match)

    # 5. ทางสุดท้าย: AI เขียนเอง
    return AIGenerate(
        warning="No OSS found — AI will draft, requires human review + bandit scan",
        save_to=".tpm_context/local_tools/ai_generated/"
    )
```

## 17.4 License Compliance (สำคัญสำหรับการใช้งานจริง)

```yaml
license_policy:
  always_safe:
    - MIT
    - BSD (2-clause, 3-clause)
    - Apache 2.0
    - PSF (Python)
    - MPL 2.0 (file-level copyleft)

  review_required:
    - LGPL: OK ถ้า dynamic link, ระวัง static link
    - AGPL: ❌ avoid ถ้า deploy public network — บังคับ share derivative
    - GPL v2/v3: ❌ avoid in commercial product
    - SSPL (MongoDB-style): ❌ avoid

  proprietary_acceptable:
    - Free desktop tier (Obsidian) — ใช้ได้แต่ vault portable เสมอ
    - Free API tier (Tavily, Brave) — ใช้ได้แต่ห้าม lock-in

  red_flags:
    - "non-commercial only"
    - "research only"
    - "evaluation only"
    - missing LICENSE file
```

**กฎ:** ทุก dependency ที่ติดตั้ง → บันทึก license + version ใน `.tpm_context/local_tools/installed/MANIFEST.yaml`

```yaml
# .tpm_context/local_tools/installed/MANIFEST.yaml
- name: openpyxl
  version: "3.1.5"
  license: MIT
  installed_at: "2026-05-01T10:00:00"
  used_by: ["excel_worker", "pm_schedule_reader"]
  alternative_to: "AI-generated openpyxl scripts"
- name: ultralytics
  version: "8.3.x"
  license: AGPL-3.0
  installed_at: "2026-05-02T15:00:00"
  used_by: ["vision_worker"]
  warning: "AGPL — review before public deploy"
  fallback: "torchvision detection models"
```


---

# 18. Microsoft Copilot Integration

> **🆕 v5.0 — แทน "Enterprise/Corporate API" ใน v4.0 ที่ระบุไม่ชัด**

## 18.1 ทำไมต้องมี Cloud Fallback

ถึงแม้ระบบหลักจะ local-first แต่บางสถานการณ์ต้อง escalate ออก cloud:

```yaml
escalation_triggers:
  - hell_loop_exhausted: retry 3 ครั้งแล้วยังไม่ผ่าน Auditor
  - high_stakes_validation: safety-critical → ต้องการ second opinion
  - rare_domain_query: เช่น regulation ใหม่ที่ยังไม่อยู่ใน wiki
  - user_explicit: user กด "Ask cloud AI" ใน Chainlit
```

แต่ห้าม escalate กรณี:
- ❌ ข้อมูล classification = CONFIDENTIAL หรือ RESTRICTED
- ❌ มี personnel data, ERP data, P&ID
- ❌ มี part number / supplier proprietary

## 18.2 ทำไมเลือก Microsoft Copilot

| ข้อ | Microsoft Copilot Student | OpenAI API | Anthropic API |
|---|---|---|---|
| ค่าใช้จ่าย | **ฟรี** (ผ่าน student email) | $$ | $$$ |
| Data residency | Microsoft commercial trust boundary | OpenAI servers | Anthropic servers |
| Model | GPT-4 + GPT-4 Turbo + DALL·E 3 | GPT-4o | Claude Sonnet/Opus |
| Tool calling | ✅ | ✅ | ✅ |
| Compliance | EU/Asia datacenters available | US-centric | US-centric |
| Integration | Office 365 (PDF, Word, Excel) | API only | API only |

**สำหรับนักศึกษาฝึกงาน:** Microsoft 365 A1 ฟรี (Office + Copilot Chat) — ใช้ผ่าน student email

## 18.3 Architecture

```
[Local LangGraph Pipeline]
    ↓
[Auditor fails after retry=3]
    ↓
[Egress Check] ← ตรวจ classification
    ├── BLOCKED → escalate ไป Human (ไม่ส่งออก)
    └── ALLOWED ↓
    ↓
[Sanitizer] ← ลบ tag number, supplier name, equipment ID
    ↓
[Microsoft Copilot API] ← primary cloud fallback
    ├── Success → ตรวจ output → Human Gate
    └── Fail ↓
    ↓
[Azure OpenAI] ← secondary fallback (need Azure subscription)
    ↓
[Result back to local pipeline]
```

## 18.4 Setup

### 18.4.1 Microsoft Copilot Chat (free tier — ผ่าน Microsoft Graph)

```python
# .env
MS_TENANT_ID=xxx
MS_CLIENT_ID=xxx
MS_CLIENT_SECRET=xxx
MS_USER_PRINCIPAL_NAME=intern@university.ac.th

# microsoft_copilot.py
from azure.identity import ClientSecretCredential
import httpx

class CopilotClient:
    def __init__(self):
        self.credential = ClientSecretCredential(
            tenant_id=os.getenv("MS_TENANT_ID"),
            client_id=os.getenv("MS_CLIENT_ID"),
            client_secret=os.getenv("MS_CLIENT_SECRET"),
        )

    async def chat(self, prompt: str, context: dict = None):
        token = self.credential.get_token("https://graph.microsoft.com/.default")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://graph.microsoft.com/v1.0/copilot/chats",
                headers={"Authorization": f"Bearer {token.token}"},
                json={
                    "message": prompt,
                    "context": context or {},
                }
            )
        return response.json()
```

### 18.4.2 Azure OpenAI (paid fallback — ถ้ามี Azure subscription)

```python
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-12-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

response = client.chat.completions.create(
    model="gpt-4o",  # หรือ "gpt-4o-mini" สำหรับ cost
    messages=[{"role": "user", "content": prompt}],
    max_tokens=1000,
)
```

## 18.5 Egress Sanitizer

```python
class EgressSanitizer:
    """
    ลบข้อมูล sensitive ก่อนส่งออก cloud
    """

    SENSITIVE_PATTERNS = [
        (r"P-\d{3,4}", "[PUMP_TAG]"),           # P-101 → [PUMP_TAG]
        (r"B-\d{1,3}", "[BOILER_TAG]"),         # B-2 → [BOILER_TAG]
        (r"[A-Z]{2,4}-\d{3,5}", "[EQUIP_TAG]"), # equipment tag pattern
        (r"\bSKF\s+\d+", "[BEARING_PART]"),     # SKF 6205 → [BEARING_PART]
        (r"นาย\s*[ก-๙]+", "[PERSON_NAME]"),     # ชื่อภาษาไทย
        (r"\b\d{10}\b", "[PHONE]"),             # เบอร์โทร
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]"),
    ]

    def sanitize(self, text: str) -> Tuple[str, dict]:
        sanitized = text
        replacements = {}
        for pattern, placeholder in self.SENSITIVE_PATTERNS:
            matches = re.findall(pattern, sanitized)
            for m in matches:
                if m not in replacements.values():
                    key = f"{placeholder}_{len(replacements)}"
                    replacements[key] = m
                    sanitized = sanitized.replace(m, key, 1)
        return sanitized, replacements

    def desanitize(self, text: str, replacements: dict) -> str:
        result = text
        for key, original in replacements.items():
            result = result.replace(key, original)
        return result
```

**Workflow:**
1. Local pipeline พยายาม → Auditor fail
2. Sanitizer ลบ tag/name → ส่ง Copilot
3. Copilot ตอบ (เห็นแค่ `[PUMP_TAG]`)
4. Desanitize: insert tag จริงกลับ
5. Auditor ตรวจ output รอบใหม่
6. Human Gate (บังคับเสมอเมื่อใช้ cloud)

## 18.6 Audit Trail สำหรับ Cloud Calls

```sql
-- audit_log.db
CREATE TABLE cloud_calls (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP,
    provider TEXT,             -- "microsoft_copilot" | "azure_openai"
    reason TEXT,               -- ทำไมต้อง escalate
    classification TEXT,       -- ก่อน sanitize ต้อง PUBLIC/INTERNAL เท่านั้น
    sanitized_input_hash TEXT, -- SHA-256 ของ input ที่ส่ง
    response_hash TEXT,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_usd REAL,
    user_approved_at TIMESTAMP,
    human_review_after BOOLEAN  -- ผ่าน Human Gate หรือยัง
);
```


---

# 19. Portable AI Team

> **🆕 v5.0 — สำหรับการย้ายระบบไปโปรเจคต่อไปหลังจบฝึกงาน**

## 19.1 หลักการ "Knowledge Travels With You"

หลังจบฝึกงาน 6 เดือน — สิ่งที่สะสมมาไม่ควรหายไปกับองค์กร

```yaml
portable_assets:
  100_percent_yours:
    - .tpm_context/wiki/             # ความรู้ทั่วไป (ไม่ใช่ proprietary)
    - .tpm_context/skills/            # workflow templates
    - .tpm_context/anti_patterns/     # บทเรียนความล้มเหลว
    - .tpm_context/local_tools/       # OSS scripts
    - .tpm_context/prompts/           # prompt templates
    - .tpm_context/domain_knowledge/  # FMEA, RCM, KPI definitions
    - models/                         # GGUF files (re-downloadable)

  must_leave_behind:
    - raw_data/                       # original PDFs, Excel
    - .tpm_context/wiki/sources/      # สรุปเอกสารบริษัท
    - .tpm_context/wiki/entities/     # equipment, supplier ของบริษัท
    - audit_log.db                    # internal incident logs

  case_by_case:
    - .tpm_context/wiki/concepts/     # OK ถ้า concept ทั่วไป (TRIZ); ตัดถ้ามี proprietary
    - .tpm_context/wiki/synthesis/    # ตรวจ case-by-case
```

## 19.2 MIGRATION.md Template

```markdown
# MIGRATION.md — ย้ายระบบ TPM AI ไปโปรเจคใหม่

## ก่อนย้าย: Sanitization Checklist (ทำใน week สุดท้ายก่อนจบ)

- [ ] รัน `scripts/portable_audit.py` — list ทุกไฟล์ที่มี proprietary ref
- [ ] ตรวจ wiki/concepts/ — ลบ section ที่อ้างถึง equipment ของบริษัท
- [ ] ตรวจ skills/ — แทนที่ "Boiler #2" เป็น "[EQUIPMENT]"
- [ ] ตรวจ anti_patterns/ — ลบ context ที่ระบุชื่อ supplier
- [ ] รัน egress_sanitizer แบบ deep scan
- [ ] รัน detect-secrets full scan
- [ ] รัน bandit scan ทุก local_tools/

## ย้ายข้อมูล

\`\`\`bash
# 1. Snapshot portable assets
mkdir -p ~/tpm_portable_$(date +%Y%m%d)
rsync -av --exclude-from=.tpm_portable_exclude \
    .tpm_context/ \
    ~/tpm_portable_$(date +%Y%m%d)/

# 2. Strip metadata
python scripts/strip_proprietary.py ~/tpm_portable_$(date +%Y%m%d)/

# 3. Bundle
cd ~ && tar -czf tpm_portable_$(date +%Y%m%d).tar.gz tpm_portable_$(date +%Y%m%d)/

# 4. Backup ไป GitHub (private repo) — ดู Section 20
\`\`\`

## ตั้งระบบใหม่ (โปรเจคต่อไป)

\`\`\`bash
# 1. Clone framework code (จาก GitHub)
git clone https://github.com/<you>/tpm-ai-framework.git new_project
cd new_project

# 2. Restore portable knowledge
tar -xzf ~/tpm_portable_*.tar.gz -C .tpm_context/

# 3. Re-download models
bash scripts/download_models.sh

# 4. Setup new raw_data/ (เริ่มจากศูนย์)
mkdir raw_data/{pdf_manuals,excel_logs,images,word_specs}

# 5. Run first compile
openkb compile --vault .tpm_context/wiki/

# 6. Verify
pytest tests/golden_dataset/
\`\`\`

## สิ่งที่ "ตามไปด้วยฟรี"

- ทุก skill workflow ที่ AI สรุปไว้ → ใช้ทันทีกับเครื่องใหม่
- ทุก anti-pattern → ไม่ต้องเรียนรู้ผิดพลาดเดิม
- ทุก local_tools → กดปุ่มเดียวรันได้
- ทุก domain knowledge (FMEA, RCM, TRIZ) → portable
- prompt templates ที่ DSPy optimize แล้ว → ดีกว่า prompt ตั้งต้น

## เวลาประหยัดเมื่อย้ายเทียบกับเริ่มใหม่

| Step | เริ่มใหม่ | ย้ายของเดิม |
|---|---|---|
| Model setup | 2 วัน | 0.5 วัน |
| Knowledge compile แรก | 2-8 ชม. + รวบรวมเอกสาร 1-2 สัปดาห์ | 30 นาที (incremental) |
| Skills/workflows | 1-3 เดือน เรียนรู้ | ใช้ทันที |
| Anti-patterns | ต้องเรียนผิดเอง | ใช้ทันที |
| **รวม** | **2-4 เดือน** | **2-3 วัน** |
```

## 19.3 Portable Audit Script

```python
# scripts/portable_audit.py
"""
สแกนหา proprietary content ทั้งหมดก่อนย้าย
"""
import re
from pathlib import Path

PROPRIETARY_PATTERNS = [
    # Equipment tags
    (r"\b(?:B|P|C|HX|V|T)-\d{1,4}\b", "equipment_tag"),
    # Specific company names (จาก config)
    (r"บริษัท\s+\S+", "company_name"),
    # Specific person names
    (r"คุณ\s*[ก-๙]{2,}", "person_name"),
    # Internal phone
    (r"ext\.\s*\d{3,4}", "internal_phone"),
    # Specific addresses
    (r"นิคม\s*\S+", "industrial_estate"),
]

def audit(vault_path: Path) -> list:
    findings = []
    for md in vault_path.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        for pattern, kind in PROPRIETARY_PATTERNS:
            for match in re.finditer(pattern, text):
                findings.append({
                    "file": str(md),
                    "line": text[:match.start()].count("\n") + 1,
                    "kind": kind,
                    "match": match.group(),
                    "context": text[max(0, match.start()-50):match.end()+50],
                })
    return findings

if __name__ == "__main__":
    issues = audit(Path(".tpm_context"))
    for i in issues:
        print(f"{i['file']}:{i['line']}  [{i['kind']}]  {i['match']!r}")
    print(f"\nTotal: {len(issues)} proprietary references")
```

## 19.4 What's Replaceable vs What's Not

```
ไม่ Replace ได้ (ต้องสร้างใหม่ทุกโปรเจค):
- raw_data/ (เอกสารใหม่)
- wiki/sources/ (สรุปเอกสารใหม่)
- wiki/entities/ (อุปกรณ์ของโปรเจคใหม่)

Replace ได้ใน 2-3 วัน:
- Models (re-download จาก HuggingFace)
- ChromaDB cache (rebuild)
- Logs (เริ่มเก็บใหม่)

Portable (ตามไปฟรี):
- Skills, anti-patterns, local_tools
- Domain knowledge (FMEA, RCM, TRIZ)
- Prompt templates
- Wiki/concepts (general knowledge)
- โครงสร้างทั้งระบบ (โค้ด LangGraph + worker subgraphs)
```


---

# 20. GitHub Backup Strategy

> **🆕 v5.0 — แทน external HDD ใน v4.0 (ไม่ซื้อฮาร์ดแวร์เพิ่ม)**

## 20.1 ทำไม GitHub แทน External HDD

| ข้อ | External HDD | GitHub Private Repo |
|---|---|---|
| ค่าใช้จ่าย | 1,500-3,000 บาท | **ฟรี** (Free tier 2000 min CI/2GB) |
| Off-site backup | ❌ อยู่ที่เดียวกับเครื่อง | ✅ คนละทวีป |
| Version history | ❌ overwrite ตลอด | ✅ ทุก commit |
| Collaboration | ❌ | ✅ |
| Disaster recovery | ❌ พังไปด้วย | ✅ |
| Drawback | — | ❌ ไม่เก็บ binary ใหญ่ (>100MB) — ใช้ Git LFS |

## 20.2 Repo Structure

```
ใช้ 2 repos:

1. tpm-ai-framework  (PUBLIC ได้)
   ├── โค้ด LangGraph
   ├── worker subgraphs
   ├── scripts/
   ├── tests/
   └── docs/

2. tpm-knowledge-private  (PRIVATE บังคับ)
   ├── .tpm_context/wiki/
   ├── .tpm_context/skills/
   ├── .tpm_context/anti_patterns/
   ├── .tpm_context/decision_log/
   └── .tpm_context/prompts/
```

**ห้ามเก็บใน Git:**
- `models/` (40 GB GGUF — ใหญ่เกิน)
- `raw_data/` (proprietary)
- `chroma_db/` (rebuild ได้)
- `*.db` (SQLite — ใช้ scheduled SQL dump แทน)
- `.env` (secrets)

## 20.3 .gitignore ที่ต้องมี

```gitignore
# Models (re-downloadable)
models/
*.gguf
*.bin
*.safetensors

# Raw proprietary data
raw_data/

# Caches
chroma_db/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.mypy_cache/

# Databases (ใช้ dump ของวันนี้)
*.db
*.sqlite
*.sqlite3

# Secrets
.env
.env.*
!.env.example
*.key
*.pem
credentials.json

# OS
.DS_Store
Thumbs.db
desktop.ini

# Logs (rotated separately)
logs/
*.log

# Outputs (regenerable)
output/

# Temp
*.tmp
*.swp
*~
```

## 20.4 Auto-Commit + Push Schedule

```python
# scripts/github_backup.py
"""
Auto-commit ทุก 4 ชม. + push ทุกวัน 23:00
"""
import subprocess
from datetime import datetime
import sqlite3

def auto_backup():
    # 1. Dump SQLite databases เป็น SQL files (Git-friendly)
    for db in ["audit_log.db", "event_log.db", "tool_registry.json"]:
        if db.endswith(".db"):
            dump_sqlite(db, f".tpm_context/dumps/{db}.sql")

    # 2. Commit knowledge repo
    cwd = ".tpm_context"
    subprocess.run(["git", "-C", cwd, "add", "."], check=True)

    status = subprocess.check_output(
        ["git", "-C", cwd, "status", "--porcelain"]
    ).decode()
    if not status.strip():
        return  # nothing to commit

    msg = f"auto-backup {datetime.now().isoformat()}"
    subprocess.run(["git", "-C", cwd, "commit", "-m", msg], check=True)

    # 3. Push (ทุกวันเที่ยงคืน, ระหว่างวัน commit local เท่านั้น)
    if datetime.now().hour == 23:
        subprocess.run(["git", "-C", cwd, "push", "origin", "main"], check=True)

def dump_sqlite(db_path: str, out_path: str):
    conn = sqlite3.connect(db_path)
    with open(out_path, "w") as f:
        for line in conn.iterdump():
            f.write(f"{line}\n")
    conn.close()
```

**Cron schedule (.tpm_context/cron.yaml):**
```yaml
backup_jobs:
  - name: "Local commit"
    schedule: "0 */4 * * *"      # ทุก 4 ชม.
    command: "python scripts/github_backup.py --no-push"
  - name: "Daily push"
    schedule: "0 23 * * *"       # ทุกวัน 23:00
    command: "python scripts/github_backup.py --push"
  - name: "Weekly snapshot"
    schedule: "0 2 * * 0"        # อาทิตย์ 02:00
    command: "python scripts/github_backup.py --snapshot-tag"
```

## 20.5 Repo Setup (One-time)

```bash
# 1. สร้าง knowledge repo (private)
gh repo create tpm-knowledge-private --private --description "TPM AI knowledge backup"

# 2. Init ใน .tpm_context/
cd .tpm_context
git init
git remote add origin git@github.com:<you>/tpm-knowledge-private.git
git branch -M main

# 3. ใส่ .gitignore
cp ../scripts/templates/knowledge.gitignore .gitignore

# 4. First commit
git add .
git commit -m "initial knowledge snapshot"
git push -u origin main

# 5. Setup pre-commit hook (สำคัญ!)
cat > .git/hooks/pre-commit <<'EOF'
#!/bin/bash
# block secrets
if detect-secrets scan --baseline .secrets.baseline; then
    echo "❌ Secrets detected — abort commit"
    exit 1
fi
# block proprietary tags
if python ../scripts/portable_audit.py --strict; then
    echo "❌ Proprietary content detected — sanitize first"
    exit 1
fi
EOF
chmod +x .git/hooks/pre-commit
```

## 20.6 Disaster Recovery Drill (ทุกเดือน)

```bash
# จำลอง: เครื่องพังหมด — restore จาก GitHub
# (รันบนเครื่องอื่น หรือ VM)

# 1. Clone ทั้ง 2 repos
git clone git@github.com:<you>/tpm-ai-framework.git
git clone git@github.com:<you>/tpm-knowledge-private.git tpm-ai-framework/.tpm_context

# 2. Re-download models
cd tpm-ai-framework
bash scripts/download_models.sh

# 3. Restore SQLite databases from dumps
python scripts/restore_dumps.py

# 4. Verify
python scripts/health_check.py
pytest tests/golden_dataset/

# Target: เริ่มทำงานได้ภายใน 4 ชม.
```


---

# 21. Security & Selective Egress

## 21.1 Data Classification

```yaml
# .tpm_context/data_classification.yaml

PUBLIC:
  description: "ข้อมูลทั่วไปที่หาได้บนเว็บ"
  examples:
    - ISO/ASME standards (เลข standard, abstract)
    - Generic equipment specs
    - TRIZ matrix
    - Public technical bulletins
  egress_allowed: ["L3_search", "cloud_fallback", "github_public"]
  retention: unlimited

INTERNAL:
  description: "ข้อมูลภายในที่ไม่ลับมาก"
  examples:
    - Maintenance procedures (generic)
    - Training material
    - Generic process flow
  egress_allowed: ["cloud_fallback (sanitized)", "github_private"]
  retention: 5_years
  must_sanitize: ["person_names", "internal_phones"]

CONFIDENTIAL:
  description: "ข้อมูลภายในสำคัญ"
  examples:
    - Specific equipment tags + history
    - Maintenance log จริง
    - Supplier prices
    - Personnel data
  egress_allowed: ["github_private (encrypted)"]
  forbidden: ["cloud_fallback", "L3_search", "external_email"]
  retention: 7_years
  encryption_at_rest: true

RESTRICTED:
  description: "ข้อมูลที่ออกนอกเครื่องไม่ได้เด็ดขาด"
  examples:
    - P&ID drawings
    - Process safety analyses
    - Incident root cause reports
    - SIL/HAZOP analyses
    - Trade secrets / IP
  egress_allowed: []  # NONE
  forbidden: ["github_any", "cloud_any", "external_anything"]
  retention: per_legal_requirement
  encryption_at_rest: required
  audit_every_access: true
```

## 21.2 Egress Enforcement Layer

```python
class EgressGuard:
    """
    บังคับใช้ classification rules ก่อนทุก network call
    """

    @classmethod
    def check(cls, content: str, destination: str) -> EgressDecision:
        classification = cls.classify(content)
        policy = cls.load_policy()[classification]

        if destination not in policy["egress_allowed"]:
            cls.log_blocked(content, destination, classification)
            raise EgressBlocked(
                f"Cannot send {classification} to {destination}\n"
                f"Allowed: {policy['egress_allowed']}"
            )

        if "must_sanitize" in policy:
            content = EgressSanitizer.apply(content, policy["must_sanitize"])

        cls.log_allowed(content, destination, classification)
        return EgressDecision(allowed=True, sanitized=content)

    @classmethod
    def classify(cls, content: str) -> str:
        # Pattern-based
        if any(p in content for p in ["P&ID", "HAZOP", "SIL"]):
            return "RESTRICTED"

        if re.search(r"\b(?:B|P|C)-\d{1,4}\b", content):  # equipment tags
            if "maintenance log" in content.lower() or "history" in content.lower():
                return "CONFIDENTIAL"
            return "INTERNAL"

        # Semantic check (Scavenger)
        return cls.scavenger_classify(content)
```

## 21.3 Air-Gapped Verification

```bash
# scripts/airgap_check.py
# รันทุกเช้าก่อน startup — ตรวจว่าระบบ "เก็บความลับได้"

#!/bin/bash
echo "=== Air-Gap Verification ==="

# 1. Network policy: ห้าม model containers ออก internet
docker exec tpm-orchestrator curl -m 3 https://google.com && \
    echo "❌ FAIL: orchestrator can reach internet" && exit 1

# 2. Egress audit ใน last 24h
sqlite3 audit_log.db "
    SELECT classification, destination, COUNT(*)
    FROM egress_log
    WHERE timestamp > datetime('now', '-1 day')
    GROUP BY classification, destination;
"

# 3. ตรวจ unauthorized cloud calls
sqlite3 audit_log.db "
    SELECT * FROM cloud_calls
    WHERE classification IN ('CONFIDENTIAL', 'RESTRICTED');
" | grep -q . && echo "❌ FAIL: confidential leaked" && exit 1

echo "✅ Air-gap intact"
```

## 21.4 Hash-Chain Audit Log (Tamper-Evident)

```python
# audit_log.db schema
import hashlib

class AuditLog:
    """
    Hash chain: each row hash = SHA256(prev_hash + row_content)
    Tamper detection: ถ้าใครแก้ row เก่า → chain แตก
    """

    def append(self, event: dict):
        prev = self.get_last_hash()
        content = json.dumps(event, sort_keys=True)
        new_hash = hashlib.sha256(
            (prev + content).encode()
        ).hexdigest()

        self.db.execute("""
            INSERT INTO audit_log
            (timestamp, event, prev_hash, this_hash)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().isoformat(), content, prev, new_hash))

    def verify_chain(self) -> bool:
        rows = self.db.execute("""
            SELECT event, prev_hash, this_hash
            FROM audit_log ORDER BY id
        """).fetchall()

        last_hash = ""
        for event, prev_hash, this_hash in rows:
            if prev_hash != last_hash:
                return False  # tampered
            expected = hashlib.sha256(
                (last_hash + event).encode()
            ).hexdigest()
            if expected != this_hash:
                return False
            last_hash = this_hash
        return True
```

ตรวจ chain integrity ทุกคืน — Section 15.6

## 21.5 Code Security (Air-Gapped DevSecOps)

ทุก AI-generated code ต้องผ่าน:

```yaml
quality_gates:
  pre_commit:
    - ruff check
    - bandit -ll  # high+ severity only
    - detect-secrets scan
  pre_run:
    - pytest tests/local_tools/<tool_name>/
    - import sandbox check (block: os.system, subprocess.shell=True)
  approval_required:
    - human approval ก่อน register ใน tool_registry
```

**ห้าม import เด็ดขาด:**
- `subprocess.run(..., shell=True)` ที่มี user input
- `eval()`, `exec()` กับ untrusted string
- `pickle.loads()` กับ untrusted data
- ค่อนข้างห้าม: dynamic `importlib.import_module()` ที่ใช้ string จาก config

## 21.6 Forbidden Topics — L1 Forced

```yaml
# ห้าม query ผ่าน Layer 2/3 — L1 only
forced_l1_only:
  - LOTO procedures
  - Pressure limits, MAWP
  - Hazmat handling (H2S, NH3, ก๊าซระเบิด)
  - Confined space entry
  - Hot work permits
  - LEL/UEL data ของก๊าซเฉพาะ
  - SIL ratings
  - HAZOP findings
  - Specific catalyst handling
```

**เหตุผล:** L2/L3 อาจมี outdated/wrong info — life-safety ต้อง trusted source เท่านั้น


---

# 22. Implementation Phases

> **เป้าหมาย:** ค่อยๆ ทำทีละ phase ห้ามข้าม ห้ามเร่ง — แต่ละ phase ต้องผ่าน acceptance criteria ก่อน phase ถัดไป

## 22.1 Phase Overview

| Phase | ชื่อ | เวลา | Output | Acceptance |
|---|---|---|---|---|
| **Phase 0** | Workspace + Models + Safety Nets | 2-3 วัน | ระบบรัน Hello World ได้ | VRAM ≤ 7 GB idle, thermal guard ทำงาน |
| **Phase 1** | Knowledge 3-Layer + Search | 3-4 วัน | ค้นเอกสารใน wiki ได้ | PageIndex query < 2s, SearXNG return JSON |
| **Phase 2** | LangGraph Pipeline + Clarification | 4-6 วัน | Clarify → Plan → ตอบ ได้ | golden_dataset 5/10 cases pass |
| **Phase 3** | Workers + Auditor + Tools | 4-5 วัน | สร้าง report/Excel/PPTX ได้ | golden_dataset 8/10 cases pass |
| **Phase 4** | Activity Tracking + Night Cycle + UI | 3-4 วัน | Self-correction รันคืนแรก | morning brief สร้างได้ |
| **Phase 5** | DSPy Optimization + Productionization | ≥1 เดือน หลัง production | Prompt optimized | regression test ผ่าน 95%+ |

**Total Phase 0-4:** ~3-4 สัปดาห์ ที่ทำงานเต็มเวลา

## 22.2 Phase 0 — Workspace + Models + Safety Nets

### 22.2.1 Tasks

```yaml
day_1_morning:
  - [ ] สร้างโครงสร้างโฟลเดอร์ตาม Section 5.1
  - [ ] สร้าง Python venv (Python 3.11+)
  - [ ] ติดตั้ง core deps:
      pip install langgraph langchain-core pydantic
      pip install ollama chromadb pageindex
      pip install psutil GPUtil watchdog
      pip install ruff bandit pytest detect-secrets

day_1_afternoon:
  - [ ] ติดตั้ง Ollama (Windows native หรือ WSL2)
  - [ ] ดาวน์โหลด core models:
      ollama pull qwen3:8b-instruct-q4_K_M       # Orchestrator
      ollama pull qwen3:1.7b-instruct-q4_K_M     # Scavenger
      ollama pull bge-m3                          # Embedding
  - [ ] ทดสอบ inference: `ollama run qwen3:8b "สวัสดี"` ตอบเป็นภาษาไทยได้

day_2_morning:
  - [ ] เขียน thermal_guard.py (Section 3.4)
  - [ ] เขียน power_monitor.py (Section 3.3)
  - [ ] เขียน langgraph_checkpoint setup (auto save 30s)
  - [ ] ทดสอบ VRAM idle: nvidia-smi → ≤ 6.5 GB

day_2_afternoon:
  - [ ] เขียน .tpm_context/AGENTS.md (Engineering Mind Protocol — Section 9)
  - [ ] เขียน .tpm_context/SCHEMA.md (wiki structure)
  - [ ] เขียน .tpm_context/RUNBOOK.md (skeleton)
  - [ ] สร้าง data_classification.yaml (Section 21.1)
  - [ ] สร้าง .gitignore (Section 20.3)

day_3_morning:
  - [ ] สร้าง 2 GitHub repos (private):
      - tpm-ai-framework
      - tpm-knowledge-private
  - [ ] init git ใน .tpm_context, ใส่ pre-commit hook (Section 20.5)
  - [ ] commit + push ครั้งแรก

day_3_afternoon:
  - [ ] เขียน scripts/health_check.py
  - [ ] เขียน scripts/start.sh + stop.sh
  - [ ] ทดสอบ end-to-end: start → query "สวัสดี" → response → stop
```

### 22.2.2 Acceptance Criteria — Phase 0

```yaml
must_pass:
  - VRAM idle (orchestrator + scavenger loaded) ≤ 6.5 GB
  - thermal_guard pause heavy task เมื่อ CPU > 80°C
  - power_monitor switch mode เมื่อถอดปลั๊ก
  - langgraph checkpoint save ทุก 30s ลง .db
  - GitHub auto-commit ทำงาน (manual trigger)
  - health_check.py ผ่านทุกข้อ
```

## 22.3 Phase 1 — Knowledge 3-Layer + Search

### 22.3.1 Tasks

```yaml
day_1:
  - [ ] วางเอกสารใน raw_data/:
      pdf_manuals/  (อย่างน้อย 5 PDF)
      excel_logs/   (อย่างน้อย 2 Excel)
      standards/    (TRIZ matrix + 1 ISO)
  - [ ] ติดตั้ง OpenKB + PageIndex
  - [ ] รัน openkb compile --vault .tpm_context/wiki/ (กลางคืน — ใช้ 2-8 ชม.)

day_2:
  - [ ] ติดตั้ง Obsidian → Open Folder as Vault → .tpm_context/wiki/
  - [ ] ตรวจ wiki ที่ได้ — เห็น graph view
  - [ ] ติดตั้ง Obsidian Copilot plugin → เชื่อม Ollama
  - [ ] ทดสอบ query ภาษาไทย → ได้ผลที่ link กลับ source

day_3:
  - [ ] Setup ChromaDB (Layer 2):
      pip install chromadb
      สร้าง collection "web_cache"
      schema ตาม Section 6.3
  - [ ] เขียน L2 retriever (BM25 + vector hybrid)

day_4:
  - [ ] Setup SearXNG (Layer 3 — Section 6.4.1):
      docker compose up -d searxng redis
      ทดสอบ JSON API → คืนผลค้นได้
  - [ ] สมัคร Brave Search API + Tavily (free tiers)
  - [ ] ใส่ API keys ใน .env
  - [ ] เขียน L3 router (Section 6.4 พร้อม fallback chain)
  - [ ] เขียน egress_guard.py (Section 21.2) — ห้าม CONFIDENTIAL ออก L3
```

### 22.3.2 Acceptance Criteria — Phase 1

```yaml
must_pass:
  - PageIndex query "สเปคของ Boiler #2" → return chunk + page pointer ภายใน 2s
  - SearXNG query "ราคา bearing SKF 6205" → return JSON 10 results
  - L1+L2 merge → ผลรวมไม่ duplicate
  - egress_guard block CONFIDENTIAL ก่อนถึง SearXNG
  - 5 questions in golden_dataset → ค้นเจอ answer ใน wiki/cache
```

## 22.4 Phase 2 — LangGraph Pipeline + Clarification + Inquiry-First

### 22.4.1 Tasks

```yaml
day_1:
  - [ ] เขียน State schema (Pydantic v2 — Section 10.2)
  - [ ] เขียน HandoffPacket schema (Section 10.3)
  - [ ] Setup LangGraph SQLite checkpoint
  - [ ] เขียน Node: orchestrator (root entry)

day_2:
  - [ ] เขียน Clarification Loop (Section 7):
      - intent_parser
      - ambiguity_detector
      - clarification_question_generator
      - confirmation_loop (max 5 iterations)

day_3:
  - [ ] เขียน Inquiry-First (Section 8):
      - is_user_specific check
      - ask_user_first
      - Mem0 integration (จำคำตอบ user)

day_4:
  - [ ] เขียน Recon Master Node
  - [ ] เขียน Search Loop (L1 → L2 → L3) — Section 6.5
  - [ ] เขียน Conflict Detector (Section 6.6)

day_5:
  - [ ] เขียน Task Planner Node
  - [ ] เขียน Decision Logger (Section 16.1) — บันทึกทุก step
  - [ ] ติดตั้ง Langfuse self-hosted → integrate

day_6:
  - [ ] Build golden_dataset 10 cases:
      - 3 simple lookups
      - 3 PM checks
      - 2 calc tasks
      - 2 vision tasks
  - [ ] ทดสอบ end-to-end: input → clarify → plan → ตอบ
  - [ ] Dashboard Langfuse: เห็น trace ครบ
```

### 22.4.2 Acceptance Criteria — Phase 2

```yaml
must_pass:
  - คลุมเครือ prompt → AI ถาม clarify ภายใน 1s
  - ขาดข้อมูล user-specific → AI ถามก่อนค้น web
  - golden_dataset 5/10 cases ผ่าน end-to-end
  - Langfuse trace แสดงทุก node + tokens + latency
  - Decision log เขียนทุก decision มีเหตุผล
```

## 22.5 Phase 3 — Workers + Auditor + Tools

### 22.5.1 Tasks

```yaml
day_1:
  - [ ] เขียน Report Worker subgraph (Section 11.2.A)
  - [ ] เขียน Excel Worker (B)
  - [ ] ทดสอบ: "เขียน maintenance report ของ Pump P-101" → ได้ .docx

day_2:
  - [ ] ดาวน์โหลด Vision model:
      ollama pull qwen2.5-vl:7b-q4_K_M
  - [ ] เขียน VRAM swap manager (lock + swap rules)
  - [ ] เขียน Vision Worker (Section 11.2.D)
  - [ ] เขียน PPTX Worker (C)

day_3:
  - [ ] ดาวน์โหลด Coder model:
      ollama pull qwen3-coder:8b-q4_K_M (หรือ qwen2.5-coder:7b)
  - [ ] เขียน Calc Worker + SymPy integration (E)
  - [ ] เขียน Hybrid Debate (Section 11.3) สำหรับ high-stakes

day_4:
  - [ ] เขียน Auditor 8-layer (Section 12.1):
      - Pydantic schema validate
      - Multi-strategy CoVe (Section 12.2)
      - Report quality checker
      - PPTX checker
      - Excel formula validator
      - Safety inspector
      - Phoenix semantic eval
      - Uncertainty quantification
  - [ ] เขียน Hell Loop (max 3 retries → escalate)

day_5:
  - [ ] เขียน Tool Registry + auto-discovery (Section 13)
  - [ ] เขียน OSS Catalog matcher (Section 17.3)
  - [ ] Install MCP servers: excel_writer, pdf_reader
  - [ ] เขียน Tool Search Index (ChromaDB)
  - [ ] golden_dataset retest → 8/10 ผ่าน
```

### 22.5.2 Acceptance Criteria — Phase 3

```yaml
must_pass:
  - Vision swap ไม่ทำให้ VRAM เกิน 7 GB
  - Auditor ตีกลับ output ที่มีตัวเลขผิด (ทดสอบใส่ผิดตั้งใจ)
  - CoVe verify PDF pointer สำเร็จ ≥ 90%
  - Hell Loop escalate ถูกที่หลัง retry=3
  - Excel worker ผลิต .xlsx ที่ openpyxl reload ได้ + สูตรไม่เพี้ยน
  - golden_dataset 8/10 cases ผ่าน end-to-end + auditor
```

## 22.6 Phase 4 — Activity Tracking + Night Cycle + UI

### 22.6.1 Tasks

```yaml
day_1:
  - [ ] ติดตั้ง Chainlit:
      pip install chainlit
      สร้าง app.py + UI
  - [ ] Diff View component
  - [ ] Decision Trace expandable
  - [ ] Task Queue + Thermal display

day_2:
  - [ ] เขียน activity_tracker.py (Section 14):
      - Tier 1: AI session tracking (wrap tool calls)
      - Tier 2: Workspace file events (watchdog)
      - Tier 3: Outside-AI tracking (active-win-listener WSL)
  - [ ] Pattern Detector (Section 14.5)

day_3:
  - [ ] เขียน Night Cycle (Section 15):
      - Daytime task replay (ใช้ Heavy 27B)
      - Discrepancy analysis
      - Self-correction proposals
      - Morning brief generator
  - [ ] ดาวน์โหลด heavy_reasoning model (lazy load):
      ollama pull qwen3:27b-instruct-q4_K_M

day_4:
  - [ ] เขียน Tool Creation Pipeline (Section 13.6) — for night
  - [ ] เขียน Cache Freshness Check + Hash Chain Integrity (Section 15.6)
  - [ ] Schedule cron (Section 20.4 + night cycle)
  - [ ] เขียน Progress Report Generator (Section 16.2)
  - [ ] เขียน Educational Mode (Section 16.3)
  - [ ] รัน night cycle จริง 1 คืน → เช้ามาเช็ค morning brief
```

### 22.6.2 Acceptance Criteria — Phase 4

```yaml
must_pass:
  - Chainlit UI: clarify → diff → approve flow ทำงานครบ
  - Activity tracker บันทึก patterns 24 ชม.
  - Night cycle รันจริง 1 คืน → morning brief สร้างได้ ≥ 3 items
  - Hash chain integrity verify ผ่าน
  - Backup auto-commit ทุก 4 ชม. + push 23:00
  - Progress report (Section 16.4) สร้าง .pptx ได้ทุกศุกร์ 17:00
```

## 22.7 Phase 5 — DSPy Optimization + Hardening (≥ 1 เดือนหลัง production)

```yaml
prerequisites:
  - golden_dataset ≥ 50 cases (สะสมจาก approve/reject จริง)
  - audit_log ≥ 1 เดือนของการใช้งานจริง
  - confidence_calibration data พอที่จะ train

tasks:
  - [ ] ติดตั้ง DSPy
  - [ ] DSPy optimize prompt orchestrator + workers
  - [ ] Weekly regression test: ใหม่ vs baseline
  - [ ] A/B test: prompt v1 vs v2 (Langfuse)
  - [ ] ทดลอง:
      - Uncensored model สำหรับ engineering edge cases (Section 4.2 Option B)
      - Hermes 4 35B A3B บน CPU+RAM สำหรับ heavy debate
  - [ ] A2A protocol (ถ้าต้องเชื่อมกับ agent อื่นในองค์กร)

acceptance:
  - golden_dataset ผ่าน ≥ 95%
  - Avg task duration ลดลง ≥ 20% จาก baseline
  - First-try success rate ≥ 80%
```

## 22.8 Cross-Phase Dependencies

```
Phase 0 ──────────────► Phase 1
   │                      │
   ▼                      ▼
GitHub backup        OpenKB wiki + SearXNG
ทำงานทันที           เป็นพื้นฐาน Phase 2

Phase 2 ──────────────► Phase 3
   │                      │
   ▼                      ▼
Pipeline + State    Workers ใช้ State schema
Clarification       Tool registry ใช้กับ Auditor

Phase 3 ──────────────► Phase 4
   │                      │
   ▼                      ▼
Workers ผลิต output  Activity tracker เห็น tools
Auditor + Hell Loop  Night cycle replay tasks

Phase 4 ──────────────► Phase 5
   │                      │
   ▼                      ▼
Decision logs +     DSPy ใช้ logs เป็น training data
audit trail
```

## 22.9 Rollback Plan (ถ้า phase ไหนติดปัญหา)

```yaml
phase_0_fallback:
  problem: "VRAM idle เกิน budget"
  solution:
    - ลด orchestrator → Qwen3-4B-instruct-q4 (ราว 3 GB)
    - หรือ scavenger → Qwen2.5-0.5B (ราว 0.4 GB)

phase_1_fallback:
  problem: "OpenKB compile ช้า/พัง"
  solution:
    - แบ่ง raw_data เป็นย่อย ทำทีละ folder
    - หรือใช้ markitdown + ChromaDB ตรงๆ ก่อน เริ่ม PageIndex ทีหลัง

phase_2_fallback:
  problem: "Clarification loop วน infinite"
  solution:
    - ลด MIN_CONFIDENCE จาก 0.90 → 0.80
    - เพิ่ม max_iterations 5 → 3
    - เพิ่ม "skip clarify" cue ให้ user

phase_3_fallback:
  problem: "Vision worker swap ทำให้ VRAM แตก"
  solution:
    - ลอง Qwen3-VL-2B (เล็กกว่า ~2 GB)
    - หรือ run vision บน CPU+GPU split

phase_4_fallback:
  problem: "Heavy 27B ช้าเกินกลางคืน"
  solution:
    - ใช้ Qwen3-14B แทน (เร็วกว่า, คุณภาพยังดี)
    - หรือ replay เฉพาะ task ที่ confidence < 0.7
```


---

# 23. Risk Register

## 23.1 Top Risks (เรียงตาม Severity × Probability)

| # | Risk | Severity | Probability | Mitigation | Owner |
|---|---|---|---|---|---|
| R1 | VRAM 8 GB ไม่พอเมื่อ swap model | 🔴 High | 🔴 High | Section 4 swap rules + model_health_check() ก่อนทุก session | System |
| R2 | Confidential data leak ออก L3 / cloud | 🔴 High | 🟡 Medium | EgressGuard + classification + sanitizer (Section 21) | EgressGuard |
| R3 | Laptop overheat → throttle / shutdown | 🔴 High | 🟡 Medium | thermal_guard.py pause @ 80°C, work area ≥ 22°C | thermal_guard |
| R4 | OpenKB compile ครั้งแรกพัง / นาน | 🟡 Medium | 🟡 Medium | Run กลางคืน + incremental update ครั้งถัดไป | manual |
| R5 | AI hallucinate ตัวเลขใน safety-critical | 🔴 High | 🟢 Low | L1 forced + CoVe verify + Human Gate บังคับ | Auditor |
| R6 | Hash chain corrupted (audit log แตก) | 🟡 Medium | 🟢 Low | Daily verify (Section 15.6) + git backup | Night Cycle |
| R7 | Free tier API quota หมดกลางวัน | 🟡 Medium | 🟡 Medium | Quota tracker + multi-provider fallback | L3 router |
| R8 | Pre-commit secrets leaked to GitHub | 🔴 High | 🟢 Low | detect-secrets pre-commit hook (Section 20.5) | Git hook |
| R9 | Power outage during night cycle | 🟡 Medium | 🟢 Low | LangGraph checkpoint 30s + power_monitor.py | checkpoint |
| R10 | Model drift หลัง upgrade | 🟡 Medium | 🟡 Medium | Weekly regression on golden_dataset (Section 15.6) | Night Cycle |
| R11 | DSPy optimization ทำ prompt แย่ลง | 🟢 Low | 🟡 Medium | A/B test ก่อน rollout + version prompts | Phase 5 |
| R12 | Obsidian vault corruption | 🟢 Low | 🟢 Low | Markdown plain → Git history → easy restore | Git |
| R13 | Microsoft Copilot quota / outage | 🟢 Low | 🟡 Medium | Azure OpenAI fallback + skip cloud (continue local) | Cloud router |
| R14 | YOLO AGPL license issue | 🟡 Medium | 🟢 Low | torchvision detection fallback (Section 17.2.D) | License audit |
| R15 | Disk full (models + logs + chroma) | 🟡 Medium | 🟡 Medium | Daily rotate logs + weekly archive checkpoints | Cleanup cron |

## 23.2 Detailed Mitigation Plans

### R1: VRAM Exceeded

```python
# ต้องรันก่อนทุก task
def model_health_check() -> str:
    free_vram = get_free_vram_gb()
    if free_vram < 1.0:
        return "EMERGENCY: ปฏิเสธ task — รอ swap"
    if free_vram < 1.5:
        # Force unload swappable
        return "DEGRADED: unload current → swap manually"
    return "OK"
```

### R2: Data Leak

3-layer defense:
1. **Classification ก่อน** — ทุก content tagged ตอน ingest
2. **EgressGuard** — block ที่ network layer
3. **Sanitizer** — ลบ tag ก่อนส่ง cloud (last resort)

Test: Red team ทุกเดือน — ใส่ fake confidential → ลองให้หลุด

### R3: Thermal

Hardware-level: ตั้ง laptop บน cooling pad
Software: thermal_guard.py 3 thresholds (warn/throttle/critical)
Behavior: heavy task เริ่มได้เมื่อ CPU < 70°C เท่านั้น

### R5: Safety Hallucination

```yaml
defense_layers:
  1: L1 forced query (ไม่ออก web)
  2: CoVe verify PDF pointer แบบ exact match
  3: Cross-check ระหว่าง multiple sources
  4: Confidence < 70% → Human Gate บังคับ
  5: Audit log + post-mortem ถ้าหลุด
```

### R7: Free Tier Exhausted

```python
# quota_tracker.py
quotas = {
    "brave": {"used": 0, "limit": 2000, "reset": "monthly"},
    "tavily": {"used": 0, "limit": 1000, "reset": "monthly"},
}

def get_search_provider() -> str:
    # ใช้ SearXNG ก่อนเสมอ (unlimited)
    if searxng_healthy():
        return "searxng"
    # Fall back to API quota
    for name, q in quotas.items():
        if q["used"] < q["limit"] * 0.9:
            return name
    return "blocked"  # ทุกอันหมด → ถาม user
```

## 23.3 Failure Mode → Recovery

```yaml
ระบบ_crash_กลางทำงาน:
  recovery: LangGraph resume from last checkpoint (≤ 30s loss)

ไฟดับ:
  recovery: power_monitor → graceful save → resume เมื่อกลับมา

GPU_driver_crash:
  recovery: pause queue → notify user → wait restart Ollama

Model_OOM:
  recovery: Fallback chain (Section 4.5) → next smaller model

Disk_full:
  recovery: Cleanup cron → if still full → pause non-essential

Audit_chain_broken:
  recovery: notify user → freeze write → manual investigation

GitHub_push_fail:
  recovery: keep local commits → retry next interval → notify after 24h fail

Cloud_provider_down:
  recovery: skip cloud → return local result with "cloud unavailable" flag
```

## 23.4 Acceptable Loss Boundaries

```yaml
data_loss_tolerance:
  langgraph_checkpoint: ≤ 30s (auto-save interval)
  audit_log: 0 (hash chain bound to verify)
  decision_log: ≤ 5 min (batch flush)
  activity_log: ≤ 1 hour (batch flush)
  cache_chromadb: rebuildable (no tolerance)

uptime_target:
  daytime: 99% (allow 1% breaks for swap/maintenance)
  night_cycle: 95% (less critical)

response_time_target:
  clarification: ≤ 2s
  simple_lookup: ≤ 5s
  report_generation: ≤ 5 min
  vision_analysis: ≤ 30s per image
  night_replay: ≤ 6 hours total (23:00-05:00)
```


---

# 24. Quick Reference สำหรับ AI ที่จะอ่านต่อ

## 24.1 TL;DR — ระบบนี้คืออะไรใน 60 วินาที

ผู้ช่วยวิศวกรซ่อมบำรุง (TPM) บน laptop RTX 5060 8GB VRAM ใช้ LangGraph + ทีม local LLM (Qwen3-8B + Qwen3-1.7B + Vision/Coder swap) + 3-layer knowledge (OpenKB wiki + ChromaDB + SearXNG/Brave/Tavily) + night-cycle self-correction + activity tracking + open-source-first + GitHub backup + Microsoft Copilot escalation — ทุก decision อธิบายได้, clarify ก่อนทำ, ถาม user ก่อนค้น, audit ทุก output, hash-chain ทุก log

## 24.2 กฎเหล็ก 10 ข้อ (ย้ำ)

```yaml
1. Open-Source First   — หา OSS ก่อนเขียนเอง
2. Tool > AI           — ห้าม AI คิดเลข ใช้ SymPy/numpy
3. Ask Before Search   — ถาม user ก่อนค้น web
4. Confirm Before Act  — clarify intent ก่อนเริ่มงาน
5. Explain Everything  — what/why this/why not/what failed
6. Night Self-Check    — replay + diagnose + fix ทุกคืน
7. VRAM ≤ 7 GB         — ตลอดเวลา (1 GB headroom)
8. Free or Cheap       — free tier ก่อน จ่ายเมื่อจำเป็น
9. Portable Knowledge  — ย้ายโปรเจคต่อไปได้
10. Learning Together  — educational mode สำหรับ user
```

## 24.3 ไฟล์สำคัญ (Top 20)

```
.tpm_context/
├── AGENTS.md                    # บุคลิก + Engineering Mind Protocol
├── data_classification.yaml     # PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED
├── tool_registry.json           # registry tools ทั้งหมด
├── audit_log.db                 # hash-chain tamper-evident
├── langgraph_checkpoint.db      # state checkpoint 30s
├── confidence_calibration.db    # self-reported vs actual
├── wiki/index.md                # catalog ทุก wiki page
├── skills/                      # workflow templates
├── anti_patterns/               # บทเรียนความล้มเหลว
├── domain_knowledge/fmea/       # FMEA template
├── domain_knowledge/rcm/        # RCM decision tree
├── domain_knowledge/kpis/       # MTBF, MTTR, OEE
├── prompts/                     # versioned prompt templates
├── golden_dataset/              # regression test cases
├── night_cycle/morning_brief/   # เช้ามาเช็คก่อนเริ่มงาน
└── decision_log/for_reports/    # progress report material

scripts/
├── thermal_guard.py             # CPU/GPU temp monitor
├── power_monitor.py             # battery-aware
├── activity_tracker.py          # 3-tier tracking
├── github_backup.py             # auto-commit + push
├── airgap_check.py              # daily egress audit
└── portable_audit.py            # ก่อนย้ายโปรเจค

services/docker-compose.yml      # SearXNG, Langfuse, Phoenix
```

## 24.4 Commands ที่ใช้บ่อย

```bash
# Start ระบบ
bash scripts/start.sh

# Stop (graceful)
bash scripts/stop.sh

# Health check
python scripts/health_check.py

# OpenKB compile (incremental)
openkb compile --vault .tpm_context/wiki/ --incremental

# Run regression
pytest tests/golden_dataset/

# Manual night cycle
python scripts/night_cycle.py --now

# Verify hash chain
python scripts/audit/verify_chain.py

# Egress audit (24h)
python scripts/airgap_check.py

# Backup now
python scripts/github_backup.py --push

# Disaster recovery
bash scripts/disaster_recovery.sh
```

## 24.5 Decision Flowchart สำหรับ AI ที่อ่านแผนนี้

```
ก่อนทำอะไร:
  1. Read AGENTS.md (Engineering Mind Protocol)
  2. Read SCHEMA.md (wiki structure)
  3. Read this Section 24
  4. Check anti_patterns/ (อย่าทำผิดเดิม)

ก่อนเริ่ม task:
  1. Clarify intent กับ user (Section 7)
  2. Inquiry-First ถ้าขาดข้อมูล (Section 8)
  3. ตรวจ classification → routing
  4. ตรวจ tool_registry มี tool ที่ทำได้ไหม
  5. ตรวจ skills/ มี workflow เดิมไหม

ระหว่างทำ:
  1. ทุก decision → DecisionLogger.log()
  2. ทุกตัวเลข → SymPy/numpy (ห้ามคิดเอง)
  3. ทุก claim → PDF/source pointer
  4. ทุก code → ผ่าน ruff + bandit ก่อน save

ก่อนส่ง output:
  1. Self-Critique 4 checklist (Section 9.4)
  2. Auditor 8-layer (Section 12.1)
  3. CoVe verify ตัวเลข (Section 12.2)
  4. Human Gate (Diff View) ถ้า high-stakes

หลังจบ:
  1. บันทึก skill ถ้าจะใช้ซ้ำ
  2. บันทึก anti-pattern ถ้าล้มเหลว
  3. Update tool_registry หาก tool ใหม่
  4. ทุกคืน Night Cycle replay
```

## 24.6 Mapping: ปัญหาบ่อย → Section ที่อ่าน

| ถ้าจะ... | อ่าน Section |
|---|---|
| Setup ครั้งแรก | 22.2 (Phase 0) |
| เพิ่มเอกสารใหม่ | 6.2 (OpenKB) + 22.3 |
| สร้าง tool ใหม่ | 13 + 17.3 (decide source) |
| AI ตอบผิดบ่อย | 12 (Auditor) + 15 (Night Cycle) |
| VRAM แตก | 4 (Models) + 22.9 R1 |
| Data leak risk | 21 + 18.5 (sanitizer) |
| ย้ายโปรเจค | 19 (Portable) |
| Backup กังวล | 20 (GitHub) |
| ทำ progress report | 16.2 + 16.4 |
| ต้องการ cloud help | 18 (Copilot) |
| Pattern detect | 14.5 |

## 24.7 Anti-Patterns ที่ห้ามทำ (สรุป)

```yaml
forbidden:
  - ✗ AI คำนวณตัวเลขเอง (ใช้ SymPy เสมอ)
  - ✗ เริ่มงานโดยไม่ clarify
  - ✗ ค้น web ก่อนถาม user
  - ✗ Approve safety-critical โดยไม่มี Human Gate
  - ✗ ส่ง CONFIDENTIAL ออก external
  - ✗ เขียน Python ก่อนเช็ค OSS
  - ✗ swap VRAM ทำให้เกิน 7 GB
  - ✗ ใช้ Perplexity (แพง+ช้า) — ใช้ SearXNG แทน
  - ✗ commit secrets ลง Git
  - ✗ ข้าม night cycle (ระบบจะไม่โต)
```

## 24.8 Glossary (ศัพท์เฉพาะของแผนนี้)

```yaml
TPM:               Total Productive Maintenance
Orchestrator:      Qwen3-8B ที่ lock VRAM — รับ task หลัก
Scavenger:         Qwen3-1.7B ที่ lock VRAM — RAG/SQL/cleanup
Worker Subgraph:   ทีมย่อยใน LangGraph (Report/Excel/PPTX/Vision/Calc)
CoVe:              Chain of Verification — verify ตัวเลข
Hell Loop:         retry สูงสุด 3 → ถ้ายัง fail → escalate
Hybrid Debate:     ใช้ model เดียวกัน 2 รอบ (Proposer/Devil's Advocate)
Inquiry-First:     ถาม user ก่อนค้น web
Egress:            ข้อมูลออกนอกเครื่อง — ต้องผ่าน Guard
Hash Chain:        SHA256 chain ใน audit log → tamper-evident
Night Cycle:       23:00-05:00 self-correction routine
Morning Brief:     สรุปคืนที่แล้ว → user เช็คเช้า
Hand-off Packet:   payload ระหว่าง LangGraph nodes (Pydantic)
Lineage:           metadata ของทุก output (model, prompt hash, sources)
```

## 24.9 Final Reminder

> ระบบนี้ "ค่อยๆ โต" — ห้ามเร่ง Phase, ห้ามข้าม acceptance criteria
>
> เป้าหมายไม่ใช่ "ทำเสร็จเร็ว" แต่ "ทำแล้วใช้ได้จริง + ย้ายโปรเจคต่อไปได้"
>
> ทุกคืน Night Cycle ทำให้ระบบดีขึ้นโดยไม่ต้องสั่ง — แค่เปิดเครื่องไว้

---

**END OF MASTER PLAN v5.0**

> **Last updated:** 1 พฤษภาคม 2026
> **Total sections:** 24
> **Total length:** ~5,000+ บรรทัด
> **License:** MIT (ผู้ใช้ฟรี + commercial OK)
> **Maintainer:** TPM Intern + AI co-pilot


