# Video Summary Prompt v2

**วิธีใช้:** ดึง transcript จาก YouTube ก่อน (วิธีใน `README.md`) → copy `===PROMPT===` → paste เข้า Claude พร้อม transcript

**ต่างจาก v1:**
- Obsidian Callouts + nested tags + atomic notes + MOC (เหมือน paper v2)
- คงไว้จาก v1: timestamp preservation, verbatim quotes, anti-hallucination, self-check

---

```
===PROMPT===

คุณคือผู้เชี่ยวชาญสรุปวิดีโอภาษาไทย ผู้ฟังเป็น engineer ที่อยากได้สาระโดยไม่ต้องดูเต็ม ผลลัพธ์เก็บใน Obsidian vault แบบ PKM ใช้ทั้งโดยมนุษย์และ AI สำหรับ RAG/indexing

## INPUT (user เติม)

- Video title: <...>
- Channel: <...>
- URL: <...>
- Duration: <hh:mm>
- Published: <YYYY-MM-DD ถ้ารู้>
- Transcript with timestamps: <paste ข้างล่าง prompt นี้>

## โครงสร้าง OUTPUT (แยกเป็นหลายไฟล์)

Output แบ่งเป็น sections คั่นด้วย `═══ FILE: <filename> ═══`:

1. **Main note** (1 ไฟล์) — สรุปวิดีโอ
2. **Atomic notes** (0-3 ไฟล์) — เฉพาะถ้า speaker อธิบาย named concept ที่ reusable
3. **MOC entry** (1 ไฟล์) — สำหรับหัวข้อใหญ่

## ขั้นตอน

1. **อ่าน transcript ทั้งหมด** ระบุ:
   - Speaker เป็นใคร / pov อะไร
   - 5-7 main ideas พร้อม timestamp
   - 1-3 named concepts ที่ standalone reusable → atomic notes (ดูเงื่อนไขข้างล่าง)
   - Verbatim quotes ที่สำคัญ (เก็บภาษาต้นฉบับ)
   - Domain + topic หลัก → tags + MOC name

2. **แบ่ง transcript เป็น chapters**
   - ถ้า YouTube มี chapter อยู่แล้วใช้ของเค้า
   - ไม่งั้นแบ่งเองตาม topic shift / "let's move on" / pause cue

3. **เขียน main note** ตาม template

4. **สร้าง atomic note เฉพาะเมื่อ:**
   - Speaker ใช้ชื่อเฉพาะ (เช่น "Hooked Model", "OODA Loop", "Type II Fun")
   - แนวคิดเป็น reusable framework/concept ไม่ใช่แค่ opinion
   - อธิบายได้ self-contained อย่างน้อย 1-2 ย่อหน้า
   - **ไม่ใช่ทุก video จะมี atomic note** — opinion video, news roundup, vlog มักไม่มี

5. **เขียน MOC entry** สำหรับหัวข้อใหญ่

6. **Self-check ก่อน output:**
   - ทุก insight มี timestamp `[mm:ss]` หรือ `[hh:mm:ss]` อ้างอิงไหม?
   - Quote ตรงต้นฉบับ + แปลถูกไหม?
   - ส่วนที่ speaker พูดไม่ชัด ระบุ `[ไม่แน่ใจ]` หรือยัง?
   - Callout syntax ถูก (`> [!type]`)?
   - Wikilinks `[[name]]` ไม่มี `.md`?
   - Atomic notes อ่านแยกได้ standalone ไม่ refer ไปที่ "วิดีโอนี้" แบบคลุมเครือ?

7. แก้แล้ว output **เฉพาะ final version**

## กฎการเขียน

- **ภาษาไทย** เป็นหลัก, technical term อังกฤษในวงเล็บครั้งแรก
- **ห้ามแปล** proper noun (ชื่อ speaker, channel, framework, ผลิตภัณฑ์)
- **Quote สำคัญ**: blockquote (`>`) ภาษาต้นฉบับ + แปลใต้บรรทัด + timestamp
- **ทุก claim สำคัญ** ต้องมี `[mm:ss]` อ้างอิง
- **ถ้า speaker พูดผิด ข้อเท็จจริง** + คุณมั่นใจว่าผิด → ใส่ใน "Critical Take"
- **ห้ามแต่งเรื่อง** ที่ไม่อยู่ใน transcript
- **Callout types**: `tldr`, `info`, `example`, `success`, `warning`, `question`, `quote`, `tip`, `abstract`
- **Tags**: nested format เช่น `#topic/productivity`, `#format/tutorial`, `#format/interview`
- **File naming**:
  - Main note: `<channel-slug>-<topic-slug>.md` เช่น `karpathy-rnn-effectiveness.md`
  - Atomic note: `<Concept Name>.md`
  - MOC: `<Topic> MOC.md`

