---
name: api-contract
description: Assess the HTTP contract of added or changed endpoints.
---

Inspect request validation, status codes, response bodies and missing resources.
Prefer the existing TestClient with a mocked repository. Do not duplicate all
schema tests through HTTP. Verify invalid input does not call the repository.
