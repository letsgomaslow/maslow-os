import tempfile
import unittest
from pathlib import Path

from dev.gpt_live_backend import GPTLiveBackend
from maslow_voice.errors import VoiceError
from maslow_voice.store import TaskStore
from maslow_voice.tasks import TaskManager


BRIEF = {"objective": "Create a scratch page", "summary": "Create the requested small HTML page.",
         "constraints": [], "requested_output": "A small HTML file", "tool_preference": "auto",
         "unresolved_questions": []}


class GPTLiveBackendTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.scratch = self.root / "scratch"
        self.scratch.mkdir()
        self.store = TaskStore(self.root / "state")
        self.started = []

        async def client(_task):
            raise AssertionError("The unit test must not start an executor")

        async def publish():
            pass

        self.manager = TaskManager(self.store, client, publish)
        self.manager._start = self.started.append
        self.calls = []

        async def brief_builder(prompt, project):
            self.calls.append((prompt, project))
            return dict(BRIEF)

        self.backend = GPTLiveBackend(self.manager, brief_builder, self.scratch)

    async def asyncTearDown(self):
        await self.manager.close()
        self.store.close()
        self.temporary.cleanup()

    async def test_voice_and_typed_turns_share_idempotent_durable_backend(self):
        first = await self.backend.submit_turn(channel="voice", session_id="s1", turn_id="t1",
                                                text="Create a landing page", project=self.scratch,
                                                context="Use one heading.")
        repeated = await self.backend.submit_turn(channel="typed", session_id="s1", turn_id="t1",
                                                   text="Create a landing page", project=self.scratch,
                                                   context="Use one heading.")
        self.assertFalse(first["duplicate"])
        self.assertTrue(repeated["duplicate"])
        self.assertEqual(first["task"]["id"], repeated["task"]["id"])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(self.started), 1)
        self.assertIn("User-provided context", first["task"]["source"])
        self.assertIn("selected GPT-Live scratch project", first["task"]["brief"]["constraints"][-3])
        snapshot = self.backend.snapshot()
        self.assertGreaterEqual(snapshot["tasks"][0]["revision"], 1)

    async def test_redirect_stops_old_run_and_relaunches_same_task_revision(self):
        task = await self.backend.submit_turn(channel="typed", session_id="s1", turn_id="t2",
                                               text="Create a note", project=self.scratch)
        self.store.update(task["task"]["id"], state="running", run_id="run-1")

        class Client:
            async def stop(self, run_id):
                self.run_id = run_id

        client = Client()
        self.manager.clients[task["task"]["id"]] = client
        redirected = await self.backend.task_action(task["task"]["id"], "redirect", "Use a blue heading")
        self.assertEqual(client.run_id, "run-1")
        self.assertEqual(redirected["id"], task["task"]["id"])
        self.assertEqual(redirected["state"], "queued")
        self.assertEqual(redirected["attempt"], 1)
        self.assertIsNone(redirected["run_id"])
        self.assertIn("Explicit revision: Use a blue heading", redirected["brief"]["summary"])

    async def test_existing_task_survives_new_backend_after_conversation_end(self):
        created = await self.backend.submit_turn(channel="typed", session_id="s1", turn_id="t1",
                                                  text="Create a note", project=self.scratch)
        # A new transport/conversation backend discovers the persisted task by
        # its stable versioned request identity instead of submitting again.
        other = GPTLiveBackend(self.manager, self.backend.brief_builder, self.scratch)
        duplicate = await other.submit_turn(channel="voice", session_id="s1", turn_id="t1",
                                            text="Create a note", project=self.scratch)
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(created["task"]["id"], duplicate["task"]["id"])

    async def test_rejects_projects_outside_the_test_scratch_workspace(self):
        with self.assertRaisesRegex(VoiceError, "scratch workspace"):
            await self.backend.submit_turn(channel="typed", session_id="s", turn_id="t", text="Create a file", project=self.root)


    async def test_planner_interprets_all_actions_with_snapshot_and_deduplicates(self):
        plans = []
        async def planner(prompt, project):
            self.assertIn('transcript', prompt)
            self.assertIn('tasks', prompt)
            return plans.pop(0)
        self.backend.planner = planner
        async def delegate(identity):
            return await self.backend.submit_delegation(delegation_id=identity,
                transcript=[{'role': 'user', 'text': 'A natural request without keyword routing'}],
                project=self.scratch)
        plans.append({'action': 'clarify', 'question': 'What heading should the page use?'})
        self.assertEqual((await delegate('d1'))['action'], 'clarify')
        self.assertTrue((await delegate('d1'))['duplicate'])
        plans.append({'action': 'new', 'text': 'Create a page'})
        first = await delegate('d2')
        task_id = first['task']['id']
        plans.append({'action': 'redirect', 'task_id': task_id, 'text': 'Change heading'})
        revised = await delegate('d3')
        self.assertEqual(revised['task']['id'], task_id)
        self.assertEqual(revised['task']['attempt'], 1)
        plans.append({'action': 'cancel', 'task_id': task_id})
        self.assertEqual((await delegate('d4'))['task']['state'], 'cancelled')
        self.assertEqual(len(self.store.list()), 1)
        plans.append({'action': 'cancel', 'task_id': 'unknown'})
        with self.assertRaises(VoiceError):
            await delegate('d5')

    async def test_redirect_joins_old_monitor_before_revision(self):
        import asyncio
        task = (await self.backend.submit_turn(channel='typed', session_id='s', turn_id='t',
            text='Create a note', project=self.scratch))['task']
        identity = task['id']
        self.store.update(identity, state='running', run_id='old')
        class Client:
            async def stop(self, run_id):
                self.stopped = run_id
        client = Client()
        self.manager.clients[identity] = client
        async def stale_monitor():
            try:
                await asyncio.sleep(60)
            finally:
                self.store.update(identity, state='completed', result='stale result')
        monitor = asyncio.create_task(stale_monitor())
        self.manager.monitors[identity] = monitor
        await asyncio.sleep(0)
        revision = await self.backend.task_action(identity, 'redirect', 'Use blue')
        self.assertTrue(monitor.done())
        self.assertEqual(revision['state'], 'queued')
        self.assertEqual(revision['result'], '')
        self.assertEqual(revision['attempt'], 1)

class ScratchExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from dev.gpt_live_backend import HermesProfile, HermesScratchExecutor
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.scratch = self.root / 'scratch'
        self.scratch.mkdir()
        self.profile = HermesProfile(self.root / 'profile', 'unit-test-key')
        self.executor = HermesScratchExecutor(profile=self.profile)

    async def asyncTearDown(self):
        await self.executor.close()
        self.temporary.cleanup()

    async def run_script(self, script, artifact='page.html'):
        import sys
        from unittest.mock import patch
        task = {'id': 'task', 'project': str(self.scratch), 'brief': BRIEF,
                'source': 'Expected test artifact (must exist before completion): ' + artifact}
        self.profile.prepare()
        with patch.object(self.profile, 'command', return_value=[sys.executable, '-c', script]):
            result = await self.executor.submit(task)
        return result['run_id']

    async def test_profile_has_no_secret_files_or_ambient_environment(self):
        import os
        import json
        from unittest.mock import patch
        with patch.dict(os.environ, {'OTHER_API_KEY': 'must-not-inherit', 'HERMES_HOME': '/unrelated'}):
            model, env = self.profile.prepare()
        self.assertEqual(model['provider'], 'openai-api')
        self.assertEqual(model['default'], 'gpt-5-mini')
        self.assertEqual(env['OPENAI_API_KEY'], 'unit-test-key')
        self.assertNotIn('OTHER_API_KEY', env)
        self.assertEqual(env['HOME'], str(self.profile.root))
        self.assertFalse((self.profile.root / '.env').exists())
        config = json.loads((self.profile.root / 'config.yaml').read_text())
        self.assertEqual(config['platform_toolsets']['cli'], [])
        self.assertEqual(config['mcp_servers'], {})
        for path in self.profile.root.rglob('*'):
            if path.is_file():
                self.assertNotIn('unit-test-key', path.read_text())

    async def test_large_stdout_is_drained_before_exit_and_valid_artifact_published_once(self):
        run = await self.run_script('import json; print(json.dumps({"content": "x" * 100000}))')
        await self.executor.runs[run]['reader']
        self.assertEqual((await self.executor.status(run))['status'], 'completed')
        target = self.scratch / 'page.html'
        self.assertEqual(len(target.read_bytes()), 100000)
        target.write_text('user edit')
        self.assertEqual((await self.executor.status(run))['status'], 'completed')
        self.assertEqual(target.read_text(), 'user edit')

    async def test_preexisting_unchanged_artifact_is_not_success(self):
        target = self.scratch / 'page.html'
        target.write_text('old')
        run = await self.run_script('print(\'{"content":"old"}\')')
        await self.executor.runs[run]['reader']
        self.assertEqual((await self.executor.status(run))['status'], 'failed')
        self.assertEqual(target.read_text(), 'old')

    async def test_cancel_after_generation_suppresses_artifact_and_reports_cancelled(self):
        run = await self.run_script('print(\'{"content":"new"}\')')
        await self.executor.runs[run]['reader']
        await self.executor.stop(run)
        self.assertEqual((await self.executor.status(run))['status'], 'cancelled')
        self.assertFalse((self.scratch / 'page.html').exists())

    async def test_cancel_reaps_process_and_output_reader(self):
        import asyncio
        run = await self.run_script('import time; time.sleep(60)')
        await asyncio.wait_for(self.executor.stop(run), 5)
        self.assertIsNotNone(self.executor.runs[run]['process'].returncode)
        self.assertTrue(self.executor.runs[run]['reader'].done())
        self.assertEqual((await self.executor.status(run))['status'], 'cancelled')

    async def test_output_overflow_stops_process(self):
        from maslow_voice.errors import VoiceError
        run = await self.run_script('import sys,time; sys.stdout.write("x"*300000); sys.stdout.flush(); time.sleep(60)')
        with self.assertRaises(VoiceError):
            await self.executor.runs[run]['reader']
        self.assertEqual((await self.executor.status(run))['status'], 'failed')
        self.assertIsNotNone(self.executor.runs[run]['process'].returncode)

    async def test_concurrent_edit_and_symlink_are_not_overwritten(self):
        target = self.scratch / 'page.html'
        run = await self.run_script('print(\'{"content":"new"}\')')
        await self.executor.runs[run]['reader']
        target.write_text('user edit')
        self.assertEqual((await self.executor.status(run))['status'], 'failed')
        self.assertEqual(target.read_text(), 'user edit')
        target.unlink()
        target.symlink_to(self.root / 'outside.html')
        with self.assertRaises(VoiceError):
            await self.run_script('print(\'{"content":"unsafe"}\')')

    @unittest.skipUnless(Path('/usr/bin/sandbox-exec').exists(), 'Mac sandbox required')
    async def test_actual_sandbox_denies_write_outside_profile(self):
        import asyncio
        import sys
        command = self.profile.command('/unused', 'unused')
        inside = self.profile.root / 'allowed'
        outside = self.root / 'forbidden'
        script = f'from pathlib import Path; Path({str(inside)!r}).write_text("ok"); Path({str(outside)!r}).write_text("bad")'
        process = await asyncio.create_subprocess_exec(*command[:3], sys.executable, '-c', script,
                    env=self.profile.prepare()[1], stderr=asyncio.subprocess.DEVNULL)
        await process.wait()
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(inside.read_text(), 'ok')
        self.assertFalse(outside.exists())

    async def test_stderr_is_drained_and_only_allowlisted_diagnostic_survives(self):
        run = await self.run_script('import sys; sys.stderr.write("invalid_api_key secret-canary " + "x"*100000); sys.exit(1)')
        await self.executor.runs[run]['reader']
        result = await self.executor.status(run)
        self.assertEqual(result['error_code'], 'OPENAI_AUTH_FAILED')
        self.assertNotIn('secret-canary', str(result))
        self.assertNotIn('secret-canary', str(self.executor.runs[run]))

    async def test_cancellation_during_spawn_reaps_the_new_child(self):
        import asyncio
        import sys
        from unittest.mock import patch
        from dev.gpt_live_backend import _spawn
        self.profile.prepare()
        original = asyncio.create_subprocess_exec
        launched = asyncio.Event()
        release = asyncio.Event()
        children = []
        async def delayed(*args, **kwargs):
            process = await original(sys.executable, '-c', 'import time; time.sleep(60)', **kwargs)
            children.append(process)
            launched.set()
            await release.wait()
            return process
        with patch('dev.gpt_live_backend.asyncio.create_subprocess_exec', side_effect=delayed):
            spawning = asyncio.create_task(_spawn(self.profile, 'hermes', 'unused'))
            await launched.wait()
            spawning.cancel()
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await spawning
        self.assertIsNotNone(children[0].returncode)

    @unittest.skipUnless(Path('/usr/bin/sandbox-exec').exists(), 'Mac sandbox required')
    async def test_sandbox_blocks_session_persistence_and_dotenv_reads(self):
        import asyncio
        import sys
        command = self.profile.command('/unused', 'unused')
        dotenv = self.root / '.env'
        dotenv.write_text('test-only-canary')
        database = self.profile.root / 'state.db'
        session = self.profile.root / 'sessions' / 'request.json'
        script = ('from pathlib import Path\nblocked=0\n' +
                  f'for path,read in [({str(dotenv)!r},True),({str(database)!r},False),({str(session)!r},False)]:\n' +
                  ' try:\n  Path(path).read_text() if read else Path(path).write_text("data")\n' +
                  ' except PermissionError:\n  blocked+=1\nassert blocked==3\n')
        process = await asyncio.create_subprocess_exec(*command[:3], sys.executable, '-c', script,
                    env=self.profile.prepare()[1], stderr=asyncio.subprocess.DEVNULL)
        await process.wait()
        self.assertEqual(process.returncode, 0)
        self.assertFalse(database.exists())
        self.assertFalse(session.exists())

