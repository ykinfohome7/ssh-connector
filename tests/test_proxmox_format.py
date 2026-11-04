"""Offline regression проверки на чистите нормализатори."""
import unittest

from monitoring.proxmox_format import normalize, number


class FormatTests(unittest.TestCase):
    def test_numbers_reject_nonfinite_booleans_and_oversized_integers(self):
        for value in (True, False, -1, '0', float('nan'), float('inf'), 10**400):
            with self.subTest(kind=type(value).__name__):
                self.assertFalse(number(value))
                with self.assertRaises(ValueError):
                    normalize('node_status', {'cpu': value})
        for value in (0, 0.0, 10**30):
            self.assertTrue(number(value))

    def test_storage_flags_are_boolean_not_arbitrary_metrics(self):
        for value in (True, False, 0, 1):
            data, _ = normalize('storage', [{'storage': 'lab', 'active': value, 'enabled': value}])
            self.assertEqual(data[0]['active'], int(value))
        for value in (2, -1, 0.5, 1.0, '1'):
            for key in ('active', 'enabled'):
                with self.subTest(value=value, key=key), self.assertRaises(ValueError):
                    normalize('storage', [{'storage': 'lab', key: value}])

    def test_storage_capacity_cannot_be_contradictory(self):
        for fields in ({'used': 101, 'total': 100}, {'avail': 101, 'total': 100},
                       {'used': 1, 'total': 0}, {'used': 0.5, 'total': 100}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                normalize('storage', [{'storage': 'lab', **fields}])

    def test_zero_and_missing_storage_capacity_remain_distinct(self):
        rows, _ = normalize('storage', [
            {'storage': 'zero', 'used': 0, 'total': 100, 'avail': 100},
            {'storage': 'inactive', 'active': False, 'used': 0, 'total': 0},
            {'storage': 'missing', 'active': True},
        ])
        self.assertEqual(rows[0]['usage_ratio'], 0)
        self.assertIs(rows[0]['warning'], False)
        self.assertNotIn('usage_ratio', rows[1])
        self.assertFalse(rows[1]['capabilities']['capacity'])
        self.assertTrue(rows[1]['warning'])
        self.assertIsNone(rows[2]['warning'])

    def test_backup_outcomes_are_conservative(self):
        statuses = ['OK', 'ERROR', 'ERROR: disk full', 'TASK ERROR: disk full',
                    'WARNINGS: 2', '', 'unknown', 'unexpected status', 'disk full', 'RUNNING']
        data, caps = normalize('backup_tasks', [
            {'type': 'vzdump', 'status': status, 'endtime': 20} for status in statuses])
        outcomes = {task['status']: task['outcome'] for task in data['tasks']}
        self.assertEqual(outcomes['OK'], 'completed_success')
        self.assertEqual(outcomes['WARNINGS: 2'], 'completed_warning')
        self.assertEqual(len(data['failures']), 3)
        for status in ('', 'unknown', 'unexpected status', 'disk full', 'RUNNING'):
            self.assertEqual(outcomes[status], 'unknown')
        self.assertFalse(caps['history_complete'])
        self.assertFalse(caps['backup_recency_assurance'])
        self.assertFalse(caps['pbs_health'])

    def test_running_and_missing_backup_outcome(self):
        data, _ = normalize('backup_tasks', [
            {'type': 'vzdump', 'status': 'RUNNING'}, {'type': 'vzdump'},
            {'type': 'vzdump', 'endtime': 10}, {'type': 'vzdump', 'status': 'ERROR'}])
        self.assertEqual([x['outcome'] for x in data['tasks']],
                         ['in_progress', 'unknown', 'unknown', 'unknown'])
        self.assertFalse(any(x['outcome_available'] for x in data['tasks']))
        self.assertEqual(data['failures'], [])

    def test_invalid_task_times_are_not_measurements(self):
        for fields in ({'endtime': 1.5}, {'endtime': True}, {'starttime': 20, 'endtime': 10}):
            with self.assertRaises(ValueError):
                normalize('backup_tasks', [{'type': 'vzdump', **fields}])

    def test_job_enabled_has_explicit_boolean_semantics(self):
        for value in (True, False, 0, 1):
            data, _ = normalize('backup_jobs', [{'id': 'lab-job', 'enabled': value}])
            self.assertEqual(data[0]['enabled'], int(value))
        for value in (1.0, 2, 'yes'):
            with self.assertRaises(ValueError):
                normalize('backup_jobs', [{'id': 'lab-job', 'enabled': value}])


if __name__ == '__main__':
    unittest.main()