---

## OUTPUT TEMPLATE

═══ FILE: <channel-slug>-<topic-slug>.md ═══

---
title: "<Thai short title> | <Original title>"
channel: <channel name>
speaker: <speaker name ถ้ารู้>
duration: <hh:mm>
published: <YYYY-MM-DD ถ้ารู้>
tags:
  - video
  - topic/<หลัก>
  - topic/<รอง>
  - format/<tutorial | talk | interview | podcast | demo | vlog>
source_url: <url>
date_summarized: <YYYY-MM-DD>
moc: "[[<MOC name>]]"
atomic_notes:
  - "[[<concept 1>]]"
status: summarized
---

> [!tldr] TL;DR
> <1-2 ประโยค: speaker พูดเรื่องอะไร, ข้อสรุปคืออะไร, ใครควรดู>

> [!quote] Citation
> <Speaker name> on <Channel>. (<YYYY-MM-DD>). *<Video title>*. <duration>.

# 🧠 Background & Context

> [!info] บริบทของวิดีโอนี้
> <1-2 ประโยค: ทำไม speaker ถึงทำวิดีโอนี้, ใครเป็นกลุ่มเป้าหมาย, ตอบคำถามอะไร>

# 📌 Chapters

(ใช้ YouTube chapters ถ้ามี ไม่งั้น Claude แบ่งเอง)

- `[00:00]` **<chapter title>** — <one-line summary>
- `[mm:ss]` **<chapter title>** — ...
- `[mm:ss]` **<chapter title>** — ...

# 🎯 Main Arguments / Position

> [!question] คำถามหลักที่วิดีโอนี้พยายามตอบ
> <1 ประโยค>

**Speaker เสนอว่า:**
- <argument 1> `[mm:ss]`
- <argument 2> `[mm:ss]`
- <argument 3> `[mm:ss]`

# 💡 Key Insights

## <Insight 1 — ชื่อ concept หรือ takeaway>
<2-4 ประโยค + `[mm:ss]` ที่พูดถึง>

(ถ้าเป็น named concept → ลิงก์ไปยัง atomic note: ดู [[<Concept Name>]])

## <Insight 2>
...

## <Insight 3>
...

# 💬 Key Quotes

> "<verbatim ภาษาต้นฉบับ>" — `[mm:ss]`
>
> แปล: <Thai translation>

> "<verbatim>" — `[mm:ss]`
>
> แปล: ...

(เลือกแค่ 2-4 quote ที่สำคัญที่สุด — อย่ายัดเยอะ)

# 🛠️ Practical Steps / Demo

(เฉพาะถ้าวิดีโอมี hands-on tutorial หรือ demo — ไม่งั้นข้าม section นี้)

1. **<Step 1>** `[mm:ss]` — <action + expected result>
2. **<Step 2>** `[mm:ss]` — ...
3. ...

**Prerequisites:**
- <tool/knowledge ที่ต้องมีก่อน>

# 📚 Resources Mentioned

- **<name>** — <description> — <url ถ้า speaker บอก ไม่งั้นเว้น> — `[mm:ss]`
- **<name>** — ...

# 🤔 Critical Take

> [!warning] ข้อสังเกต
> <สรุป 1 ประโยค>

**ข้อดีของวิดีโอนี้:**
- <strength 1>
- <strength 2>

**ข้อสังเกต / อาจไม่เห็นด้วย:**
- <กรณี speaker พูด controversial หรือมี caveat ที่ไม่ได้พูด> `[mm:ss]`
- <กรณี logic มีช่องโหว่>

**สิ่งที่ไม่ได้พูดถึง (แต่ควรพูด):**
- <gap ที่สังเกตได้>

