# Step 1: Summary Toolkit v2

ชุด prompt 3 ตัวสำหรับสรุป paper / YouTube / GitHub repo ลง Obsidian แบบ PKM (Personal Knowledge Management) เต็มรูปแบบ

---

## ต่างจาก v1 ยังไง

| ด้าน | v1 | v2 |
|---|---|---|
| **โครงสร้าง output** | ไฟล์เดียวต่อ source | Main note + Atomic notes + MOC entry |
| **Visual scanning** | `# heading + emoji` | Obsidian Callouts (`> [!tldr]`, `> [!warning]`) |
| **Tags** | flat `[paper, ai]` | nested `#domain/nlp`, `#method/optimization` |
| **My Reflections** | placeholder ตอนท้าย | first-class section + ไอเดียต่อยอด |
| **Knowledge graph** | ไม่มี | Atomic notes (technique standalone) + MOC (Map of Content) |
| **AI-ready (RAG)** | ไม่ได้คิด | TL;DR ใส่ตอนต้นเสมอ + structured callouts ให้ AI parse ง่าย |
| **คงไว้จาก v1** | — | self-check, anti-hallucination, Thai rules, structured tables |

---

## 4 ขั้นตอนหลัก (เหมือนเดิม)

1. **เตรียม source** (วิธีเดียวกับ v1 — ดูข้างล่าง)
2. เปิด **claude.ai** → new chat
3. **Copy prompt v2** ที่ตรงประเภท → paste เข้า Claude → attach/paste source
4. **แยก output เป็นหลายไฟล์** ตาม delimiter `═══ FILE: ... ═══` → save ใน Obsidian

---

## วิธีแยกไฟล์จาก output

Claude จะ output แบ่งเป็น sections ที่คั่นด้วย:

```
═══ FILE: paper-name.md ═══
(เนื้อหา main note)

═══ FILE: Technique Name.md [ATOMIC NOTE] ═══
(เนื้อหา atomic note)

═══ FILE: Topic MOC.md [MOC — append if exists, create if not] ═══
(MOC entry)
```

วิธีจัดการ:
1. Copy ทั้งหมดที่ Claude ตอบ
2. แยกตาม `═══ FILE: ═══` markers — แต่ละ section = 1 ไฟล์
3. สร้าง note ใหม่ใน Obsidian ตามชื่อที่ระบุ → paste เนื้อหา
4. สำหรับ MOC: ถ้ามีอยู่แล้ว → append แค่ entry section; ถ้าไม่มี → สร้างใหม่ทั้งไฟล์

**Tip:** ใช้ plugin `Obsidian-Templater` หรือ `QuickAdd` ช่วยสร้างหลายไฟล์เร็วขึ้น (ภายหลัง — ตอนนี้ manual ก็ได้)

---

## โครงสร้าง vault ที่แนะนำ

```
📁 Vault
├── 📁 00-MOCs                    ← Map of Content (จุดศูนย์รวม)
│   ├── Prompt Evolution MOC.md
│   ├── Multi-Agent Systems MOC.md
│   └── ...
├── 📁 10-Atomic-Notes             ← Technique standalone notes
│   ├── Chain of Density.md
│   ├── Reflective Feedback.md
│   └── ...
├── 📁 20-Papers
│   └── 2024-cod-summarization.md
├── 📁 30-Videos
│   └── andrej-karpathy-rnn-effectiveness.md
├── 📁 40-Repos
│   └── langgraph.md
├── 📁 90-Inbox                    ← paste ไว้ก่อน organize ทีหลัง
└── 📁 _prompts                    ← เก็บ prompt files ใน folder นี้
    ├── paper-prompt-v2.md
    ├── video-prompt-v2.md
    └── code-prompt-v2.md
```

ใช้ prefix ตัวเลข (00, 10, 20, ...) เพื่อให้ folder เรียงตามลำดับ workflow ไม่ใช่ alphabetical

---

## เตรียม source ตามประเภท (เหมือน v1)

### 📄 Paper
- โหลด PDF จาก arxiv/journal → drag เข้า Claude
- Paper ยาวมาก → arxiv HTML version (เปลี่ยน `abs` เป็น `html` ใน URL)

