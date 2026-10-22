import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_agent as agent


class TestAgent(unittest.TestCase):
    def test_only_maintainers_can_generate_and_sufficient_review_is_a_noop(self):
        event = {"sender": {"login": "owner"}, "comment": {"body": "generate tests"}, "issue": {"number": 1}}
        pr = {"state": "open", "head": {"sha": "current", "ref": "feature", "repo": {"full_name": agent.REPO}}, "base": {"sha": "base"}}
        review = {"head_sha": "current", "score": 5, "gaps": []}
        comments = [{"user": {"login": "github-actions[bot]"}, "body": agent.MARKER + "\n<!-- review-data:" + json.dumps(review) + " -->"}]
        with patch.dict(agent.os.environ, {"GITHUB_EVENT_NAME": "issue_comment", "GITHUB_EVENT_PATH": "/event"}), patch.object(agent.Path, "read_text", return_value=json.dumps(event)), patch.object(agent, "output") as emit:
            for role in ("read", "triage", "write"):
                with self.subTest(role=role), patch.object(agent, "api", return_value={"role_name": role}), self.assertRaisesRegex(ValueError, "maintainers"):
                    agent.prepare(Path("/unused"))
            for role in ("maintain", "admin"):
                with self.subTest(role=role), patch.object(agent, "api", side_effect=[{"role_name": role}, pr, comments, {}]) as request:
                    agent.prepare(Path("/unused"))
                    emit.assert_called_with(mode="skip", number=1, head_sha="current")
                    self.assertIn("5/5", request.call_args.args[2]["body"])

    def test_rules_match_conditions_on_the_same_file_and_deduplicate_skills(self):
        rules = [
            {"name": "backend", "paths": ["backend/**"], "skills": ["pytest"]},
            {
                "name": "endpoint",
                "paths": ["backend/**"],
                "added_lines": [r"@router\.get"],
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
        changes[0]["added_lines"] = '@router.get("/new")'
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