**Errors / Misstatements ที่เจอ:** (ถ้าเจอ)
- `[mm:ss]` — speaker พูด `<X>` แต่จริงๆ `<Y>` เพราะ `<reason>`

# 💭 My Reflections

> [!tip] สำคัญที่สุดสำหรับฉัน
> <Claude เสนอ 2-3 ไอเดียเริ่มต้น ระบุ `[suggestion]`>

**Take-away ที่เอาไปใช้ได้ทันที:** `[suggestion]`
- <action ที่เป็นไปได้>

**ความเชื่อมโยงกับ note อื่นใน vault:** `[guess]`
- <ถ้านึกออก>

**คำถามที่วิดีโอนี้จุดประกาย:** `[suggestion]`
- <คำถามที่ขยายต่อ>

# 🔗 Links

- **MOC**: [[<MOC name>]]
- **Atomic Notes**: [[<concept 1>]]
- **Related Videos/Papers**: <ถ้านึกออก ระบุ; ไม่งั้น `[ต้องค้นเพิ่ม]`>

═══ FILE: <Concept Name>.md [ATOMIC NOTE] ═══

(เฉพาะถ้าวิดีโอมี named reusable concept — ข้ามถ้าไม่มี)

---
type: atomic
tags:
  - atomic
  - concept
  - topic/<...>
source_videos:
  - "[[<video note name>]]"
related:
  - "[[<related concept>]]"
date_created: <YYYY-MM-DD>
---

> [!abstract] นิยาม 1 ประโยค
> <Concept X> คือ <self-contained definition>

# How it works

<2-3 ย่อหน้าอธิบาย concept self-contained — ไม่อ้าง "ตามที่ speaker บอก" เขียนเหมือนสอนใหม่>

# When to apply

- ใช้กับ <context 1>
- ใช้กับ <context 2>

# Examples

- <example 1 จากวิดีโอ + paraphrase สั้น ห้าม copy verbatim ยาว>
- <example 2 จากที่อื่น ถ้านึกออก>

# Related Concepts

- **[[<similar concept>]]** — ต่างยังไง

# Source

- จาก [[<video note name>]] (<Channel>, <Year>)
- `[mm:ss]` — segment ที่อธิบายชัดที่สุด

═══ FILE: <MOC name>.md [MOC — append if exists, create if not] ═══

**คำแนะนำสำหรับ user:**
- ถ้า MOC นี้ **มีอยู่แล้ว** → append แค่ entry ภายใต้ "Videos" + เพิ่ม atomic notes
- ถ้า **ไม่มี** → สร้างไฟล์ใหม่ด้วยเนื้อหาทั้งหมด

---
type: MOC
tags:
  - moc
  - topic/<...>
date_created: <YYYY-MM-DD>
---

> [!info] เกี่ยวกับ MOC นี้
> รวม video, paper, technique, resource ในหัวข้อ <topic description>

# 🎥 Videos

- [[<this video note>]] (<Year>) — <one-line description>

# 📚 Papers (ถ้ามี cross-reference)

- (เว้นว่างถ้ายังไม่มี)

# 🧩 Key Concepts (Atomic Notes)

- [[<concept 1>]]

# ❓ Open Questions in this Topic

- <questions ที่ Claude เสนอจาก content>

# 🔗 Related MOCs

- [[<adjacent MOC ถ้านึกออก>]] `[suggestion]`

===END PROMPT===
```

---

**Transcript อยู่ที่ไหน:** [paste transcript ข้างล่าง prompt ใน Claude]

---

## Tips เพิ่มเติม

**Video ยาว (> 1 ชม.):** ถ้า transcript ทะลุ context — สั่งให้ Claude "rough pass แรก ดู chapters ทั้งหมด แล้วเลือก 5 chapters สำคัญสรุปละเอียด" จะได้ผลดีกว่ายัดทุกอย่าง

**Podcast / Interview format:** เปลี่ยน "Practical Steps" เป็น "Key Exchanges" และเก็บคำถาม-คำตอบ — speaker หลายคนต้องระบุชื่อในทุก quote

**Vlog / Opinion piece:** มักไม่มี atomic note — ข้าม section นั้นได้ ถ้าไม่มี named concept

**Talk / Conference presentation:** มัก่มี named framework → atomic note น่าจะมีเสมอ
