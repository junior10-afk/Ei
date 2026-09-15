# Office Skill 03 — PDF read / merge / split

Source: NousResearch/hermes-agent skills/productivity/pdf (SKILL.md skimmed, not copied)
License: MIT (Nous Research)
Trigger: user mentions "PDF" — read/extract text, merge, split, rotate, or
  form-field listing. (Creation/forms/OCR/encryption deliberately out of scope.)

Ei mapping: NEW tool needed — Ei's `read_local_document` (documents.py) is
text-only and cannot parse PDF bytes. `execute_python_code` could do it ad
hoc, but a dedicated tool keeps the voice path reliable.

Procedure (English, Ei-ready):
1. For READ requests call `read_pdf_document` (proposal below), mode=text
   first; fall back to mode=meta (page count, encrypted/scanned flags) to
   explain empty results honestly (scanned PDFs need OCR — say so, don't
   invent content).
2. For MERGE/SPLIT call `merge_pdfs` / `split_pdf`, then verify by calling
   `read_pdf_document` mode=meta on the output (confirm page_count).
3. Decrypt before any other op; rotation must be a multiple of 90.
4. Voice reply in French: 1–3 sentences (page count + key content or output
   path). Extracted text goes to chat/console only.

Proposed NEW tools (implement in tools/documents.py, register in
tools/registry.py; pure stdlib + pypdf/pdfplumber, offline):
Tool(name="read_pdf_document",
     description="Extract text/tables/metadata from a local PDF file.",
     parameters={"file_path": "str (PDF path)",
                 "mode": "str (text, tables or meta; default text)",
                 "max_pages": "int (page cap, default 20, optional)"},
     handler=<pypdf/pdfplumber reader>, requires_confirmation=False,
     category="office")
Tool(name="merge_pdfs",
     description="Merge multiple PDFs into one file, in order.",
     parameters={"input_paths": "list (PDF paths in merge order)",
                 "output_path": "str (destination PDF path)"},
     handler=<pypdf merger>, requires_confirmation=True, category="office")
Tool(name="split_pdf",
     description="Extract a page subset from a PDF, optionally rotated.",
     parameters={"file_path": "str (source PDF path)",
                 "pages": "str (e.g. '1-3,7')",
                 "output_path": "str (destination PDF path)",
                 "rotate": "int (multiple of 90, default 0, optional)"},
     handler=<pypdf splitter>, requires_confirmation=True, category="office")

AgentProfile wiring (brain/multi_agents.py): extend CODE_SPECIALIST.tools
with ["read_pdf_document", "merge_pdfs", "split_pdf"], or create
OFFICE_SPECIALIST = AgentProfile(name="OfficeSpecialist",
  role_title="Assistant Bureautique & Documents",
  system_instruction=(...French...), tools=[...]) + "office" entry in
SPECIALISTS_MAP + a detect_specialist_for_query branch on
["pdf", "fusionne", "diaporama", "tableur", "compte-rendu"].
