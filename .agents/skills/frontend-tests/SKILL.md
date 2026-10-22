---
name: frontend-tests
description: Write readable Vitest and Testing Library tests for Taskly.
---

Reuse existing test fixtures and Testing Library conventions. Test behavior, not
component internals. Mock fetch for HTTP tests and the API boundary for hooks;
use a fresh real QueryClient with retries disabled to test cache behavior.

Prefer extending a small table of cases. Cover meaningful boundaries, error
responses, request cancellation, preserving unrelated cache entries and stale
responses. Use fake timers only for clock-dependent behavior and restore them.
Run from frontend: npm test; npm run typecheck; npm run format:check.
