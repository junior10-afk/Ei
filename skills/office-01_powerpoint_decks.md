# Office Skill 01 — PowerPoint decks (python-pptx)

Source: NousResearch/hermes-agent skills/productivity/powerpoint (SKILL.md skimmed, not copied)
License: MIT (Nous Research)
Trigger: user mentions "diaporama", "présentation", "slides", "pitch deck", or a .pptx file
  (create, read back, or edit a slide deck).

Ei mapping: NO new tool required. Use existing `execute_python_code`
(CodeSpecialist) for all .pptx work. Use `write_local_file` to stage any
JSON spec, `read_local_document` only for text files (never for .pptx bytes).

Procedure (English, Ei-ready):
1. Dependency check first — run via execute_python_code:
   `import importlib.util; print(bool(importlib.util.find_spec("pptx")))`.
   If missing, STOP and tell the user (in French) to install python-pptx;
   NEVER pip install silently.
2. CREATE: build the deck in one python snippet — Title / Title+Content /
   Two-Content layouts, bullets with levels, tables, speaker notes. Set 16:9
   explicitly (`prs.slide_width = Inches(13.33)`). Save outside system dirs.
3. READ: reopen with python-pptx and return per-slide outline
   (layout, shape texts, table cells, notes). Never claim content without
   this read-back.
4. EDIT: text replace across shapes + tables + notes; duplicate/remove slides
   only by index confirmed from step 3. Re-run the outline read after edits.
5. Voice reply in French: 1–3 sentences (slide count + file path). Full
   outline goes to chat/console only.

Pitfalls (from source): legacy .ppt binary unsupported (convert via
LibreOffice first); python-pptx has no reorder API; chart-type changes
impossible; default template is 4:3 unless overridden.

Optional NEW tool (only if deck requests become frequent):
Tool(name="build_pptx_deck",
     description="Build a .pptx deck from a slide spec (titles, bullets, tables, notes).",
     parameters={"spec_json": "str (JSON list of slides: title, bullets, table, notes)",
                 "output_path": "str (destination .pptx path)",
                 "slide_size": "str (16:9 or 4:3, optional)"},
     handler=<python-pptx builder>, requires_confirmation=True, category="office")
