# PR unit test agent

Pi 1.4.0 runs `openai/gpt-6-luna` through OpenRouter in ordinary GitHub Actions.
Pi supplies the coding agent and tools; `scripts/test_agent.py` handles GitHub,
rule selection and validation. There is no custom model loop or external server.

## Run it

Install the workflows on the default branch and set `OPENROUTER_API_KEY` in
repository Actions secrets. Use a dedicated key with a spending limit.
GitHub-hosted Ubuntu runners supply Docker. No Copilot subscription is needed.

1. Open a same-repository PR. `CI` runs pytest, Vitest, TypeScript, Prettier, Ruff
   and the orchestration tests, then calls the Pi reviewer.
2. The bot updates one PR comment and creates an **AI test review** check on the
   reviewed SHA. **5/5 means no missing tests** and a green check; 1–4 means
   concrete gaps and a red check.
3. A maintainer comments exactly `generate tests`. Only current `maintain` and
   `admin` repository roles may run this command; ordinary `write` is excluded.
4. Pi writes test files. Another job runs the checks without model credentials.
   A trusted publisher commits the tests **even when checks fail**, reports the
   result and explicitly dispatches CI for the new commit. The author investigates
   failures; the agent never changes production code or repairs tests to green.

Human pushes cancel previous work for that PR. Every publication checks the head
SHA again, and pushes are never forced. Unrelated/unauthorized comments cannot
cancel a maintainer's generation. A repeated command starts from the current
review; an obsolete review cannot authorize a commit against newer code.
Closing the PR also cancels its work. A current 5/5 review makes `generate tests`
a successful no-op, without calling the model or creating a commit.

## Agent, skills and rules

The custom instructions are `.agents/test-agent.md`. Reusable skills live in
`.agents/skills/*/SKILL.md`. `.agents/test-agent.toml` configures the model,
thinking level, timeout, test path allowlist and conditional rules:

- `paths`: a changed path matches one of the glob patterns;
- `added_paths`: a newly added file matches one of the patterns;
- `added_lines`: an added line matches one of the regular expressions.

Conditions in one rule are ANDed **on the same file**; alternatives inside a
condition are ORed. Matched skills are deduplicated. Examples cover frontend,
backend, new feature modules and HTTP endpoints. This detects declared patterns,
not arbitrary semantic feature categories. Add another rule/skill for a category.

Each invocation gets a fresh session, the full PR diff and current repository
files, including previous agent tests. Selected skills are explicitly available;
instructions require reading them. The report records selected rules/skills and
the summed cost reported by Pi across model calls (an estimate, not a guaranteed
OpenRouter invoice). Oversized diffs fail instead of receiving partial approval.

## Security and limitations

Pi runs in a container with no GitHub token, no repository Git metadata, no shell,
no project extensions/MCP/config/context discovery, and only the trusted agent
instructions mounted separately. Review is read-only at the tool level. Generation
has file-edit tools; the host rejects non-test changes, symlinks, deletions and
escaping paths before publishing. The original checkout is not writable by Pi.
The OpenRouter credential exists inside Pi; this is not a key-hiding proxy.

Verification runs separately with read-only GitHub permissions and no OpenRouter
secret. Publishing has a separate write token and does not execute generated code.
Only same-repository PRs are supported. Forks still receive ordinary CI.

AI assessment is advisory and can be wrong. Passing tests do not prove good tests;
failing tests do not prove an application bug. We keep failures visible. Model,
timeout and path limits bound work; API/agent errors fail with logs, without retry
or fallback models. CI and artifacts remain the verification evidence.

Production extensions: a credential-hiding inference proxy, network restrictions,
fully locked transitive runtime dependencies, evaluation of test usefulness and
broader fork support. Keep any such work proportional to actual usage.

## Validation

Local checks: `python -m unittest discover -s scripts/tests`, backend pytest,
frontend tests/typecheck/format, Ruff, and actionlint. Pi-to-OpenRouter connectivity
was checked with the exact pinned container and model.

- [Backend demo PR #1](https://github.com/michalwilk123/taskly-app/pull/1): a new
  statistics endpoint with one parameterized test covering empty, mixed and
  completed lists. The reviewer returned 5/5; `generate tests` finished green
  without another model call or commit. Review cost reported by Pi: $0.00152.
- [Frontend demo PR #2](https://github.com/michalwilk123/taskly-app/pull/2): an
  overdue filter with no new tests. The reviewer returned 3/5 and identified
  completed-task and date-boundary cases. Review cost reported by Pi: $0.00175.
  [Generation and verification](https://github.com/michalwilk123/taskly-app/actions/runs/39845774068)
  added [bot commit d2322ee](https://github.com/michalwilk123/taskly-app/commit/d2322ee3080102f1e607c7133a1cbd60946a404a)
  changing only two test files: one new selector test and an extension of the
  existing filter component test. Vitest reported 18 passing tests and one
  assertion failure: completed tasks incorrectly appear in the overdue filter.
  The failed test was committed, with no production-code edits. Generation cost
  reported by Pi: $0.00326. [Explicitly dispatched CI](https://github.com/michalwilk123/taskly-app/actions/runs/39846273550)
  ran against that bot commit and reproduced the failure.
- [Cancellation run](https://github.com/michalwilk123/taskly-app/actions/runs/39845313671):
  a human push during generation canceled the obsolete command run; CI started
  for the new commit.

The seven orchestration tests use case matrices for conditional rules, scores,
test-only paths, Pi errors/costs, maintainer roles, stale/closed/fork PRs and actual
Git diffs containing renames, deletions and no changes.
