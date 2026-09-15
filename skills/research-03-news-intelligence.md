# Ei Adapted Skill — News Intelligence / Topic Monitor (method)

- **Source skill:** `news-intelligence` — ryan823-dev/vertax
  (`https://github.com/ryan823-dev/vertax/tree/main/.agents/skills/news-intelligence`)
  via https://skillsmp.com/creators/ryan823-dev/vertax/agents-skills-news-intelligence
- **License:** NOT declared on the SkillsMP page (no license row; method re-expressed
  below, no code copied).
- **Original trigger:** "Use when the user wants to monitor news, track press coverage,
  analyze media sentiment, research news mentions, or stay updated on topics/companies/
  people." (Original calls Exa MCP: `web_search_exa`, `exa_answer`, `get_page_contents_exa`.)
- **Why picked:** Best query-pattern + digest-format checklist found (search patterns
  table, 3 research modes, tuning table, sentiment rubric, outlet tiers). Exa calls are
  replaced 1:1 with Ei tools — no new key needed.

## Ei tool mapping (existing tools only)

| Original (Exa MCP) | Ei equivalent |
|---|---|
| `web_search_exa(query, type=news, start_published_date)` | `web_search("<topic> actualités <JJ/MM/AAAA>", max_results=10)`; repeat per pattern row |
| `exa_answer` (direct answer + citations) | Snippet synthesis from `web_search` results + 1 `fetch_webpage` on top hit |
| `get_page_contents_exa(urls)` | `fetch_webpage(url, max_chars=5000)` per top story (max 3–5) |
| `include_domains` filter | Appended query terms (`site:`-style keywords + outlet names in French) |

## Query patterns (adapted to French)

| News type | Query template |
|---|---|
| Company | `"[Entreprise] actualités"` / `"[Entreprise] annonce"` |
| Industry | `"[Secteur] tendances 2026"` |
| Product launch | `"[Entreprise] lancement [produit]"` |
| Executive | `"[Nom] actualité"` |
| Crisis | `"[Entreprise] polémique OR controverse"` |
| Partnership | `"[Entreprise] partenariat"` |

## Modes → Ei behavior

1. **Quick (default voice):** 1 `web_search` (time-boxed: "cette semaine"), speak top
   2–3 headlines in 1–3 French sentences with source names.
2. **Tracking (chat):** run 2–4 pattern queries, `fetch_webpage` top stories, deliver
   the digest format below.
3. **Outlet-specific:** bias queries toward outlet tiers —
   Tech: TechCrunch, The Verge, Ars Technica · Finance: Bloomberg, Reuters, FT, Les Échos ·
   General FR: AFP, Le Monde, France Info, Reuters.

## Digest output format (chat/console)

```
ACTUS — [Topic] ([date range])
• [Date] Headline (Outlet, sentiment +/-/=)
Top stories: 1. Headline — 2-3 sentence summary. Key takeaways. Source: URL
Sentiment global: [Positif/Neutre/Négatif] — [1-line narrative]
Total: N articles | Période: [start–end]
```

## Dynamic tuning (from source, adapted)

- "breaking / dernières nouvelles" → 1 query, last 24–48h terms, top 5.
- "cette semaine" → 2 queries, top 10–15.
- "dossier complet / approfondi" → 4+ queries + deep-reads, hand off to `02-deep-research.md`.

## AgentProfile wiring (brain/multi_agents.py)

Add trigger keywords to `detect_specialist_for_query` web branch:
`["breaking", "dernières nouvelles", "presse", "couverture médiatique", "suivi actu"]`,
and note the digest format in `WEB_RESEARCHER.system_instruction`. No new Tool().
Optional future: `schedule_digest` Tool() wrapping existing `schedule_reminder` for
daily briefings — NOT proposed now (reuse `schedule_reminder` instead).
