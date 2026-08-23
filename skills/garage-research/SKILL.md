---
name: garage-research
description: Rules for researching car problems on forums and the web — source quality, consensus vs. anecdote, and using the local archive index first.
version: 0.1.0
author: owner
license: MIT
metadata:
  hermes:
    requires_toolsets: [web]
---

# Forum & Web Research Rules

When diagnosing problems not fully covered by the manuals:

0. **Site registry**: check `$GARAGE_DATA_DIR/research-sources.md` if it
   exists — the owner maintains known-good forums, parts vendors, and
   classifieds there (with language notes). Prefer those sites; suggest
   adding new good ones when encountered.

1. **Local archive first**: call `search_archive` (garage-knowledge MCP)
   with symptom keywords before hitting the live web. Follow promising hits
   with `get_thread(url)`.
2. **Live web second**: prefer marque/model-specific forums and known
   communities over generic Q&A aggregators. Include the model/engine code
   in searches where relevant.
3. **Report honestly**:
   - link every thread you used
   - state whether it's one report or a recurring pattern ("3 threads,
     all resolved by X" vs "one guy's theory")
   - separate *confirmed fixes* from *hypotheses*
   - note the poster's engine/year if it differs from ours
4. **Contradictions**: if sources disagree, present both with evidence
   strength, then say which you'd try first and why.
5. **Give back**: after WE solved something ourselves, offer to draft a
   forum post (symptom → diagnosis → fix, with photos). Always show the
   draft for approval; never post anywhere without explicit confirmation.

# Classifieds sweep (daily cron context)

When running the daily watcher heartbeat:
- run saved searches from the ledger (`parts` WHERE status='needed')
- search eBay/Kleinanzeigen/specialty vendors for those terms + part numbers
- alert only on meaningful matches: correct variant, price below the part's
  `price` field (or market-typical), seller ships to us
- record hits as parts rows with status='found' + url + price, and tell the
  owner with links. Never contact sellers or buy anything.
