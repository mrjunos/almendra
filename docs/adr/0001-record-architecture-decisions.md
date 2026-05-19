# ADR-0001: Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-05-19

## Context
almendra is a long-lived investigation that will be re-trained and re-designed as
better data and hardware arrive. Decisions made now need to stay legible later —
to the user, to contributors, and to a future self choosing whether to revisit a
choice.

## Decision
Significant, hard-to-reverse decisions are recorded as **Architecture Decision
Records** in `docs/adr/`, numbered sequentially. Each ADR is short and states:
**Status**, **Context**, **Decision**, **Consequences**. A superseded ADR is kept
and marked `Superseded by ADR-NNNN` rather than deleted.

## Consequences
- The reasoning behind a choice survives even after the choice changes.
- Contributors propose decisions as ADRs in pull requests.
- Small, easily-reversed choices do not need an ADR — this is for the load-bearing ones.
