# Project Knowledge — News Divergence Agent

## One-line summary
An AI agent that helps humanitarian analysts cross-reference how the same event
is reported across multiple languages and source types — surfacing factual
divergence and candidate events for human verification.

## The problem
In humanitarian and conflict contexts, official data is often unavailable,
suppressed, or contested. Researchers at ACLED, ICRC, UNAMA, and outlets like
Bellingcat reconstruct what happened by triangulating local press, NGO reports,
government statements, and wire services — manually, article by article, often
across languages. This agent automates the first pass of that work.

## What it does
1. Identifies the underlying event from a user query or URL
2. Searches a multilingual indexed corpus via Elastic
3. Filters to articles about the same event
4. Extracts factual claims (casualties, participants, locations, attribution)
5. Aligns claims: shared, unique, contradictory, framing differences
6. Produces a structured comparison with every claim cited to its source

## What it explicitly does not do
- Verify truth or fact-check
- Score source reliability
- Produce ground-truth estimates
- Make any factual assertion beyond what a cited source said

## Demo case
Provisional: Kabul market explosion, September 2024.
Corpus: hand-curated, pre-indexed. Sources include Reuters, AP, AFP, ToloNews,
Pajhwok Afghan News, BBC, ICRC public reports, UNAMA where available.
Backup: a natural disaster in Southeast Asia or Latin America (TBD).

## Judging criteria (equal weight, Stage 2)
1. Technological implementation
2. Design
3. Potential impact
4. Quality of the idea

## Decisions made
- Partner track: Elastic
- Framing: humanitarian / accountability research
- v1 languages: English + Dari/Pashto/Arabic (adjustable)
- Corpus: pre-indexed, hand-curated for demo
- License: MIT

## Open questions
- Specific demo incident and exact corpus article list
- How much non-English original-language content is obtainable
- Whether to add source-type filter in UI (wire / NGO / local / government)
- Backup demo case selection
- Whether "claim coverage" count (N sources report this claim) is v1 or v2
