#!/usr/bin/env python3
"""Unit tests for agent-nudge CLI utility."""

import datetime
from importlib.machinery import SourceFileLoader
import importlib.util
from pathlib import Path
import unittest

SCRIPT_PATH = Path.home() / ".local/bin/agent-nudge"
loader = SourceFileLoader("agent_nudge", str(SCRIPT_PATH))
spec = importlib.util.spec_from_loader("agent_nudge", loader)
agent_nudge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_nudge)


class TestAgentNudge(unittest.TestCase):
    def setUp(self):
        self.mock_agents = [
            {
                "pane_id": "w1:p6",
                "display_agent": "usps-setup",
                "agent": "codex",
                "agent_status": "working",
                "terminal_title_stripped": "usps-setup | usps",
                "agent_session": {"value": "01a16705-6d9a-7112-ae9f-52d65263134f"},
            },
            {
                "pane_id": "w1:p8",
                "display_agent": "usps-agy",
                "agent": "agy",
                "agent_status": "idle",
                "terminal_title_stripped": None,
                "agent_session": {"value": "3ef06365-8754-4186-b8bb-f35324537b4f"},
            },
        ]

    def test_resolve_target_exact_display_name(self):
        agent = agent_nudge.resolve_target("usps-setup", self.mock_agents)
        self.assertIsNotNone(agent)
        self.assertEqual(agent["pane_id"], "w1:p6")

    def test_resolve_target_exact_pane_id(self):
        agent = agent_nudge.resolve_target("w1:p8", self.mock_agents)
        self.assertIsNotNone(agent)
        self.assertEqual(agent["display_agent"], "usps-agy")

    def test_resolve_target_shorthand_pane_id(self):
        agent = agent_nudge.resolve_target("p6", self.mock_agents)
        self.assertIsNotNone(agent)
        self.assertEqual(agent["display_agent"], "usps-setup")

    def test_resolve_target_session_uuid(self):
        agent = agent_nudge.resolve_target(
            "01a16705-6d9a-7112-ae9f-52d65263134f", self.mock_agents
        )
        self.assertIsNotNone(agent)
        self.assertEqual(agent["display_agent"], "usps-setup")

    def test_resolve_target_case_insensitive_substring(self):
        agent = agent_nudge.resolve_target("agy", self.mock_agents)
        self.assertIsNotNone(agent)
        self.assertEqual(agent["display_agent"], "usps-agy")

    def test_parse_reset_datetime_full_date(self):
        text = "visit https://chatgpt.com/settings/usage to purchase more credits or try again at Oct 29th, 2026 3:17 AM."
        dt = agent_nudge.parse_reset_datetime(text)
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 10)
        self.assertEqual(dt.day, 29)
        self.assertEqual(dt.hour, 3)
        self.assertEqual(dt.minute, 17)

    def test_parse_reset_datetime_on_date(self):
        text = "⚠ 5h limit: 7% left · resets at 3:17 AM on 29 Oct · /status"
        dt = agent_nudge.parse_reset_datetime(text)
        self.assertIsNotNone(dt)
        self.assertEqual(dt.month, 10)
        self.assertEqual(dt.day, 29)
        self.assertEqual(dt.hour, 3)
        self.assertEqual(dt.minute, 17)

    def test_parse_reset_datetime_time_only(self):
        text = "resets at 4:30 PM · /status"
        dt = agent_nudge.parse_reset_datetime(text)
        self.assertIsNotNone(dt)
        self.assertEqual(dt.hour, 16)
        self.assertEqual(dt.minute, 30)

    def test_inspect_session_parsing(self):
        sample_output = """
        • Working on feature
        ■ You’ve hit your usage limit. Upgrade to Pro, visit https://chatgpt.com/settings/usage or try again at Oct 29th, 2026 3:17 AM.
        usps-setup · GPT-6.1-Sol · default · usps · Ready · 5h 0% left · weekly 84% left
        """
        agent_meta = {
            "display_agent": "usps-setup",
            "agent": "codex",
            "agent_status": "done",
        }
        # Monkeypatch read_pane_output for testing
        orig_read = agent_nudge.read_pane_output
        try:
            agent_nudge.read_pane_output = lambda pane_id, lines=60: sample_output
            info = agent_nudge.inspect_session("w1:p6", agent_meta)
            self.assertEqual(info["credit_percent"], 0)
            self.assertEqual(info["weekly_percent"], 84)
            self.assertTrue(info["has_limit_notice"])
            self.assertIsNotNone(info["reset_time"])
        finally:
            agent_nudge.read_pane_output = orig_read

    def test_inspect_session_human_blocker(self):
        sample_output = """
        • The Mac is locked. Please unlock it and reply “unlocked” so I can finish the live popover review.
        usps-setup · GPT-6.1-Sol · default · usps · Ready · 5h 100% left · weekly 78% left
        """
        agent_meta = {
            "display_agent": "usps-setup",
            "agent": "codex",
            "agent_status": "done",
        }
        orig_read = agent_nudge.read_pane_output
        try:
            agent_nudge.read_pane_output = lambda pane_id, lines=60: sample_output
            info = agent_nudge.inspect_session("w1:p6", agent_meta)
            self.assertTrue(info["is_waiting_human"])
            self.assertIn("Screen locked", info["human_reason"])
            self.assertEqual(info["credit_percent"], 100)
            self.assertFalse(info["is_currently_limited"])
        finally:
            agent_nudge.read_pane_output = orig_read

    def test_format_duration(self):
        self.assertEqual(agent_nudge.format_duration(45), "45s")
        self.assertEqual(agent_nudge.format_duration(125), "2m 05s")
        self.assertEqual(agent_nudge.format_duration(3665), "1h 01m 05s")


if __name__ == "__main__":
    unittest.main()
