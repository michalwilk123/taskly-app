---
name: new-module
description: Assess tests for newly added feature modules.
---

Find the new module's public behavior and existing nearby test conventions.
Request a small successful case and the most important failure or boundary case
only if existing tests do not exercise them. A new file is not by itself a gap:
types, exports, styles and declarative wiring may need no additional tests.
