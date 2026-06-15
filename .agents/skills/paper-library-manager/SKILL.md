---
name: paper-library-manager
description: Manage this repository's local OKF paper library under `paper-library/`. Use when Codex is asked to add arXiv or research-paper URLs, update paper notes, maintain paper/topic indexes, automatically create or update topic summary pages for important new themes, normalize paper metadata, track reading status, compare papers, or check the health of the repo-local paper library. This skill is local to this repository and should not write to global Codex skill directories.
---

# Paper Library Manager

## Overview

Maintain the repo-local OKF paper library as Markdown files with YAML frontmatter. Keep paper content in `paper-library/`; keep this skill limited to workflow rules, schema guidance, and validation expectations.

## Scope

Use `paper-library/` as the default library root unless the user names a different repo-local path. Treat every non-reserved `.md` file in that tree as an OKF concept.

Do not write to `~/.codex/skills`, `$CODEX_HOME/skills`, or other global skill locations for paper-library work. This skill itself lives in `.agents/skills/paper-library-manager/` so it remains repo-local.

## Workflow

When adding or updating a paper:

1. Parse the arXiv ID from the URL or user input.
2. Read the existing paper file if `paper-library/papers/<arxiv_id>.md` already exists.
3. Fetch or verify metadata from authoritative sources when network access is available. Prefer arXiv for bibliographic facts; use project pages, GitHub, Hugging Face paper pages, or Semantic Scholar only as additional sources.
4. Create or update one paper concept under `paper-library/papers/`.
5. Identify 1 to 3 important themes from the paper's title, abstract, method, benchmarks, and contributions.
6. Reuse existing topic pages when they cover those themes; otherwise create new `paper-library/topics/<slug>.md` topic summary pages without waiting for an explicit user request.
7. Add concise topic links under the paper's `# Related` section and add the paper to each affected topic's `# Papers` section.
8. Update `paper-library/papers/index.md`, `paper-library/topics/index.md`, and every affected `paper-library/topics/*.md`.
9. Preserve user notes, reading status, priority, and manually curated tags unless the user explicitly asks to change them.
10. Cite only sources that were actually used.

## Paper Documents

Use `references/schema.md` for the frontmatter and body conventions. Default body sections for papers:

* `# Summary`
* `# Key Ideas`
* `# Method` when the paper has a concrete method section worth separating
* `# Experiments` when the paper reports empirical results
* `# Limitations` when known from the paper or user's notes
* `# Notes`
* `# Related`
* `# Citations`

Keep generated summaries concise and distinguish paper claims from personal notes. If a paper has not been read in full, avoid presenting speculative critique as established fact.

## Topic Documents

Use topic concepts for stable themes such as `multi-agent-systems`, `llm-agents`, `ai-for-science`, `agent-self-evolution`, `benchmarks`, or named methods. A topic page should list related papers and open questions, not duplicate each paper's full summary.

Create or update topic pages proactively whenever a new paper introduces an important theme. Important themes usually satisfy at least two of these conditions:

* The theme appears in the title, abstract, method name, benchmark name, or central contribution.
* The theme could group multiple current or future papers.
* The theme is useful for retrieval, comparison, or literature-review synthesis.
* The theme is more specific than a broad field label such as `ai` or `machine-learning`.

Do not create a topic for every tag. Tags can be granular; topic pages should represent durable synthesis nodes. Prefer reusing an existing topic when the new theme is semantically equivalent to one already present.

Every topic page should include `# Scope`, `# Papers`, and `# Open Questions`. When a topic has two or more papers, optionally add `# Synthesis` with concise cross-paper observations.

When adding a new topic, update `paper-library/topics/index.md`. Ensure links are bidirectional: the paper links to the topic, and the topic links back to the paper.

## Indexes

Maintain index files as plain Markdown without frontmatter. Sort paper entries by arXiv ID or submitted date when the user does not specify a preference. Keep descriptions one sentence.

## Metadata Rules

Preserve these user-curated fields when updating a paper:

* `status`
* `priority`
* `tags`
* `# Notes`
* any custom frontmatter keys not defined in `references/schema.md`

Use `status: unread` for newly added papers unless the user says otherwise. Recommended status values are `unread`, `skimmed`, `read`, and `summarized`.

## Validation

Before finishing paper-library edits:

* Check that every paper has `type: Paper`, `title`, `description`, `resource`, `arxiv_id`, `authors`, `submitted`, `tags`, `status`, `priority`, and `timestamp`.
* Check that internal Markdown links resolve within `paper-library/`.
* Check that index entries point to existing files.
* Run the skill validator when editing this skill's own files:

```bash
python /Users/pengqianhan/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/paper-library-manager
```

## Comparison Tasks

When comparing papers, write the comparison as a separate note only if the user asks for a durable artifact. Otherwise answer in chat and reference the paper files. Compare along concrete axes such as problem framing, method, evidence, assumptions, failure modes, reusable artifacts, and relevance to the user's research direction.
