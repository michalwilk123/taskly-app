import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_agent as agent


class TestAgent(unittest.TestCase):
    def test_only_maintainers_can_generate_and_sufficient_review_is_a_noop(self):
        event = {
            "sender": {"login": "owner"},
            "comment": {"body": "generate tests"},
            "issue": {"number": 1},
        }
        pr = {
            "state": "open",
            "head": {
                "sha": "current",
                "ref": "feature",
                "repo": {"full_name": agent.REPO},
            },
            "base": {"sha": "base"},
        }
        review = {"head_sha": "current", "score": 5, "gaps": []}
        comments = [
            {
                "user": {"login": "github-actions[bot]"},
                "body": agent.MARKER
                + "\n<!-- review-data:"
                + json.dumps(review)
                + " -->",
            }
        ]
        with (
            patch.dict(
                agent.os.environ,
                {"GITHUB_EVENT_NAME": "issue_comment", "GITHUB_EVENT_PATH": "/event"},
            ),
            patch.object(agent.Path, "read_text", return_value=json.dumps(event)),
            patch.object(agent, "output") as emit,
        ):
            for role in ("read", "triage", "write"):
                with (
                    self.subTest(role=role),
                    patch.object(agent, "api", return_value={"role_name": role}),
                    self.assertRaisesRegex(ValueError, "maintainers"),
                ):
                    agent.prepare(Path("/unused"))
            for role in ("maintain", "admin"):
                with (
                    self.subTest(role=role),
                    patch.object(
                        agent,
                        "api",
                        side_effect=[{"role_name": role}, pr, comments, {}],
                    ) as request,
                ):
                    agent.prepare(Path("/unused"))
                    emit.assert_called_with(mode="skip", number=1, head_sha="current")
                    self.assertIn("5/5", request.call_args.args[2]["body"])
                    self.assertIn("current", request.call_args.args[2]["body"])
            review["head_sha"] = "previous"
            comments[0]["body"] = (
                agent.MARKER + "\n<!-- review-data:" + json.dumps(review) + " -->"
            )
            with (
                patch.object(
                    agent, "api", side_effect=[{"role_name": "admin"}, pr, comments]
                ),
                self.assertRaisesRegex(ValueError, "current PR commit"),
            ):
                agent.prepare(Path("/unused"))

    def test_large_pi_prompt_uses_stdin_and_container_is_cleaned_on_every_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docker = root / "docker"
            docker.write_text("""#!/usr/bin/env python3
import json, os, sys, time
with open(os.environ["TEST_DOCKER_RECORD"], "a") as log:
    record = {"args": sys.argv[1:]}
    if sys.argv[1] == "run":
        record["prompt"] = json.load(sys.stdin)
    log.write(json.dumps(record) + "\\n")
if sys.argv[1] != "run":
    sys.exit(0)
case = os.environ["TEST_PI_CASE"]
if case == "timeout":
    time.sleep(5)
if case == "exit_error":
    sys.stderr.write("runtime failed")
    sys.exit(1)
if case == "malformed":
    print("invalid JSON")
else:
    message = {"role": "assistant", "content": [{"type": "text", "text": json.dumps({"score": 5, "summary": "No gaps", "gaps": []})}]}
    if case == "model_error":
        message.update(stopReason="error", errorMessage="provider failed")
    print(json.dumps({"type": "message_end", "message": message}))
""")
            docker.chmod(0o755)
            head = agent.command("git", "rev-parse", "HEAD", cwd=agent.ROOT).strip()
            change = {
                "path": "frontend/src/example.ts",
                "status": "M",
                "patch": "+" + "ą" * 60000,
                "added_lines": "ą" * 60000,
            }
            for case, error in (
                ("success", None),
                ("timeout", subprocess.TimeoutExpired),
                ("exit_error", RuntimeError),
                ("malformed", ValueError),
                ("model_error", ValueError),
            ):
                with self.subTest(case=case):
                    work = root / case
                    work.mkdir()
                    (work / "state.json").write_text(
                        json.dumps(
                            {
                                "mode": "review",
                                "head_sha": head,
                                "pull_request": {"title": "Review", "body": ""},
                            }
                        )
                    )
                    record = work / "docker.jsonl"
                    with (
                        patch.dict(
                            os.environ,
                            {
                                "PATH": str(root) + os.pathsep + os.environ["PATH"],
                                "TEST_DOCKER_RECORD": str(record),
                                "TEST_PI_CASE": case,
                            },
                        ),
                        patch.dict(
                            agent.CONFIG,
                            {
                                "timeout_seconds": 1 if case == "timeout" else 5,
                                "rules": [
                                    {
                                        "name": "frontend",
                                        "paths": ["frontend/**"],
                                        "skills": [
                                            ".agents/skills/frontend-tests/SKILL.md"
                                        ],
                                    }
                                ],
                            },
                        ),
                        patch.object(agent, "diff_context", return_value=[change]),
                    ):
                        if error:
                            with self.assertRaises(error):
                                agent.run_pi(agent.ROOT, work)
                        else:
                            agent.run_pi(agent.ROOT, work)
                            result = json.loads((work / "result.json").read_text())
                            self.assertEqual(
                                result["skill_rules"],
                                {
                                    ".agents/skills/frontend-tests/SKILL.md": [
                                        "frontend"
                                    ]
                                },
                            )
                    calls = [
                        json.loads(line) for line in record.read_text().splitlines()
                    ]
                    self.assertEqual(len(calls), 2)
                    args = calls[0]["args"]
                    self.assertIn("--interactive", args)
                    self.assertNotIn("added_lines", calls[0]["prompt"]["diff"][0])
                    self.assertEqual(
                        calls[0]["prompt"]["diff"][0]["patch"], change["patch"]
                    )
                    self.assertGreater(len(json.dumps(calls[0]["prompt"])), 131072)
                    self.assertEqual(
                        calls[1]["args"],
                        ["rm", "--force", args[args.index("--name") + 1]],
                    )

    def test_review_metadata_round_trips_and_old_review_loses_generation_action(self):
        review = {
            "score": 3,
            "summary": "Handle <!-- --> and --> correctly",
            "gaps": [
                {
                    "path": "app.py",
                    "scenario": "Empty input",
                    "reason": "Missing boundary",
                }
            ],
        }
        body = agent.review_comment(
            {
                "review": review,
                "head_sha": "previous",
                "skill_rules": {".agents/skills/backend-tests/SKILL.md": ["backend"]},
            }
        )
        stored = json.loads(agent.re.search(r"<!-- review-data:(.*?) -->", body)[1])
        self.assertEqual(stored, {**review, "head_sha": "previous"})
        comment = {"id": 7, "user": {"login": "github-actions[bot]"}, "body": body}
        pr = {"head": {"sha": "current"}}
        with (
            patch.object(
                agent, "current_pr", return_value={"head": {"sha": "previous"}}
            ) as read_pr,
            patch.object(agent, "api", side_effect=[[comment], comment, {}]) as request,
        ):
            agent.mark_review_stale(1, "current")
            read_pr.assert_not_called()
            outdated = request.call_args.args[2]["body"]
        self.assertIn("Outdated review", outdated)
        self.assertNotIn("generate tests", outdated)
        self.assertEqual(
            json.loads(agent.re.search(r"<!-- review-data:(.*?) -->", outdated)[1]),
            stored,
        )
        for current, text in (("previous", body), ("current", outdated)):
            with (
                self.subTest(current=current),
                patch.object(
                    agent, "current_pr", return_value={"head": {"sha": current}}
                ),
                patch.object(
                    agent, "api", return_value=[{**comment, "body": text}]
                ) as request,
            ):
                agent.mark_review_stale(1)
                self.assertEqual(request.call_count, 1)
        with (
            patch.object(agent, "current_pr", return_value=pr),
            patch.object(
                agent,
                "api",
                side_effect=[[comment], {**comment, "body": "A newer review"}],
            ) as request,
        ):
            agent.mark_review_stale(1)
            self.assertEqual(request.call_count, 2)

    def test_generation_report_includes_files_and_scenarios_and_rejects_unknown_status(
        self,
    ):
        result = {
            "files": [{"path": "backend/tests/test_example.py", "content": "test"}],
            "generation_summary": "Covers empty input.\nPreserves unrelated records.",
        }
        for status, label in (("success", "✅ Passed"), ("failure", "❌ Failed")):
            with self.subTest(status=status):
                body = agent.generation_comment(
                    result, "abc", status, "https://example.com/logs"
                )
                self.assertIn(label, body)
                self.assertIn(result["files"][0]["path"], body)
                self.assertIn("Preserves unrelated records.", body)
        for status in ("cancelled", "", None):
            with self.subTest(status=status), self.assertRaises(ValueError):
                agent.generation_comment(
                    result, "abc", status, "https://example.com/logs"
                )

    def test_rules_match_conditions_on_the_same_file_and_deduplicate_skills(self):
        rules = [
            {"name": "backend", "paths": ["backend/**"], "skills": ["pytest"]},
            {
                "name": "endpoint",
                "paths": ["backend/**"],
                "added_lines": [r"^@router\.get"],
                "skills": ["pytest", "api"],
            },
            {
                "name": "module",
                "added_paths": ["backend/features/**"],
                "skills": ["module"],
            },
        ]
        changes = [
            {
                "path": "backend/features/new.py",
                "status": "A",
                "added_lines": "def helper(): pass",
            },
            {
                "path": "frontend/example.ts",
                "status": "M",
                "added_lines": "@router.get",
            },
        ]
        self.assertEqual(
            agent.select_skills(rules, changes),
            {"pytest": ["backend"], "module": ["module"]},
        )
        changes[0]["added_lines"] = 'def helper(): pass\n@router.get("/new")'
        self.assertEqual(
            agent.select_skills(rules, changes),
            {
                "pytest": ["backend", "endpoint"],
                "api": ["endpoint"],
                "module": ["module"],
            },
        )

    def test_review_requires_consistent_score_and_actionable_changed_code(self):
        gap = {
            "path": "app.py",
            "scenario": "empty input",
            "reason": "boundary untested",
        }
        for score, gaps in [(5, []), (4, [gap]), (1, [gap])]:
            agent.validate_review(
                {"score": score, "summary": "Assessment", "gaps": gaps}, {"app.py"}
            )
        for score, gaps in [
            (5, [gap]),
            (4, []),
            (True, []),
            (0, []),
            (3, [{**gap, "path": "unchanged.py"}]),
            (3, [{**gap, "scenario": ""}]),
        ]:
            with self.subTest(score=score, gaps=gaps), self.assertRaises(ValueError):
                agent.validate_review(
                    {"score": score, "summary": "Assessment", "gaps": gaps}, {"app.py"}
                )

    def test_only_test_files_are_publishable(self):
        for path in [
            "backend/tests/test_new.py",
            "backend/tests/features/test_new.py",
            "frontend/src/features/new.test.tsx",
        ]:
            agent.validate_files([{"path": path, "content": "test content"}])
        for path in [
            "../backend/tests/test_x.py",
            "/backend/tests/test_x.py",
            "backend/tests/../app/test_x.py",
            "backend/app/router.py",
            ".github/workflows/test.yml",
            "frontend/package.json",
            "backend/tests/conftest.py",
            "frontend/src/../../test_x.test.ts",
            "backend\\tests\\test_x.py",
        ]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                agent.validate_files([{"path": path, "content": "test content"}])
        item = {"path": "backend/tests/test_new.py", "content": "x"}
        for files in [[], [item, item], [{**item, "content": ""}]]:
            with self.subTest(files=files), self.assertRaises(ValueError):
                agent.validate_files(files)

    def test_pi_events_sum_each_completed_call_and_surface_model_errors(self):
        def event(text, cost):
            return {
                "type": "message_end",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": text}],
                    "usage": {"cost": {"total": cost}},
                },
            }

        records = [
            {"type": "message_update", "usage": {"cost": {"total": 99}}},
            event("Reading files", 0.01),
            event('{"score":5}', 0.02),
        ]
        answer, cost = agent.parse_events("\n".join(map(json.dumps, records)))
        self.assertEqual(answer, '{"score":5}')
        self.assertAlmostEqual(cost, 0.03)
        with self.assertRaisesRegex(ValueError, "rate limit"):
            agent.parse_events(
                json.dumps(
                    {
                        "type": "message_end",
                        "message": {
                            "role": "assistant",
                            "stopReason": "error",
                            "errorMessage": "rate limit",
                        },
                    }
                )
            )
        for reason in ("aborted", "length"):
            with (
                self.subTest(reason=reason),
                self.assertRaisesRegex(ValueError, reason),
            ):
                agent.parse_events(
                    json.dumps(
                        {
                            "type": "message_end",
                            "message": {"role": "assistant", "stopReason": reason},
                        }
                    )
                )

    def test_full_diff_preserves_renames_deletions_and_empty_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)

            def git(*args):
                return agent.command(
                    "git",
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.com",
                    *args,
                    cwd=source,
                ).strip()

            git("init", "-q")
            (source / "old.py").write_text(
                '@router.get("/existing")\n' + "# unchanged\n" * 20
            )
            (source / "deleted.py").write_text("removed = True\n")
            git("add", ".")
            git("commit", "-qm", "base")
            base = git("rev-parse", "HEAD")
            (source / "old.py").rename(source / "new.py")
            (source / "deleted.py").unlink()
            git("add", "-A")
            git("commit", "-qm", "rename and delete")
            head = git("rev-parse", "HEAD")
            changes = {
                c["path"]: c
                for c in agent.diff_context(
                    source, {"base_sha": base, "head_sha": head}
                )
            }
            self.assertTrue(changes["new.py"]["status"].startswith("R"))
            self.assertIn("rename from old.py", changes["new.py"]["patch"])
            self.assertEqual(changes["new.py"]["added_lines"], "")
            self.assertEqual(changes["deleted.py"]["status"], "D")
            self.assertIn("-removed = True", changes["deleted.py"]["patch"])
            self.assertEqual(
                agent.diff_context(source, {"base_sha": head, "head_sha": head}), []
            )

    def test_pr_must_be_open_same_repository_and_at_reviewed_sha(self):
        pr = {
            "state": "open",
            "head": {"sha": "expected", "repo": {"full_name": agent.REPO}},
        }
        with patch.object(agent, "api", return_value=pr):
            self.assertEqual(agent.current_pr(3, "expected"), pr)
            with self.assertRaisesRegex(ValueError, "changed"):
                agent.current_pr(3, "old")
        for value in [
            {**pr, "state": "closed"},
            {**pr, "head": {"sha": "expected", "repo": {"full_name": "fork/repo"}}},
        ]:
            with (
                patch.object(agent, "api", return_value=value),
                self.assertRaises(ValueError),
            ):
                agent.current_pr(3)


if __name__ == "__main__":
    unittest.main()
