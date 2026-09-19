import unittest

from maslow_voice.errors import VoiceError
from maslow_voice.live_tasks import LiveTaskPlanner, LiveTranscript, live_request_id, live_update_text


class LiveTranscriptTests(unittest.IsolatedAsyncioTestCase):
    def test_snapshot_keeps_fragments_role_labelled_and_respects_delegation_offset(self):
        transcript = LiveTranscript()
        transcript.append("user", "Create ", 10, 20)
        transcript.append("user", "a file", 20, 40)
        transcript.append("assistant", "I can do that.", 45, 60)
        transcript.append("user", "later correction", 80, 90)
        self.assertEqual(transcript.snapshot(60), [
            {"role": "user", "text": "Create a file", "start_ms": 10, "end_ms": 40},
            {"role": "assistant", "text": "I can do that.", "start_ms": 45, "end_ms": 60},
        ])

    def test_snapshot_does_not_absorb_late_untimed_fragments(self):
        transcript = LiveTranscript()
        transcript.append("user", "delegated words")
        boundary = transcript.mark()
        transcript.append("user", " later conversation")
        self.assertEqual(transcript.snapshot(60, boundary), [
            {"role": "user", "text": "delegated words", "start_ms": None, "end_ms": None},
        ])

    async def test_planner_uses_latest_user_words_and_selected_agent_without_inventing_a_turn(self):
        planner = LiveTaskPlanner()
        plan = await planner.prepare([
            {"role": "user", "text": "Create a harmless note."},
            {"role": "assistant", "text": "Which agent should handle it?"},
            {"role": "user", "text": "Use Codex."},
        ], context="Inside the selected project.", preferred_coder="codex")
        brief, source = plan["brief"], plan["source"]
        self.assertEqual(plan["action"], "new")
        self.assertEqual(brief["objective"], "Use Codex.")
        self.assertEqual(brief["tool_preference"], "codex")
        self.assertIn("Create a harmless note", source)
        self.assertIn("Explicit user context", source)
        self.assertEqual(brief["unresolved_questions"], [])

    async def test_planner_rejects_delegation_without_user_transcript(self):
        with self.assertRaises(VoiceError) as caught:
            await LiveTaskPlanner().prepare([{"role": "assistant", "text": "Hello"}])
        self.assertEqual(caught.exception.code, "TRANSCRIPT_PENDING")

    async def test_explicit_cancel_and_redirect_control_one_active_task(self):
        planner = LiveTaskPlanner()
        active = [{"id": "task-1"}]
        cancel = await planner.prepare([{"role": "user", "text": "Cancel that task."}], active_tasks=active)
        self.assertEqual(cancel["action"], "cancel")
        self.assertEqual(cancel["task_id"], "task-1")
        redirect = await planner.prepare(
            [{"role": "user", "text": "Change that task to write two notes."}], active_tasks=active)
        self.assertEqual(redirect, {
            "action": "steer", "task_id": "task-1", "text": "write two notes.",
            "source": "User transcript: Change that task to write two notes.",
        })

    async def test_control_request_does_not_guess_between_active_tasks(self):
        with self.assertRaises(VoiceError) as caught:
            await LiveTaskPlanner().prepare(
                [{"role": "user", "text": "Stop the task"}],
                active_tasks=[{"id": "one"}, {"id": "two"}],
            )
        self.assertEqual(caught.exception.code, "TASK_SELECTION_REQUIRED")

    async def test_conversational_comment_preserves_words_but_grants_no_action(self):
        plan = await LiveTaskPlanner().prepare([
            {"role": "user", "text": "That sounds useful."},
        ], preferred_coder="hermes")
        self.assertEqual(plan["brief"]["summary"], "That sounds useful.")
        self.assertIn("Do not change files or take an external action", plan["brief"]["constraints"][-1])

    def test_request_identity_and_context_updates_are_bounded(self):
        first = live_request_id("session", "delegation", "source")
        self.assertEqual(first, live_request_id("session", "delegation", "source"))
        self.assertNotEqual(first, live_request_id("session", "other", "source"))
        self.assertLessEqual(len(first), 128)
        self.assertLessEqual(len(live_update_text("é" * 1000).encode()), 480)
