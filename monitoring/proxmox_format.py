"""Валидация на PVE отговори без I/O и без измислени нули."""
import math
import re


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def fields(item, strings=(), numbers=()):
    if not isinstance(item, dict):
        raise ValueError('Expected object')
    out = {}
    for key in strings:
        if key in item and item[key] is not None:
            value = item[key]
            if not isinstance(value, str) or len(value) > 512 or any(ord(c) < 32 for c in value):
                raise ValueError('Invalid string')
            out[key] = value
    for key in numbers:
        if key in item and item[key] is not None:
            if not number(item[key]):
                raise ValueError('Invalid numeric metric')
            out[key] = item[key]
    return out


def normalize(resource, value):
    if resource == 'api_version':
        data = fields(value, ('version', 'release', 'repoid'))
        if not data.get('version'):
            raise ValueError('Missing version')
        return data, {'api_version': True}
    if resource == 'node_status':
        data = fields(value, ('status', 'kversion', 'pveversion'), ('uptime', 'cpu', 'wait', 'netin', 'netout'))
        for key in ('memory', 'swap'):
            if value.get(key) is not None:
                data[key] = fields(value[key], numbers=('used', 'total', 'free'))
        return data, {key: bool(data.get(key)) if key in ('memory', 'swap') else key in data
                      for key in ('cpu', 'uptime', 'memory', 'swap', 'netin', 'netout')} | {'network_metrics': 'netin' in data or 'netout' in data}
    if resource == 'guest_status':
        data = fields(value, ('status',), ('uptime', 'cpu', 'mem', 'maxmem', 'netin', 'netout', 'diskread', 'diskwrite'))
        if data.get('status') not in (None, 'running', 'stopped'):
            raise ValueError('Invalid guest status')
        flags = {key: key in data for key in ('status', 'uptime', 'cpu', 'mem', 'maxmem', 'netin', 'netout', 'diskread', 'diskwrite')}
        flags['network_metrics'] = 'netin' in data or 'netout' in data
        return data, flags
    if not isinstance(value, list):
        raise ValueError('Expected list')
    if resource == 'nodes':
        out = []
        for item in value:
            row = fields(item, ('node', 'status'))
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,62}', row.get('node', '')):
                raise ValueError('Invalid node')
            if row.get('status') not in (None, 'online', 'offline', 'unknown'):
                raise ValueError('Invalid node status')
            out.append(row)
        return out, {'node_inventory': True}
    if resource == 'storage':
        out = []
        for item in value:
            row = fields(item, ('storage', 'type'), ('used', 'total', 'avail', 'active', 'enabled'))
            if not row.get('storage'):
                raise ValueError('Missing storage identity')
            used, total = row.get('used'), row.get('total')
            capacity = used is not None and total is not None and total > 0
            row['warning'] = used / total >= .9 if capacity else None
            if capacity:
                row['usage_ratio'] = used / total
            if row.get('active') == 0:
                row['warning'] = True
            row['capabilities'] = {'capacity': capacity}
            out.append(row)
        return out, {'capacity': any(x['capabilities']['capacity'] for x in out)}
    if resource in ('qemu', 'lxc'):
        out = []
        for entry in value:
            row = fields(entry, ('name', 'status'), ('vmid', 'uptime', 'cpu', 'mem', 'maxmem', 'netin', 'netout'))
            if type(row.get('vmid')) is not int or not 100 <= row['vmid'] <= 999999999:
                raise ValueError('Invalid VMID')
            if row.get('status') not in (None, 'running', 'stopped'):
                raise ValueError('Invalid guest status')
            row['capabilities'] = {key: key in row for key in ('status', 'cpu', 'uptime', 'mem', 'maxmem', 'netin', 'netout')}
            out.append(row)
        return out, {'inventory': True, 'network_metrics': any('netin' in x or 'netout' in x for x in out)}
    if resource == 'backup_jobs':
        jobs = []
        for item in value:
            row = fields(item, ('id', 'node', 'storage', 'schedule'), ('enabled',))
            if not row.get('id'):
                raise ValueError('Missing job identity')
            if 'enabled' in row and row['enabled'] not in (0, 1):
                raise ValueError('Invalid enabled flag')
            row['capabilities'] = {key: key in row for key in ('node', 'storage', 'schedule', 'enabled')}
            jobs.append(row)
        return jobs, {'backup_jobs': True, 'backup_recency_assurance': False, 'pbs_health': False}
    if resource == 'backup_tasks':
        tasks, failures = [], []
        for item in value:
            row = fields(item, ('upid', 'id', 'type', 'status'), ('starttime', 'endtime'))
            if row.get('type') != 'vzdump':
                continue
            row['outcome_available'] = 'endtime' in row and 'status' in row
            if row['outcome_available'] and row['status'] != 'OK':
                failures.append(row)
            tasks.append(row)
        return {'tasks': tasks, 'failures': failures, 'total_returned': len(tasks)}, {
            'pve_backup_task_history': True, 'history_may_be_truncated': True,
            'history_complete': False, 'backup_recency_assurance': False, 'pbs_health': False}
    raise ValueError('Unknown resource')