class JSONOutputTests(unittest.TestCase):
    def test_plain_and_whole_fenced_objects_are_accepted(self):
        from dev.gpt_live_backend import _parse_json_output
        for content in (b'{"content":"hello"}', b'```json\n{"content":"hello"}\n```',
                        b' \n```\n{"content":"hello"}\n```\n'):
            diagnostics = {}
            self.assertEqual(_parse_json_output(content, diagnostics), {'content': 'hello'})
            self.assertEqual(diagnostics['output_bytes'], len(content))
            self.assertIsNone(diagnostics['json_error'])

    def test_surrounding_prose_banner_and_multiple_objects_are_not_salvaged(self):
        from dev.gpt_live_backend import _parse_json_output
        for content in (b'Here it is {"content":"private-canary"}',
                        b'Warning: private-canary\n{"content":"hello"}',
                        b'```json\n{"content":"private-canary"}\n```\nextra',
                        b'{"content":"private-canary"}\n{}', b'[]', b'\xff'):
            diagnostics = {}
            with self.assertRaises(VoiceError):
                _parse_json_output(content, diagnostics)
            self.assertIn(diagnostics['json_error'], {'JSONDecodeError', 'ValueError', 'UnicodeDecodeError'})
            self.assertNotIn('private-canary', str(diagnostics))
            self.assertNotIn('Here it is', str(diagnostics))

    def test_synthetic_debug_redacts_key_headers_assignments_and_paths(self):
        from dev.gpt_live_backend import _redact_synthetic_output
        output = b'Error canary-key Authorization: Bearer secret-canary api_key=another-canary /Users/private/profile'
        result = _redact_synthetic_output(output, 'canary-key')
        for sensitive in ('canary-key', 'secret-canary', 'another-canary', '/Users/private'):
            self.assertNotIn(sensitive, result)
        self.assertIn('Error', result)
