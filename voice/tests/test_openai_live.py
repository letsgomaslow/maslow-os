"""GPT-Live protocol tests; only fake sockets and synthetic PCM are used."""
import asyncio
import base64
import json
import unittest
from unittest.mock import AsyncMock

from maslow_voice.audio import PcmFrame
from maslow_voice.providers.base import ProviderError
from maslow_voice.providers.openai_live import OpenAILiveProvider


class Socket:
    def __init__(self):
        self.sent = []
        self.inbox = asyncio.Queue()
        self.send_times = []
        self.closed = False
        self.ack_start = self.ack_close = True
        self.start_sent = asyncio.Event()

    async def send(self, message):
        event = json.loads(message)
        self.sent.append(event)
        self.send_times.append(asyncio.get_running_loop().time())
        if event['type'] == 'session.start':
            self.start_sent.set()
            if self.ack_start:
                self.inbox.put_nowait(json.dumps({'type': 'session.started', 'session': {'id': 'private-session-id'}}))
        if event['type'] == 'session.close' and self.ack_close:
            self.inbox.put_nowait(json.dumps({'type': 'session.closed', 'reason': 'close_requested', 'usage': {'seconds': 17}}))

    async def recv(self):
        value = await self.inbox.get()
        if isinstance(value, Exception):
            raise value
        return value

    async def close(self):
        self.closed = True


class Audio:
    def __init__(self):
        self.start = AsyncMock()
        self.set_muted = AsyncMock()
        self.stop = AsyncMock()
        self.clear_playback = AsyncMock()
        self.play = AsyncMock()
        self.wait_playback = AsyncMock()


class OpenAILiveTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.socket, self.audio = Socket(), Audio()
        self.events = []
        self.factory = AsyncMock(return_value=self.socket)
        self.submit = AsyncMock()
        async def emit(event):
            self.events.append(event)
        self.provider = OpenAILiveProvider(config={'socket_factory': self.factory, 'live_close_timeout': .02},
                                           secrets={'openai': 'private-fixture-key'}, emit=emit, submit=self.submit,
                                           audio_transport=self.audio)

    async def asyncTearDown(self):
        await self.provider.stop()

    async def test_start_uses_live_endpoint_session_start_and_client_pcm_configuration(self):
        await self.provider.start()
        args = self.factory.call_args.args
        self.assertEqual(args[0], 'wss://api.openai.com/v1/live/sessions')
        self.assertEqual(args[1], {'Authorization': 'Bearer private-fixture-key'})
        first = self.socket.sent[0]
        self.assertEqual(first['type'], 'session.start')
        self.assertEqual(first['session']['model'], 'gpt-live-1')
        self.assertEqual(first['session']['delegation'], {'type': 'client'})
        self.assertEqual(first['session']['audio'], {'format': {'type': 'audio/pcm', 'rate': 24000}, 'output': {'voice': 'marin'}})
        self.assertFalse(first['session']['store'])
        self.assertNotIn('tools', first['session'])
        self.assertTrue(self.provider.metrics_snapshot()['session_started'])
        self.assertNotIn('private-', json.dumps(self.provider.metrics_snapshot()))

    async def test_input_sends_silence_and_resamples_without_turn_commit(self):
        await self.provider.start()
        handler = self.audio.start.call_args.args[0]
        await handler(PcmFrame(b'\0' * 1920, 48000))
        await handler(PcmFrame(b'\x11\x00' * 960, 48000))
        appends = [event for event in self.socket.sent if event['type'] == 'session.input_audio.append']
        self.assertEqual(len(appends), 2)
        self.assertEqual(base64.b64decode(appends[0]['audio']), b'\0' * 960)
        self.assertEqual(len(base64.b64decode(appends[1]['audio'])), 960)
        self.assertFalse(any(event['type'] in {'response.create', 'input_audio_buffer.commit'} for event in self.socket.sent))

    async def test_slow_transcript_delivery_does_not_hold_microphone_input(self):
        await self.provider.start()
        entered, release = asyncio.Event(), asyncio.Event()
        original_emit = self.provider._emit_callback
        async def slow_transcript(event):
            if event['type'] == 'transcript_delta':
                entered.set()
                await release.wait()
            await original_emit(event)
        self.provider._emit_callback = slow_transcript
        delivery = asyncio.create_task(self.provider._handle_event({
            'type': 'session.input_transcript.delta', 'delta': 'Known test words',
            'start_ms': 0, 'end_ms': 40,
        }))
        try:
            await asyncio.wait_for(entered.wait(), .5)
            handler = self.audio.start.call_args.args[0]
            await asyncio.wait_for(handler(PcmFrame(b'\x11\x00' * 960, 48000)), .5)
            self.assertEqual(self.provider.metrics_snapshot()['input_packets'], 1)
            self.assertFalse(delivery.done())
        finally:
            release.set()
            await delivery

    async def test_output_only_preview_paces_zeros_and_reports_microphone_off(self):
        self.provider._input_silence = True
        await self.provider.start()
        await asyncio.sleep(.065)
        packets = [(event, when) for event, when in zip(self.socket.sent, self.socket.send_times) if event['type'] == 'session.input_audio.append']
        self.assertGreaterEqual(len(packets), 2)
        self.assertLessEqual(len(packets), 5)
        self.assertTrue(all(base64.b64decode(event['audio']) == b'\0' * 960 for event, _ in packets))
        self.assertTrue(all(right[1] - left[1] >= .015 for left, right in zip(packets, packets[1:])))
        self.assertFalse(self.events[-1]['microphone'])
        self.assertTrue(self.events[-1]['listening'])
        self.audio.start.assert_awaited_once()

    async def test_transcript_deltas_preserve_text_timestamps_and_do_not_claim_final_turns(self):
        await self.provider.start()
        for role, delta, start, end in [('input', ' hello ', 10, 40), ('output', '  yes', 30, 80), ('input', 'world', 40, 100)]:
            await self.provider._handle_event({'type': f'session.{role}_transcript.delta', 'delta': delta, 'start_ms': start, 'end_ms': end})
        fragments = [event for event in self.events if event['type'] == 'transcript_delta']
        self.assertEqual([event['delta'] for event in fragments], [' hello ', '  yes', 'world'])
        self.assertEqual([event['start_ms'] for event in fragments], [10, 30, 40])
        self.assertFalse(any('final' in event or 'turn_id' in event for event in fragments))
        self.submit.assert_not_called()

    async def test_delegation_is_metadata_only_and_context_ack_is_not_task_completion(self):
        await self.provider.start()
        event = {'type': 'session.delegation.created', 'offset_ms': 101,
                 'delegation': {'id': 'item_private-delegation', 'type': 'delegation', 'target': 'client', 'ignored': 'private metadata'}}
        await self.provider._handle_event(event)
        await self.provider._handle_event(event)
        notices = [event for event in self.events if event['type'] == 'delegation']
        self.assertEqual(notices, [{'type': 'delegation', 'delegation_id': 'item_private-delegation', 'offset_ms': 101}])
        command = await self.provider.append_context('thinking', 'The lookup is still running.', 'item_private-delegation')
        sent = self.socket.sent[-1]
        self.assertEqual(sent['delegation_id'], 'item_private-delegation')
        await self.provider._handle_event({'type': 'session.thinking.appended', 'client_event_id': command, 'start_ms': 101, 'end_ms': 120})
        self.assertEqual(self.events[-1]['type'], 'context_ack')
        self.assertTrue(self.events[-1]['accepted'])
        self.assertNotIn('completed', self.events[-1])
        self.assertEqual(self.provider.metrics_snapshot()['delegations'], 1)
        self.assertNotIn('private', json.dumps(self.provider.metrics_snapshot()))
        self.submit.assert_not_called()

    async def test_context_validation_and_rejection_keep_session_running(self):
        await self.provider.start()
        for args in [('unknown', 'short', None), ('thinking', 'x' * 501, None), ('thinking', 'short', 'unknown')]:
            with self.assertRaises(ProviderError):
                await self.provider.append_context(*args)
        command = await self.provider.append_context('commentary', 'The result is ready.')
        await self.provider._handle_event({'type': 'error', 'error': {'type': 'invalid_request_error', 'code': 'unknown-provider-code',
                                                                     'client_event_id': command, 'message': 'private-fixture-key'}})
        self.assertTrue(self.provider._started)
        self.assertFalse(self.events[-1]['accepted'])
        self.assertNotIn('private-fixture-key', json.dumps(self.events))

    async def test_playback_and_silence_do_not_call_backend_cancel_or_submit(self):
        await self.provider.start()
        await self.provider._handle_event({'type': 'session.output_audio.delta', 'delta': base64.b64encode(b'\x55\x00' * 480).decode()})
        await self.provider.wait_playback()
        self.audio.play.assert_awaited_once()
        speaking = [event for event in self.events if event.get('speaking')]
        self.assertTrue(speaking)
        self.assertTrue(speaking[-1]['listening'])
        self.assertTrue(speaking[-1]['microphone'])
        await self.provider.silence()
        self.submit.assert_not_called()
        self.assertFalse(any('cancel' in event['type'] for event in self.socket.sent))

    async def test_usage_is_cumulative_and_graceful_close_records_final_usage(self):
        await self.provider.start()
        for seconds in [5, 12]:
            await self.provider._handle_event({'type': 'session.usage.updated', 'usage': {'seconds': seconds}})
        self.assertEqual(self.provider.metrics_snapshot()['usage_seconds'], 12)
        await self.provider.stop()
        metrics = self.provider.metrics_snapshot()
        self.assertEqual(metrics['usage_seconds'], 17)
        self.assertTrue(metrics['finalized'])
        self.assertEqual(metrics['closed_reason'], 'close_requested')
        self.assertTrue(self.socket.closed)
        self.assertTrue(any(event['type'] == 'closed' and event['finalized'] for event in self.events))

    async def test_missing_session_closed_is_reported_as_unconfirmed(self):
        self.socket.ack_close = False
        await self.provider.start()
        await self.provider.stop()
        self.assertFalse(self.provider.metrics_snapshot()['finalized'])
        self.assertEqual(self.events[-1]['reason'], 'unconfirmed')
        self.assertTrue(self.socket.closed)

    async def test_remote_expiry_releases_audio_capture_and_reports_disabled(self):
        await self.provider.start()
        await self.provider._handle_event({'type': 'session.closed', 'reason': 'expired', 'usage': {'seconds': 11}})
        self.audio.stop.assert_awaited_once()
        self.assertFalse(self.provider._started)
        self.assertFalse(self.events[-1]['microphone'])
        self.assertEqual(self.events[-2], {
            'type': 'closed', 'finalized': True, 'reason': 'expired', 'usage_seconds': 11,
        })

    async def test_cancelled_start_releases_socket_and_owned_reader_without_capture(self):
        self.socket.ack_start = False
        task = asyncio.create_task(self.provider.start())
        await self.socket.start_sent.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(self.socket.closed)
        self.audio.start.assert_not_called()
        self.assertIsNone(self.provider._reader)

    async def test_transport_failure_stops_capture_without_exposing_diagnostics(self):
        await self.provider.start()
        self.socket.inbox.put_nowait(RuntimeError('private-fixture-key'))
        await self.provider._reader
        self.assertFalse(self.provider._started)
        self.audio.stop.assert_awaited()
        self.assertNotIn('private-fixture-key', json.dumps(self.events))
        self.assertFalse(self.provider.metrics_snapshot()['finalized'])
        self.assertEqual(self.provider.metrics_snapshot()['errors'], 1)

    async def test_audio_buffer_overflow_is_bounded_and_does_not_submit_work(self):
        await self.provider.start()
        self.provider._max_audio_bytes = 2
        await self.provider._handle_event({'type': 'session.output_audio.delta', 'delta': base64.b64encode(b'\x55\x00' * 480).decode()})
        self.assertFalse(self.provider._started)
        self.assertEqual(self.provider.metrics_snapshot()['last_error_code'], 'LIVE_AUDIO_BACKLOG')
        self.assertTrue(self.provider._queue.empty())
        self.assertEqual(self.provider._queued_bytes, 0)
        self.submit.assert_not_called()

    async def test_notice_does_not_misclassify_moderation_as_closed_session(self):
        await self.provider.start()
        await self.provider._handle_event({'type': 'error', 'error': {'type': 'moderation_error', 'message': 'private diagnostic'}})
        self.assertEqual(self.events[-1]['type'], 'notice')
        self.assertTrue(self.provider._started)
        self.assertFalse(self.provider.metrics_snapshot()['finalized'])
        self.assertNotIn('private diagnostic', json.dumps(self.events))


if __name__ == '__main__':
    unittest.main()
