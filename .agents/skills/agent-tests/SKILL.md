---
name: agent-tests
description: Test the agent's rules, model contracts and write boundaries.
---

Use Python unittest with temporary repositories or fixtures, without real API
calls. Prioritize conditional skill selection, invalid model output, path escape,
non-test writes and stale SHA protection. Test behavior using compact tables.
Run from repository root: python -m unittest discover -s scripts/tests.
