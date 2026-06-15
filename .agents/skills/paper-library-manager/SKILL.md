---
name: paper-library-manager
description: Manage an OKF paper library under `paper-library/` in the current repository. Use when Codex is asked to add arXiv or research-paper URLs, update paper notes, maintain paper/topic indexes, automatically create or update topic summary pages for important new themes, normalize paper metadata, track reading status, compare papers, generate optional visualizations, or validate the paper library. Prefer repo-local use from `.agents/skills` when the paper library belongs to one repository.
---

# Paper Library Manager

## Overview

Maintain an OKF paper library as Markdown files with YAML frontmatter. Keep paper content in `paper-library/`; keep this skill limited to workflow rules, schema guidance, and validation expectations.

## Scope

Use `paper-library/` as the default library root unless the user names a different path. Treat every non-reserved `.md` file in that tree as an OKF concept.

When used for a repository-specific library, prefer installing or copying this skill under that repository's `.agents/skills/` directory. Do not write to `~/.codex/skills`, `$CODEX_HOME/skills`, or other global skill locations unless the user explicitly asks for global installation.

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

Use `references/SPEC.md` as the base OKF format reference and `references/schema.md` as the stricter paper-library profile. Default body sections for papers:

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

* Check that every paper has `type: Paper`, `title`, `description`, `resource`, `arxiv_id`, `pdf_url`, `doi`, `authors`, `submitted`, `tags`, `status`, `priority`, and `timestamp`.
* Check that internal Markdown links resolve within `paper-library/`.
* Check that index entries point to existing files.
* Run the bundled paper-library validator after content edits:

```bash
python .agents/skills/paper-library-manager/scripts/validate_paper_library.py paper-library
```

If your environment provides a Codex skill validator, run it against this skill folder after editing the skill itself.

## Visualization

Generating `paper-library/viz.html` is optional and depends on an OKF-compatible viewer. Do not assume the target repository has the OKF reference viewer unless it is present.

If the host repository contains the OKF reference viewer at `okf/src`, generate a graph view with:

```bash
python -c 'import sys; from pathlib import Path; sys.path.insert(0, "okf/src"); from enrichment_agent.viewer import generate_visualization; print(generate_visualization(Path("paper-library"), Path("paper-library/viz.html"), bundle_name="Paper Library"))'
```

If no OKF viewer is available, leave `viz.html` unchanged or skip visualization; the Markdown bundle remains the source of truth.

## Comparison Tasks

When comparing papers, write the comparison as a separate note only if the user asks for a durable artifact. Otherwise answer in chat and reference the paper files. Compare along concrete axes such as problem framing, method, evidence, assumptions, failure modes, reusable artifacts, and relevance to the user's research direction.
