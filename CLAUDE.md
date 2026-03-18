# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

A collection of distributable AI "skills" — structured prompt files that teach AI assistants domain-specific behaviour. Each skill lives in its own directory and is packaged into a `.skill` file (a ZIP archive) for distribution.

## Skill File Format

A skill is defined by a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: skill-name
description: One-line description used by the AI to decide when to trigger this skill automatically.
---

# Skill Title

Detailed instructions for the AI...
```

The `description` field is critical: it determines when the skill auto-activates. It should list concrete trigger phrases and conditions.

## Directory Structure

```
.
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md          # Skill definition (source of truth)
│       ├── <app>.html        # Companion web app (if any)
│       ├── evals/
│       │   └── evals.json    # Evaluation test cases
│       ├── references/       # Reference material (external scripts, docs)
│       └── scripts/          # Automation scripts
├── study/
│   └── <topic>/
│       ├── <topic>_英中双语对照.md  # Bilingual (EN/ZH) article translation
│       └── images/                  # Images referenced by the markdown
├── dist/                     # Built .skill files (git-ignored)
├── CLAUDE.md
└── README.md
```

## Packaging: Source → .skill File

A `.skill` file is a ZIP archive containing `<skill-name>/SKILL.md`. To package a skill:

```bash
zip -j dist/movie-search.skill movie-search/SKILL.md
```

Built `.skill` files go into `dist/` (git-ignored). Rebuild from source `SKILL.md` when needed.

## Evals Format

`evals/evals.json` schema:

```json
{
  "skill_name": "movie-search",
  "evals": [
    {
      "id": 1,
      "prompt": "user input to test",
      "expected_output": "natural-language rubric describing expected behaviour"
    }
  ]
}
```

Each eval prompt is run twice: once with the skill loaded and once without (A/B comparison). Results are recorded in `feedback.json` at the repo root using `run_id` pattern `eval-{name}-{with_skill|without_skill}`.

## feedback.json

Tracks eval review outcomes. `"lgtm"` means the run passed human review; `""` means it did not or was not reviewed. `status: "complete"` means the eval cycle for that batch is done.

## Architecture Notes

- Skills are purely prompt engineering — no code is executed by the skill itself. The AI follows the `SKILL.md` instructions at inference time.
- Companion web apps (e.g. `movie-search.html`) and reference material live inside their skill's directory.
- `dist/` contains built `.skill` archives and is git-ignored.
