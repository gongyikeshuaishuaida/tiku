---
name: text-extract
description: Process Chinese information technology exam PDFs into an Obsidian question bank. Use when the user provides exam PDF originals, answer PDFs, or asks to extract, organize, validate, update, or import practice statistics for IT exam questions in an Obsidian vault with files such as 题库管理规则.md, 题库_模板.md, 题库管理.base, PDF试卷提取方案.md, 试卷/, and attachments/.
---

# Text Extract

## Overview

Extract only the information technology part of a Chinese exam PDF into the user's Obsidian question bank, following the vault's local management rules exactly. Preserve original question wording, create stable question notes, and write answers and explanations during extraction.

PDF extraction uses **MinerU** (`mineru-open-api` CLI) as the first-pass extractor for both text-based and scanned PDFs. MinerU handles OCR, table recognition, formula recognition, and image extraction, but it does not replace vault-local review: question text must still be checked against the original PDF, and every extracted image must be manually verified or re-cropped when MinerU omits, misplaces, or over-crops a figure. Supports PDF, images, Word, Excel, PPT → Markdown, HTML, LaTeX, DOCX.

## Setup: MinerU

### Install

```powershell
npm install -g mineru-open-api
```

### Verify

```powershell
mineru-open-api version
```

### High-precision mode (preferred, login required)

Use high-precision mode for formal question-bank imports. It has higher accuracy and supports output formats md, docx, html, latex:

```powershell
mineru-open-api auth                # one-time login
mineru-open-api extract 文件.pdf -o ./out -f md,docx
```

### Flash mode (quick trial only)

Flash mode requires no token or authentication, but it does not extract images and should not be used as the final basis for papers with figures, tables, charts, screenshots, or diagrams.

```powershell
mineru-open-api flash-extract 文件.pdf
mineru-open-api flash-extract 文件.pdf -o ./输出目录
```

## Required Context

Before processing, read the vault-local rules instead of relying on memory:

- `题库管理规则.md`
- `题库_模板.md`
- `题库管理.base`
- `PDF试卷提取方案.md`
- Existing extracted notes for the same paper, if any

When reading these files on Windows, use UTF-8 from the first read. Do not first try PowerShell's default encoding and then correct garbled Chinese output.

Use the current rule files as authoritative when they differ from this skill.

## Windows UTF-8 Command Policy

When running PowerShell commands that involve Chinese paths, Chinese filenames, Markdown/PDF text, `rg` output, or `Get-Content` output, set console output to UTF-8 before the command:

```powershell
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
```

For file reads, use UTF-8 explicitly and preserve literal paths:

```powershell
Get-Content -Encoding UTF8 -LiteralPath "题库管理规则.md"
```

Use the same UTF-8 setup for searches and diagnostics, for example:

```powershell
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; rg -n "图片核验|正确答案" -g "*.md"
```

Continue using `py -X utf8` for all Python helper scripts and validation commands.

When a command needs to pass Chinese paths, avoid inline Python code piped through PowerShell here-strings. Prefer:
- PowerShell `Resolve-Path -LiteralPath`, then pass as argument to a `.py` script.
- UTF-8 `.py` file called with `py -X utf8 script.py -- "<path>"`.
- Discovery from ASCII parent directories using `Path.glob()`.
- `-LiteralPath` in PowerShell rather than bare path strings.

Preferred pattern:

```powershell
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$p = Resolve-Path -LiteralPath "D:\agent\cc\sort\2512-诸暨统测-高三-月考.pdf"
py -X utf8 scripts\mineru_extract.py -- "$($p.Path)"
```

## Helper Scripts

This skill includes reusable scripts under `scripts/`. Use `py -X utf8` on Windows.

### MinerU Extract (primary)

Run PDF extraction through the MinerU CLI. Automatically handles both text-based and scanned PDFs:

