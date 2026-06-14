# Paper Library Schema

## Paper Frontmatter

Required fields for `paper-library/papers/<arxiv_id>.md`:

```yaml
---
type: Paper
title: Paper title
description: One sentence summary for indexes and search.
resource: https://arxiv.org/abs/<arxiv_id>
arxiv_id: "<arxiv_id>"
pdf_url: https://arxiv.org/pdf/<arxiv_id>
doi: https://doi.org/10.48550/arXiv.<arxiv_id>
authors:
- Author One
submitted: YYYY-MM-DD
subjects:
- cs.AI
tags:
- short-topic-tag
status: unread
priority: normal
timestamp: YYYY-MM-DDTHH:MM:SSZ
---
```

Optional fields:

```yaml
project_url: https://example.com
code_url: https://github.com/org/repo
venue: Conference or journal name
reading_round: 1
```

## Paper Body

Default sections:

```markdown
# Summary

# Key Ideas

# Method

# Experiments

# Limitations

# Notes

# Related

# Citations
```

Omit `# Method`, `# Experiments`, or `# Limitations` if there is no reliable information yet. Preserve `# Notes` exactly when updating a paper unless the user asks to revise it.

## Topic Frontmatter

Topic files live in `paper-library/topics/<slug>.md`:

```yaml
---
type: Topic
title: Topic Name
description: One sentence describing the topic.
tags:
- topic-tag
timestamp: YYYY-MM-DDTHH:MM:SSZ
---
```

Default topic body:

```markdown
# Scope

# Papers

# Synthesis

# Open Questions
```

Use topic files to connect papers and track open questions. Do not duplicate full paper summaries in topic files. Omit `# Synthesis` until the topic has enough related papers to support a useful cross-paper observation.

Create topic files proactively for important new themes when adding papers. Keep topic slugs lowercase and hyphenated, for example `agent-self-evolution.md` or `long-context-reasoning.md`.
