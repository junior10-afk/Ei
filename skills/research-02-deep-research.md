# Ei Adapted Skill — Deep Research with Cited Report (method)

- **Source skill:** `deep-research` — affaan-m/ECC
  (`https://github.com/affaan-m/ECC`, skill `deep-research`)
  via https://skillsmp.com/creators/affaan-m/ecc/agents-skills-deep-research
- **License:** NOT declared on the SkillsMP page (no license row; treat as
  all-rights-reserved reference — method re-expressed below, no code copied).
- **Original trigger:** "Use when the user wants thorough research on any topic with
  evidence and citations." (Multi-source: firecrawl + exa MCPs in the original.)
- **Why picked:** Strong report structure + sub-question decomposition workflow.
  Original needs firecrawl/exa API keys; this adaptation replaces them 1:1 with Ei's
  existing `web_search` / `fetch_webpage` (Tavily backend used automatically when
  `TAVILY_API_KEY` is set — no new account required for baseline use).

## Ei tool mapping (existing tools only)

| Original step | Ei equivalent |
|---|---|
| `firecrawl_search` / `web_search_exa` per sub-question | `web_search(query, max_results=8)` per sub-question |
| `firecrawl_scrape` / `crawling_exa` (3–5 key sources) | `fetch_webpage(url, max_chars=8000)` on 3–5 best hits |
| Parallel Task subagents | Sequential sub-question loop (Ei is single-agent ReAct) |
| Cited markdown report | Same structure, chat/console only; voice gets 1–3 sentence summary |

## Adapted workflow for Ei (WebResearcher)

1. **Scope (1–2 questions max, or skip if user said "just research it"):** topic,
   depth (quick vs approfondie), date window, language (FR default + EN sources OK).
2. **Decompose** into 3–5 sub-questions (definitions, current state/data, options or
   actors, costs/risks, outlook).
3. **Search each sub-question** with `web_search` (vary phrasing; use time-boxed
   queries like "marché X 2026" for recency). Collect 8–15 candidate URLs, dedupe.
4. **Deep-read 3–5 key sources** with `fetch_webpage` (max_chars 5000–10000).
   Never rely on snippets alone for the final numbers.
5. **Synthesize** into this structure (chat/console):
   `# [Topic] — Research Report (date | N sources | confidence High/Med/Low)`
   `## Executive Summary` (3–5 sentences) → `## 1/2/3 Themes` (bullets with inline
   `[Source](url)` citations) → `## Key Takeaways` → `## Sources` (numbered, one-line
   summaries) → `## Methodology` (queries run, sources read).
6. **Voice mode:** compress to 1–3 spoken French sentences with the single most
   important verified finding.

## Quality rules (from source)

- Every factual bullet carries ≥1 inline citation; numbers carry 2 when they disagree.
- State confidence explicitly; list open questions instead of hiding gaps.
- One-off deep dives use this skill; recurring topic tracking → see `03-news-intelligence.md`.

## AgentProfile wiring (brain/multi_agents.py)

Append to `WEB_RESEARCHER.system_instruction`: "For broad questions, decompose into
3–5 sub-questions, search each independently, deep-read 3–5 sources, and deliver a
cited report (Summary → Themes → Takeaways → Sources → Methodology)." No new Tool().