### 🎥 YouTube
ดึง transcript ก่อน:
- ใน YouTube กดปุ่ม `...` ใต้ video → "Show transcript" → copy
- หรือใช้ https://youtubetotranscript.com/

### 💻 GitHub Repo
- https://gitingest.com/ — paste URL → ได้ text รวมทุกไฟล์
- ใหญ่เกิน 150k tokens → ใส่ "Include patterns" เลือก `src/,README.md,docs/`

---

## เกี่ยวกับ Atomic Notes

**Atomic note** = note สั้นๆ อธิบาย **เทคนิคเดียว** standalone อ่านแยกได้

ตัวอย่างจาก paper:
- Paper เรื่อง summarization → atomic note `Chain of Density.md`
- Paper เรื่อง agent → atomic note `Reflective Feedback.md`, `Tree of Thoughts.md`

ตัวอย่างจาก video:
- Video อธิบาย React Hooks → atomic note `useEffect Hook.md`

ตัวอย่างจาก code:
- Repo ที่ใช้ pattern เด่น → atomic note `Repository Pattern.md`, `Async Queue with Backpressure.md`

**กฎ:** Claude จะสร้าง atomic note **เฉพาะ** เมื่อ paper/video/code มี technique ที่:
1. มีชื่อชัด (named)
2. Reusable (ใช้กับ project อื่นได้)
3. คุ้มจะแยกเป็น note (อธิบายได้อย่างน้อย 1-2 ย่อหน้า)

ไม่ใช่ทุก paper จะมี atomic note — บางอันเป็น empirical study อย่างเดียวก็ไม่ต้องสร้าง

---

## เกี่ยวกับ MOC (Map of Content)

**MOC** = note กลางที่รวม link ของ paper/atomic note ในหัวข้อเดียวกัน

ตัวอย่าง:
```markdown
# Prompt Evolution MOC

> [!info] เกี่ยวกับ MOC นี้
> รวม paper, technique, resource ในหัวข้อ Prompt Evolution

# 📚 Papers
- [[2023-chain-of-density]] — entity-density iterative refinement
- [[2024-evoprompt]] — evolutionary search over prompts

# 🧩 Key Techniques
- [[Chain of Density]]
- [[Reflective Feedback]]

# ❓ Open Questions
- เมื่อไหร่ evolution beat handcrafted prompts?

# 🔗 Related MOCs
- [[LLM Evaluation MOC]]
```

**Workflow ปกติ:**
- Paper แรกของหัวข้อใหม่ → Claude เสนอชื่อ MOC + สร้าง MOC ใหม่พร้อมเนื้อหา
- Paper ที่ 2, 3, ... ของหัวข้อเดิม → Claude สร้างแค่ "entry" ที่ append เข้า MOC ที่มีอยู่

Claude **ไม่รู้** ว่า MOC ไหนมีในของคุณแล้ว — ต้องเช็คเองว่ามีอยู่หรือไม่ ถ้ามีก็ append แค่ entry ถ้าไม่มีก็สร้างใหม่จากเทมเพลตที่ให้

---

## Tips ทำให้คุณภาพดีขึ้น

- ใช้ **Sonnet 4.5** สำหรับงานปกติ / **Opus** สำหรับ paper สำคัญ
- ถ้า Claude ทำ atomic note ที่ "ไม่ใช่ technique จริง" → บอกต่อว่า "ตัดออก" หรือ "รวมเข้า main note"
- ถ้าชื่อ MOC ที่ Claude เสนอกว้างเกิน/แคบเกิน → บอก "ใช้ชื่อ `XYZ MOC` แทน" Claude จะปรับให้
- เก็บ MOC ไม่เกิน 50 entries ต่อไฟล์ — ถ้าเกินให้แตกย่อย

---

## เมื่อไหร่ควรขยับไป Step 2

เหมือน v1: ทำ 1 เดือน บันทึก pain points แล้วค่อย review ความต่างของ v2 คือ — เมื่อ vault โตขึ้น คุณจะเห็น **value ของ atomic notes + MOC** ชัดขึ้น (ใช้ search, graph view, backlinks ของ Obsidian ได้คุ้ม) ก่อนที่จะคิดสร้างระบบ automate
