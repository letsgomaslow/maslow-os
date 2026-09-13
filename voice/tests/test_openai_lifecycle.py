"""OpenAI lifecycle and PCM delivery regressions without accounts or sockets."""
import asyncio
import base64
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from maslow_voice.providers.base import ProviderError
from maslow_voice.providers.openai_realtime import OpenAIRealtimeProvider
from maslow_voice.voices import OPENAI_VOICES


class Socket:
    def __init__(self):
        self.sent = []
        self.inbox = asyncio.Queue()
        self.updated = True
        self.closed = False
        self.configured = asyncio.Event()

    async def send(self, value):
        event = json.loads(value)
        self.sent.append(event)
        if event['type'] == 'session.update':
            self.configured.set()
            if self.updated:
                self.inbox.put_nowait(json.dumps({'type': 'session.updated'}))

    async def recv(self):
        value = await self.inbox.get()
        if isinstance(value, Exception):
            raise value
        return value

    async def close(self):
        self.closed = True


class Audio:
    def __init__(self):
        self.played_ms = 0
        self.frames = []
        self.start = AsyncMock()
        self.set_muted = AsyncMock()
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.cleared = asyncio.Event()
        self.blocked = False
        self.stopped = False
        self.generation = 0

    async def play(self, frame):
        generation = self.generation
        self.entered.set()
        if self.blocked:
            await self.release.wait()
        if generation == self.generation:
            self.frames.append(frame)
            self.played_ms += len(frame.pcm) * 500 // frame.sample_rate

    async def wait_playback(self):
        pass

    async def clear_playback(self):
        self.generation += 1
        self.played_ms = 0
        self.cleared.set()
        self.release.set()

    async def stop(self):
        self.stopped = True
        await self.clear_playback()


class OpenAILifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.socket, self.audio = Socket(), Audio()
        self.events = []
        self.factory = AsyncMock(return_value=self.socket)
        async def emit(event):
            self.events.append(event)
        self.provider = OpenAIRealtimeProvider(config={'socket_factory': self.factory}, secrets={'openai': 'fixture-private-key'},
                                               emit=emit, submit=AsyncMock(), audio_transport=self.audio)

    async def asyncTearDown(self):
        await self.provider.stop()

    async def output(self, response='r1', item='a1', samples=240):
        await self.provider._handle_event({'type': 'response.created', 'response': {'id': response}})
        await self.provider._handle_event({'type': 'response.output_item.added', 'response_id': response,
                                          'item': {'id': item, 'role': 'assistant'}})
        await self.provider._handle_event({'type': 'response.output_audio.delta', 'response_id': response, 'item_id': item,
                                          'delta': base64.b64encode(b'\x01\x00' * samples).decode()})

    async def test_all_allowed_voices_and_default_reach_pcm24k_session_configuration(self):
        self.assertEqual(self.provider._session_config('gpt-realtime-2.1', True)['audio']['output']['voice'], 'cedar')
        for voice in OPENAI_VOICES:
            self.provider.config['realtime_voice'] = voice
            config = self.provider._session_config('gpt-realtime-2.1', True)
            self.assertEqual(config['audio']['output']['voice'], voice)
            self.assertEqual(config['audio']['output']['format']['rate'], 24000)
            self.assertFalse(config['audio']['input']['turn_detection']['interrupt_response'])
        self.provider.config['realtime_voice'] = 'not-a-realtime-voice'
        with self.assertRaises(ProviderError):
            await self.provider.start()
        self.factory.assert_not_called()

    async def test_cancelled_start_closes_socket_reader_and_capture(self):
        self.socket.updated = False
        task = asyncio.create_task(self.provider.start())
        await self.socket.configured.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(self.socket.closed)
        self.assertTrue(self.audio.stopped)
        self.assertIsNone(self.provider._reader)
        self.assertFalse(self.provider._started)

    async def test_restart_requires_fresh_handshake_and_unmutes_capture(self):
        await self.provider.start()
        await self.provider.mute(True)
        await self.provider.stop()
        self.socket.updated = False
        self.socket.configured.clear()
        task = asyncio.create_task(self.provider.start())
        await self.socket.configured.wait()
        self.assertFalse(task.done())
        self.socket.inbox.put_nowait(json.dumps({'type': 'session.updated'}))
        await task
        self.assertFalse(self.provider._muted)
        self.audio.set_muted.assert_awaited_with(False)

    async def test_audio_shutdown_failure_still_closes_socket_and_reader(self):
        await self.provider.start()
        self.audio.stop = AsyncMock(side_effect=RuntimeError('private driver diagnostic'))
        with self.assertRaises(ProviderError):
            await self.provider.stop()
        self.assertTrue(self.socket.closed)
        self.assertIsNone(self.provider._reader)
        self.assertIsNone(self.provider._playback_task)
        self.assertFalse(self.provider._started)
        self.audio.stop = AsyncMock()

    async def test_backpressure_does_not_block_vad_and_cancelled_deltas_cannot_resume_sound(self):
        await self.provider.start()
        self.audio.blocked = True
        await self.output()
        await self.audio.entered.wait()
        self.socket.inbox.put_nowait(json.dumps({'type': 'input_audio_buffer.speech_started'}))
        await asyncio.wait_for(self.audio.cleared.wait(), 1)
        await self.provider.wait_playback()
        self.assertTrue(any(event['type'] == 'response.cancel' for event in self.socket.sent))
        await self.provider._handle_event({'type': 'response.output_audio.delta', 'response_id': 'r1', 'item_id': 'a1',
                                          'delta': base64.b64encode(b'\x02\x00' * 240).decode()})
        await self.provider.wait_playback()
        self.assertEqual(self.audio.frames, [])

    async def test_truncate_counts_current_assistant_item_not_previous_reply(self):
        await self.provider.start()
        await self.output(samples=2400)
        await self.provider.wait_playback()
        self.assertEqual(self.audio.played_ms, 100)
        await self.provider._handle_event({'type': 'response.done', 'response': {'id': 'r1', 'status': 'completed'}})
        await self.output(response='r2', item='a2', samples=360)
        await self.provider.wait_playback()
        self.assertEqual(self.audio.played_ms, 115)
        await self.provider.silence()
        truncate = next(event for event in reversed(self.socket.sent) if event['type'] == 'conversation.item.truncate')
        self.assertEqual(truncate['item_id'], 'a2')
        self.assertEqual(truncate['audio_end_ms'], 15)

    async def test_generation_done_keeps_speaking_until_audio_finishes(self):
        await self.provider.start()
        self.audio.blocked = True
        await self.output()
        await self.audio.entered.wait()
        await self.provider._handle_event({'type': 'response.done', 'response': {'id': 'r1', 'status': 'completed'}})
        await asyncio.sleep(0)
        self.assertEqual(self.events[-1]['state'], 'speaking')
        self.audio.release.set()
        await asyncio.gather(*self.provider._drain_tasks)
        self.assertEqual(self.events[-1]['state'], 'listening')

    async def test_interrupt_and_new_turn_prevent_old_playback_drain_from_changing_state(self):
        await self.provider.start()
        self.audio.blocked = True
        await self.output()
        await self.audio.entered.wait()
        await self.provider._handle_event({'type': 'response.done', 'response': {'id': 'r1', 'status': 'completed'}})
        old_drains = tuple(self.provider._drain_tasks)
        await self.provider._handle_event({'type': 'input_audio_buffer.speech_started'})
        await self.provider._handle_event({'type': 'response.created', 'response': {'id': 'r2'}})
        before = len(self.events)
        await asyncio.gather(*old_drains)
        self.assertEqual(len(self.events), before)
        self.assertEqual(self.events[-1]['state'], 'thinking')

    async def test_stop_joins_pending_playback_drain_without_stale_listening(self):
        await self.provider.start()
        self.audio.blocked = True
        await self.output()
        await self.audio.entered.wait()
        await self.provider._handle_event({'type': 'response.done', 'response': {'id': 'r1', 'status': 'completed'}})
        old_drains = tuple(self.provider._drain_tasks)
        await self.provider.stop()
        self.assertTrue(all(task.done() for task in old_drains))
        self.assertEqual(self.events[-1]['state'], 'disabled')
        self.assertFalse(self.provider._drain_tasks)

    async def test_failed_response_rejects_typed_waiter_with_safe_quota_error(self):
        await self.provider.start()
        typed = asyncio.create_task(self.provider.text('Read the sample'))
        await asyncio.sleep(0)
        await self.provider._handle_event({'type': 'response.done', 'response': {'id': 'failed', 'status': 'failed',
            'status_details': {'error': {'code': 'insufficient_quota', 'message': 'fixture-private-key'}}}})
        with self.assertRaises(ProviderError) as caught:
            await typed
        self.assertEqual(caught.exception.code, 'OPENAI_USAGE_LIMIT')
        self.assertTrue(self.audio.stopped)
        self.assertNotIn('fixture-private-key', json.dumps(self.events))
        self.assertFalse(self.provider._started)

    async def test_typed_turn_uses_one_32_character_identity_for_message_transcript_and_response(self):
        await self.provider.start()
        typed = asyncio.create_task(self.provider.text('Read the sample'))
        await asyncio.sleep(0)
        message = next(event['item'] for event in self.socket.sent if event['type'] == 'conversation.item.create')
        response = next(event['response'] for event in self.socket.sent if event['type'] == 'response.create')
        transcript = next(event for event in self.events if event['type'] == 'transcript' and event['role'] == 'user')
        self.assertRegex(message['id'], r'^[0-9a-f]{32}$')
        self.assertEqual(transcript['turn_id'], message['id'])
        self.assertEqual(response['metadata']['maslow_turn_id'], message['id'])
        await self.provider._handle_event({'type': 'response.created', 'response': {'id': 'typed-response', 'metadata': response['metadata']}})
        await self.provider._handle_event({'type': 'response.done', 'response': {'id': 'typed-response', 'status': 'completed'}})
        await typed

    async def test_socket_failure_revokes_capture_and_reports_safe_error(self):
        await self.provider.start()
        self.socket.inbox.put_nowait(RuntimeError('fixture-private-key'))
        await self.provider._reader
        self.assertTrue(self.audio.stopped)
        self.assertFalse(self.provider._started)
        self.assertEqual(self.events[-1]['state'], 'error')
        self.assertNotIn('fixture-private-key', json.dumps(self.events))

    async def test_audio_backlog_is_bounded_and_explicitly_fails(self):
        await self.provider.start()
        self.provider._max_audio_bytes = 2
        await self.output(samples=240)
        self.assertEqual(self.provider._start_failure.code, 'OPENAI_AUDIO_BACKLOG')
        self.assertEqual(self.provider._queued_audio_bytes, 0)
        self.assertTrue(self.provider._playback_queue.empty())
        self.assertTrue(self.audio.stopped)

    async def test_safe_errors_use_structured_status_and_never_raw_diagnostics(self):
        for status, code in [(401, 'OPENAI_AUTH_FAILED'), (403, 'OPENAI_AUTH_FAILED'), (429, 'OPENAI_USAGE_LIMIT')]:
            error = RuntimeError('fixture-private-key')
            error.response = SimpleNamespace(status_code=status)
            public = self.provider._public_error(error)
            self.assertEqual(public.code, code)
            self.assertNotIn('fixture-private-key', public.message)
        public = self.provider._public_error({'type': 'invalid_request_error', 'message': 'fixture-private-key'})
        self.assertEqual(public.code, 'OPENAI_SETUP_FAILED')
        public = self.provider._public_error({'code': 'unknown-code', 'type': 'invalid_request_error', 'message': 'fixture-private-key'})
        self.assertEqual(public.code, 'OPENAI_SETUP_FAILED')
        self.assertEqual(self.provider._public_error(TypeError('fixture-private-key')).code, 'OPENAI_PROTOCOL_FAILED')


if __name__ == '__main__':
    unittest.main()
