# 🤖 TPM AI Assistant

ผู้ช่วยวิศวกรซ่อมบำรุง — ขับเคลื่อนด้วย local LLM (Ollama Qwen3-8B) + open-source first

---

## ทำได้

- 📝 **เขียน Maintenance Report** (.docx) — สรุปประวัติเสีย + Pareto + คำแนะนำ
- 📊 **สร้าง Reliability Excel** (.xlsx) — MTBF, MTTR, Availability + chart
- 🔎 **ค้นข้อมูลเทคนิค** — SearXNG/Tavily/Exa/Wikipedia (ฟรีหมด)
- ❓ **Clarify ก่อนเริ่ม** — ถ้า prompt ไม่ชัด AI จะถาม A/B/C ก่อน
- 🔒 **Egress Guard** — ข้อมูล confidential ไม่ออก L3 search

## ลองพิมพ์อะไรดู

```
เขียน maintenance report ของ SHIBAURA-EC100SX สำหรับ 90 วันล่าสุด
```

```
report on MAKINO-a51nx last 60 days
```

```
excel reliability metrics for SODICK-AD35L
```

```
what is ASTM A106 standard
```

```
ราคา bearing SKF 6205 ล่าสุด
```

## ระวัง

- ตอนนี้ระบบใช้ **DUMMY data** สำหรับ pre-internship testing
- ทุก output จะ flag ชัดเจน "DUMMY DATA"
- วันแรกที่ฝึกงาน → `rm -rf raw_data/_dummy/` แล้ววางเอกสารจริงใน `raw_data/`

## Architecture

```
prompt
  → Clarification Loop (§ 7) — ตรวจ confidence, ถามถ้าไม่ชัด
  → Inquiry Phase (§ 8)       — ถาม user ก่อนค้น web
  → Plan
      ├─ action = lookup → L3 search (SearXNG/Tavily/Exa/...)
      └─ action = report/excel → Worker (Researcher → Writer → Reviewer)
  → Done (with .docx/.xlsx file or search results)
```

ดูรายละเอียดทั้งหมดใน `MASTER_PLAN_v5.md`
