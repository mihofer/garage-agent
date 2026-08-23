---
name: skill-merge
description: Reconcile parked skill updates in ~/.hermes/skill-updates/ — compare shipped improvements with locally learned skill edits, propose a merged version, apply it on approval.
version: 0.1.0
author: owner
license: MIT
metadata:
  hermes:
    tags: [Maintenance, Skills]
---

# Skill Update Merge

When the container ships newer versions of skills while a deployed skill was
modified locally (e.g. by the learning loop), seeding keeps the local
version and parks the shipped one in `~/.hermes/skill-updates/<name>/`.
Your job here is to reconcile those.

Trigger this when the owner asks to "merge skill updates", when boot logs
show `[seed] CONFLICT` lines, or when you notice files in skill-updates/.

## Procedure (per parked skill)

1. **Read both versions**:
   - local (active): `~/.hermes/skills/<name>/SKILL.md`
   - shipped (parked): `~/.hermes/skill-updates/<name>/SKILL.md`

2. **Classify the differences**:
   - *Shipped-side*: structural fixes, corrected paths, new rules from the
     maintainer — these are the base, adopt them.
   - *Local-side*: learned behaviors, car-specific lessons, tone tweaks the
     owner approved — re-apply these on top unless the shipped change
     supersedes them (e.g. the fix obsoletes the workaround).

3. **Propose, don't act**: present the owner a short summary —
   - what the shipped update changes,
   - which local modifications survive the merge,
   - anything genuinely conflicting (both sides changed the same rule),
     with your recommendation for each.
   Wait for approval before writing.

4. **On approval**, write the merged file and update the bookkeeping so the
   next boot recognizes it:
   ```sh
   # write merged content to ~/.hermes/skills/<name>/SKILL.md, then:
   sha256sum ~/.hermes/skills/<name>/SKILL.md | cut -d' ' -f1 \
     > ~/.hermes/.skill-hashes/<name>
   rm -rf ~/.hermes/skill-updates/<name>
   ```
   Without the hash update, the next boot would flag the merged file as a
   new conflict.

5. **Report**: list what was merged per skill and remind the owner that
   running sessions pick up skill changes only after `/new`.

## Rules

- Never delete a parked update without either merging it or getting an
  explicit "discard it" from the owner.
- If both sides are identical in meaning (whitespace/rewording), just take
  the shipped version — no ceremony.
- If the merged skill should benefit everyone using this image, remind the
  owner that the learned tweak can be contributed back to the git repo.
