"""Async adapter contract проверен без engine imports или мрежа."""
import asyncio
import copy
import threading
import unittest
from unittest.mock import Mock, patch

from monitoring.proxmox_adapter import adapt_snapshot, proxmox_probe


def sample():
    return {'ok': True, 'status': 'OK', 'error_code': None, 'node': 'lab-node',
            'resource': 'snapshot', 'timestamp_utc': '2026-11-04T00:00:00Z',
            'source': 'proxmox-ve-api', 'capabilities': {'network_metrics': False},
            'data': {'resources': {'api_version': {'version': '8.4'},
                                  'node_status': {'cpu': 0}, 'storage': [],
                                  'qemu': [], 'lxc': [], 'backup_tasks': {'tasks': []}},
                     'errors': {}, 'resource_capabilities': {'node_status': {'cpu': True, 'memory': False}}}}


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        network = patch('socket.socket.connect', side_effect=AssertionError('Offline test opened a socket'))
        network.start()
        self.addCleanup(network.stop)

    async def test_complete_collection_becomes_up_and_preserves_sample(self):
        raw = sample()
        original = copy.deepcopy(raw)
        client = Mock()
        client.snapshot.return_value = raw
        result = await proxmox_probe(client, 'lab-node')
        self.assertIs(result['ok'], True)
        self.assertEqual(result['status'], 'UP')
        self.assertIsNone(result['error_code'])
        self.assertIs(result['sample'], raw)
        self.assertEqual(raw, original)
        client.snapshot.assert_called_once_with('lab-node')
        self.assertFalse(result['sample']['data']['resource_capabilities']['node_status']['memory'])

    async def test_partial_collection_is_unknown_not_down(self):
        raw = sample()
        raw['status'] = 'DEGRADED'
        raw['data']['resources']['storage'] = None
        raw['data']['errors']['storage'] = 'PERMISSION_DENIED'
        result = adapt_snapshot(raw)
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertFalse(result['ok'])
        self.assertEqual(result['error_code'], 'UNAVAILABLE')
        self.assertIs(result['sample'], raw)

    async def test_each_failure_category_stays_unknown(self):
        for code in ('API_UNREACHABLE', 'TLS_ERROR', 'AUTH_FAILED',
                     'PERMISSION_DENIED', 'RESOURCE_NOT_FOUND', 'MALFORMED_RESPONSE', 'UNAVAILABLE'):
            raw = sample()
            raw.update(ok=False, status='UNAVAILABLE', error_code=code, data=None)
            result = await proxmox_probe(Mock(snapshot=Mock(return_value=raw)), 'lab-node')
            self.assertEqual(result['status'], 'UNKNOWN')
            self.assertEqual(result['error_code'], code)
            self.assertIs(result['sample'], raw)

    async def test_missing_credentials_with_real_client_never_performs_io(self):
        import os
        from monitoring.proxmox_api import ProxmoxReadOnlyClient
        with patch.dict(os.environ, {'KSSH_PROXMOX_TOKEN_ID': '', 'KSSH_PROXMOX_TOKEN_SECRET': ''}):
            client = ProxmoxReadOnlyClient('https://lab.example.invalid:8006',
                                          allowed_hosts=['lab.example.invalid'])
            with patch.object(client._opener, 'open') as opened:
                result = await proxmox_probe(client, 'lab-node')
            opened.assert_not_called()
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertEqual(result['error_code'], 'UNAVAILABLE')
        self.assertIsNone(result['sample']['data'])
        self.assertEqual(len(result['sample']['resource_errors']), 6)
        self.assertTrue(all(code == 'UNAVAILABLE' for code in result['sample']['resource_errors'].values()))

    async def test_malformed_sample_cannot_signal_up(self):
        for raw in (None, [], {}, {'ok': 'yes', 'status': 'OK', 'error_code': None, 'data': {}},
                    {'ok': True, 'status': 'UP', 'error_code': None, 'data': {}}):
            result = adapt_snapshot(raw)
            self.assertEqual(result['status'], 'UNKNOWN')
            self.assertEqual(result['error_code'], 'MALFORMED_RESPONSE')
        raw = sample()
        raw['data']['resources'].pop('qemu')
        self.assertEqual(adapt_snapshot(raw)['status'], 'UNKNOWN')

    async def test_invalid_node_rejected_before_worker_runs(self):
        client = Mock()
        with self.assertRaises(ValueError):
            await proxmox_probe(client, '../node')
        client.snapshot.assert_not_called()

    async def test_unexpected_worker_failure_does_not_leak_details(self):
        client = Mock(snapshot=Mock(side_effect=RuntimeError('private credentials')))
        result = await proxmox_probe(client, 'lab-node')
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertEqual(result['error_code'], 'UNAVAILABLE')
        self.assertNotIn('private credentials', str(result))

    async def test_worker_does_not_block_event_loop(self):
        loop_thread = threading.get_ident()
        threads = []
        def collect(node):
            threads.append(threading.get_ident())
            return sample()
        result = await proxmox_probe(Mock(snapshot=collect), 'lab-node')
        self.assertEqual(result['status'], 'UP')
        self.assertNotEqual(threads, [loop_thread])

    async def test_cancellation_propagates_but_worker_must_finish(self):
        started, release, finished = threading.Event(), threading.Event(), threading.Event()
        def collect(node):
            started.set()
            try:
                if not release.wait(5):
                    raise AssertionError('Test worker not released')
                return sample()
            finally:
                finished.set()
        task = asyncio.create_task(proxmox_probe(Mock(snapshot=collect), 'lab-node'))
        try:
            self.assertTrue(await asyncio.to_thread(started.wait, 2))
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertFalse(finished.is_set())
        finally:
            release.set()
            self.assertTrue(await asyncio.to_thread(finished.wait, 2))


if __name__ == '__main__':
    unittest.main()