```powershell
# 优先使用高精度模式（正式入库；提取图片，需先 auth）
py -X utf8 scripts/mineru_extract.py "试卷/YYYYMM-组织-年级-类型.pdf"

# Flash 模式仅用于快速试跑或无图粗提，不作为含图试卷的最终导入依据
py -X utf8 scripts/mineru_extract.py "试卷/YYYYMM-组织-年级-类型.pdf" --flash

# 需要 OCR 表格为文字时，加 --table 启用表格识别
py -X utf8 scripts/mineru_extract.py "试卷/YYYYMM-组织-年级-类型.pdf" --table
```

Output goes to `_mineru_output/<pdf_name>/`. MinerU produces clean Markdown with:
- Properly ordered text (handles multi-column layouts)
- **Tables extracted as images by default** (`--table=false`). Do not OCR tables to HTML/Markdown — crop and embed table images instead. Use `--table` only when a clean text-format table is explicitly needed.
- LaTeX formulas for math expressions
- Extracted images under `images/` with references like `![](images/page_N_img_M.png)`
- Optional `content_list.json` with structured content metadata

### Validate Generated Notes

```powershell
py -X utf8 scripts/validate_question_bank.py --prefix "YYYYMM-组织-年级-类型"
```

Checks filename/id consistency, required frontmatter fields, stale fields, non-empty answer/analysis sections, image status consistency, and missing attachment references.

## Workflow

1. Identify the paper metadata.
   - Use `YYYYMM-组织-年级-类型` as the paper prefix, for example `202604-湖衢丽-高三-期中`.
   - If the source filename uses short dates such as `2605`, normalize it to `202605` inside the vault.
   - Valid paper grades include `高一`, `高二`, and `高三`.
   - Valid paper types are `期中`, `期末`, `月考`, `学考`, `期初`, `一模`, `二模`, and `三模`.
   - Store PDF originals under `试卷/` as `YYYYMM-组织-年级-类型.pdf` (without `-试卷` suffix).
   - If an answer file is provided, store it as `YYYYMM-组织-年级-类型-答案.pdf`; convert PNG, DOCX, or other non-PDF answer files to PDF before copying them into the vault.

2. Extract text and images with MinerU.
   - Run `scripts/mineru_extract.py` with the paper PDF. MinerU handles text-based and scanned PDFs as the first-pass extractor, then verify the generated Markdown and images against the original PDF.
   - Read the generated Markdown. Verify against the original PDF for any OCR errors or layout issues, especially on degraded scans.
   - Extract only the information technology section. Do not extract general technology questions.
   - Keep question text, code, options, numbering, and materials faithful to the original.
   - Never paste raw MinerU output directly into a final question note. Re-layout against the original PDF: separate stem, options, subquestions, code blocks, tables, and image references.
   - Format choice question stems: remove trailing punctuation, then append `（   ）`.
   - Split choice options onto individual lines as `- A. ...`, `- B. ...`, `- C. ...`, `- D. ...`. Do not write bare `A.` without the list prefix.
   - Convert code to fenced `python` blocks. Use inline code for expressions such as `a[i]`, `df["列名"]`, `==`, `[]`, and `()`.
   - For non-choice questions, lay out subquestions per the original paper structure (e.g. `(1)`, `(2)`, `①`, `②`).
   - If MinerU output is too garbled for reliable reconstruction (rare), keep the note as draft/review-needed.

3. Split notes by question id.
   - Every question note filename must equal the frontmatter `id`: `YYYYMM-组织-年级-类型-题号.md`.
   - Use two-digit question numbers such as `01`, `09`, `15`.
   - Put each note into the folder matching its primary knowledge point, following the classification rules in `题库管理规则.md`.
   - Keep cross-topic knowledge points in the `知识点` list.

4. Handle material question groups.
   - If one material block supports multiple questions, include the complete material and the complete related question group in each generated note.
   - Duplicate the note once per related question.
   - Change only `id`, filename, title question number, primary classification, and the answer/explanation focus for each duplicate.

5. Use the current template fields.
   - `题型` is only `选择题` or `填空题`.
   - Do not include `分值`.
   - `来源` must link to the PDF original in `试卷/`.
   - New notes must include `年级`, matching the paper prefix, for example `高三`.
   - New questions start with `完成次数: 0`, blank `正确率:`, `状态: 未练习`, blank `错题原因:`.
   - Do not add `正确次数`, `下次复习`, or `上次练习`.
   - Include tags according to the vault-local rules.

