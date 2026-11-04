"""Самостоятелен async contract; не импортира engine, state или notifier."""
import asyncio

from monitoring.proxmox_api import validated_node


def adapt_snapshot(sample):
    """Запазва sample и превежда collection статуса към UP/UNKNOWN."""
    valid = (isinstance(sample, dict) and type(sample.get('ok')) is bool
             and sample.get('status') in ('OK', 'DEGRADED', 'UNAVAILABLE')
             and 'error_code' in sample and 'data' in sample)
    data = sample.get('data') if valid else None
    resources = data.get('resources') if isinstance(data, dict) else None
    complete = (valid and sample['ok'] is True and sample['status'] == 'OK'
                and sample['error_code'] is None and isinstance(resources, dict)
                and all(resources.get(key) is not None for key in (
                    'api_version', 'node_status', 'storage', 'qemu', 'lxc', 'backup_tasks'))
                and data.get('errors') == {})
    error = None if complete else 'UNAVAILABLE'
    if valid and not complete:
        candidate = sample['error_code']
        if candidate in ('API_UNREACHABLE', 'TLS_ERROR', 'AUTH_FAILED',
                         'PERMISSION_DENIED', 'RESOURCE_NOT_FOUND',
                         'MALFORMED_RESPONSE', 'UNAVAILABLE'):
            error = candidate
    elif not valid:
        error = 'MALFORMED_RESPONSE'
    return {
        'ok': complete,
        'status': 'UP' if complete else 'UNKNOWN',
        'error_code': error,
        'detail': 'API collection complete' if complete else 'API collection incomplete',
        'sample': sample,
    }


async def proxmox_probe(client, node):
    """Client е доверен операторски обект; cancellation не спира worker thread."""
    validated_node(node)
    try:
        sample = await asyncio.to_thread(client.snapshot, node)
    except Exception:
        # Не разкриваме raw exception text; CancelledError се разпространява.
        return {'ok': False, 'status': 'UNKNOWN', 'error_code': 'UNAVAILABLE',
                'detail': 'API collection incomplete', 'sample': None}
    return adapt_snapshot(sample)
