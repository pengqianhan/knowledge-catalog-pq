---
type: Topic
title: Agent environment engineering
description: Papers about designing the environments — resources, constraints, and interfaces — that shape agent behavior.
tags:
- environment-engineering
- agent-environments
- reward-hacking
timestamp: 2026-06-18T00:00:00Z
---

# Scope

This topic tracks papers that treat the *environment* an agent acts in — its permissions, artifacts, budgets, interfaces, and oversight hooks — as the primary design surface, rather than the agent's prompt or workflow. It includes work on amplifying productive behaviors (exploration, artifact management, collaboration) and suppressing harmful ones (reward hacking, high-friction oversight).

# Papers

* [EurekAgent](../papers/2606.13662.md) - engineers the agent environment along permissions, artifact, budget, and human-in-the-loop dimensions for autonomous scientific discovery.

# Open Questions

* Which environment constraints reliably suppress reward hacking versus merely deferring it?
* How do filesystem/Git artifact substrates compare to shared-context substrates for inter-agent collaboration?
* How should budget engineering trade off open-ended exploration against cost ceilings?
* What is the minimal human-in-the-loop interface that keeps oversight low-friction without bottlenecking the agent?