6. Handle images.
   - MinerU extracts images to `_mineru_output/<pdf_name>/images/`.
   - Copy relevant images to `attachments/` with naming convention `YYYYMM组织简称_题号_图序.png` (e.g. `202506宁波_14_图1.png`).
   - Use Obsidian embeds: `![[attachments/图片名.png]]`.
   - Place the image immediately after the stem/subquestion that references it.
   - Do not replace required diagrams, tables, charts, tree/stack/queue/link-list structures, UI screenshots, or unreadable code screenshots with text only.
   - Never save a full-page screenshot as a question image. Do not add captions below images.
   - **Image verification**: After embedding, open each image and compare with the original PDF. Check for completeness (no clipped borders, headers, axes, legends, captions) and no unrelated content.
   - Set `图片核验: 待核验` after embedding; change to `已通过` only after manually checking each image.
   - Use `图片核验: 无图片` for notes without images.
   - If MinerU omits or miscrops a figure, open the rendered output and manually fix the image reference or re-crop.
   - After finishing each batch, update `图片核验.md` (clear previous batch, list current batch's images with note links, crop info, verification status) and `题目核验.md` (clear previous, group current batch's notes by paper with question number, type, knowledge point, note link).

7. Write answers and explanations.
   - Every note must contain `## 答案` and `## 解析`.
   - Fill answers and explanations during extraction; do not leave `待补充`.
   - Use the answer PDF when provided. Extract it with MinerU the same way.
   - If no answer is provided, solve from the question content and make the reasoning explicit.
   - Selection answer format: `**正确答案：** A`. Multi-select: `**正确答案：** A、C`.
   - Multi-answer fill-in content may use `① ...；② ...`.
   - Explain the decisive concept, elimination reason, calculation, or code trace.

8. Update management surfaces when fields change.
   - Keep `题库管理规则.md`, `题库_模板.md`, `题库管理.base`, and `Dataview查询示例.md` aligned.
   - If importing practice statistics, write `完成次数`, `正确率`, and `状态` directly into frontmatter.
   - For completed choice-question imports, set `完成次数: 1`, `状态: 已完成`, and `正确率` from the provided table.

## Validation Checklist

Run targeted checks before finishing:

- Confirm no stale fields remain: `正确次数`, `下次复习`, `上次练习`.
- Confirm all extracted filenames match their `id`.
- Confirm every new note has `题型`, `来源`, `试卷`, `年级`, `题号`, `知识点`, `完成次数`, `正确率`, `状态`, `图片核验`, and `tags`.
- Confirm each note has non-empty `## 答案` and `## 解析`.
- Confirm no final note contains raw MinerU dumps, merged neighboring questions, unreformatted option runs, or placeholder text.
- Confirm code is in fenced code blocks and options/subquestions are split onto readable lines.
- Confirm image notes embed only local question images and have correct `图片核验`.
- Confirm all `![[attachments/...]]` embeds point to files that actually exist on disk.
- Confirm no Markdown tables (`| --- |`) remain in notes — tables must be images per `--table=false` policy.
- Confirm no duplicate frontmatter keys in any note.
- Confirm `题目核验.md` lists only the current batch's notes, grouped by paper.
- Confirm `题库管理.base` references only existing frontmatter fields or defined formulas.

Useful PowerShell checks:

```powershell
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
rg -n "正确次数|下次复习|上次练习" -g "*.md" -g "*.base"
rg -n "图片核验: 待核验|!\\[\\[attachments/" -g "*.md"
py -X utf8 scripts/validate_question_bank.py --prefix "YYYYMM-组织-年级-类型"
```

## Response Pattern

When done, report:

- Number of question notes created or updated.
- PDF originals copied into `试卷/`.
- MinerU extraction summary (pages, content items, images extracted).
- Images embedded and their verification status.
- Any rule, template, Base, or Dataview files changed.
- Any validation that could not be completed.
