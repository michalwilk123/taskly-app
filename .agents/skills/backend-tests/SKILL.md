---
name: backend-tests
description: Write focused pytest tests for Taskly backend behavior.
---

Use pytest and the existing fixtures in backend/tests/conftest.py. Reuse the
autospecced repository mock for router tests and Mock(spec=Session) for repository
tests. Use parameterization for the same contract with different inputs.

Prioritize observable results and side effects: PATCH omitted vs null vs false
vs empty string, 404 responses, DELETE 204 with empty body, and transaction
rollback/cleanup. Do not assert exact current timestamps; freeze time or bound it.
Run from backend: python -m pytest. The supported Python version is 3.12.
