# Ei Adapted Skill — Fact-Check Pass (method)

- **Source skill:** `fact-check` — jwynia/teach
  (`https://github.com/jwynia/teach/tree/main/.claude/skills/fact-check`)
  via https://skillsmp.com/es/creators/jwynia/teach/claude-skills-fact-check
- **License:** MIT (declared on SkillsMP page)
- **Original trigger:** "Verify claims in generated output against sources. Use as a
  separate pass AFTER content generation to catch hallucinations. Critical constraint —
  cannot be reliably combined with generation in a single pass."
- **Why picked:** Pure method/checklist skill, zero new dependencies, zero API keys.
  Directly hardens Ei's WebResearcher + Orchestrator voice answers against hallucinations.

## Ei tool mapping (existing tools only)

- `web_search(query, max_results)` — verify each claim with an INDEPENDENT query
  (different wording from the query that produced the claim: PRODUCER ≠ VERIFIER).
- `fetch_webpage(url, max_chars)` — deep-read the 1–2 most authoritative hits per claim.
- Never accept training-data recall as evidence. No source = UNVERIFIED.

## Adapted workflow for Ei (WebResearcher / Orchestrator)

1. **Finish generation first.** Draft the full answer before any verification.
2. **Extract every verifiable claim:** numbers/dates/names, statistics, attributions
   ("research shows…"), definitions, historical/causal/comparative claims.
   Skip: clearly-marked opinions, labelled hypotheticals, pure deductions from premises.
3. **Categorize:** Hard (numbers, dates, names, quotes → must match source exactly)
   vs Soft (general facts → source must substantially support).
4. **Verify each claim** with a fresh `web_search` (re-phrased query path) and, for
   hard claims, one `fetch_webpage` on a primary source. Triangulate: 2 independent
   sources for high-stakes claims (health, safety, legal, money).
5. **Rate each claim:** VERIFIED / PARTIALLY SUPPORTED / CONTRADICTED / UNVERIFIABLE.
6. **Deliver:**
   - Voice (1–3 sentences): speak ONLY verified claims; append "à confirmer" style
     hedging in French for anything unverifiable; drop contradicted claims silently
     and re-plan the answer.
   - Chat/console: append a compact `Vérification:` block — N claims checked,
     per-claim source link, corrections made, caveats.

## Anti-patterns (from source, enforced)

- "I'm confident" / "to the best of my knowledge" → require a citation instead.
- Verifying while generating → forbidden; separate passes mandatory.
- Checking one claim and assuming the rest → check all or explicitly mark unchecked.

## AgentProfile wiring (brain/multi_agents.py)

Extend `WEB_RESEARCHER.system_instruction` with: "After drafting, run a separate
fact-check pass: extract each verifiable claim, re-verify via an independent
web_search/fetch_webpage path, rate VERIFIED/PARTIAL/CONTRADICTED/UNVERIFIABLE,
and only speak verified claims." No new Tool() needed.
