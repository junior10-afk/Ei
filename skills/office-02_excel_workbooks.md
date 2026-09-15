# Office Skill 02 — Excel workbooks (openpyxl)

Source: NousResearch/hermes-agent skills/productivity/xlsx (SKILL.md skimmed, not copied)
License: MIT (Nous Research)
Trigger: user mentions "Excel", "tableur", "classeur", "feuille de calcul",
  or a .xlsx/.csv file (create a report, read data, edit cells, CSV interop).

Ei mapping: NO new tool required. Use existing `execute_python_code`
(CodeSpecialist) for all .xlsx work. `write_local_file` stages CSV/JSON
inputs; `read_local_document` reads CSVs (never .xlsx bytes).

Procedure (English, Ei-ready):
1. Dependency check first — run via execute_python_code:
   `import importlib.util; print(bool(importlib.util.find_spec("openpyxl")))`.
   If missing, STOP and tell the user (in French) to install openpyxl;
   NEVER pip install silently.
2. CREATE: one snippet builds a styled multi-sheet workbook — header row,
   number formats (`$#,##0.00`, `0.0%`, `yyyy-mm-dd`), freeze panes,
   autofilter, formulas via `cell.value = "=SUM(B2:B9)"`. Set
   `wb.calculation.fullCalcOnLoad = True` so Excel recomputes on open
   (openpyxl NEVER evaluates formulas itself).
3. READ: `openpyxl.load_workbook(path, data_only=False)` → sheet inventory
   (names, dimensions), dump rows as JSON. Cached values exist only if a
   real spreadsheet app saved the file last; report `null` honestly.
4. EDIT: set cells / append rows by address confirmed from step 3; never
   save a `data_only=True` workbook unless discarding formulas is the goal.
5. CSV interop: pass explicit encoding/delimiter (European CSVs often use
   `;` + decimal commas). Legacy .xls → convert with LibreOffice first.
6. Voice reply in French: 1–3 sentences (sheets, row counts, file path).

Pitfalls (from source): editing a charted workbook drops charts on save;
sheet protection is NOT security (trivially strippable); sheet names max
31 chars, no `[]:*?/\`.

Optional NEW tool (only if report requests become frequent):
Tool(name="build_xlsx_report",
     description="Build a styled multi-sheet .xlsx report from row data.",
     parameters={"sheets_json": "str (JSON {sheet_name: {headers, rows}})",
                 "output_path": "str (destination .xlsx path)",
                 "with_formulas": "bool (append a totals row, optional)"},
     handler=<openpyxl builder>, requires_confirmation=True, category="office")
