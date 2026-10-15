"""Synthetic-ledger regressions. Never write the real program ledger."""
import copy
import hashlib
import json
import multiprocessing
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import manage


def task(ident, **overrides):
    result = dict(id=ident, repository='runtime', status='queued', dependencies=[], permitted_files=[f'src/{ident}.py'], evidence=[], artifact_hashes={}, attempt=0)
    result.update(overrides)
    return result


def claim_worker(path, root, ident, gate, outcomes):
    gate.wait()
    try:
        manage.claim(Path(path), Path(root), ident, 'worker', 'session', 'model', root)
        outcomes.put('claimed')
    except ValueError:
        outcomes.put('rejected')


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'tasks.json'
        self.ledger = {'program': 'test', 'tasks': [task('A'), task('B', dependencies=['A'])]}

    def write(self):
        self.path.write_text(json.dumps(self.ledger))

    def active(self, ident='A', **overrides):
        return task(ident, status='active', owner='owner', session='session', actual_model='model', worktree=str(self.root), **overrides)

    def complete(self, ident='A'):
        evidence = self.root / 'evidence.txt'
        evidence.write_text('checked output')
        return task(ident, status='integrated', evidence=['evidence.txt'])

    def test_graph_errors_and_ready_dependencies(self):
        self.assertTrue(manage.validate(self.ledger, self.root)['valid'])
        self.assertEqual([t['id'] for t in manage.ready_tasks(self.ledger)], ['A'])
        cases = [([task('A'), task('A')], 'duplicate'), ([task('A', dependencies=['MISSING'])], 'missing dependency'), ([task('A', dependencies=['B']), task('B', dependencies=['A'])], 'cycle')]
        for tasks, message in cases:
            with self.subTest(message=message):
                result = manage.validate({'tasks': tasks}, self.root)
                self.assertFalse(result['valid'])
                self.assertIn(message, ' '.join(result['errors']))
        self.ledger['tasks'][0] = self.complete()
        self.assertEqual([t['id'] for t in manage.ready_tasks(self.ledger)], ['B'])
        self.ledger['tasks'][0]['status'] = 'verified'
        self.assertEqual(manage.ready_tasks(self.ledger), [])

    def test_glob_hierarchy_and_repository_ownership(self):
        for left, right in [('src', 'src/deep/file.py'), ('src/**', 'src/deep/file.py'), ('src/*.py', 'src/a?.py'), ('src/[a-c].py', 'src/b.py'), ('src/**/file.py', 'src/file.py'), ('src/**/file.py', 'src/deep/file.py'), ('src/**/file.py', 'src/deep/more/file.py')]:
            with self.subTest(left=left, right=right):
                self.assertTrue(manage.paths_overlap(left, right))
                self.assertTrue(manage.paths_overlap(right, left))
        for left, right in [('src/*.py', 'src/deep/file.py'), ('src/a*.py', 'src/b*.py'), ('src/[a-c].py', 'src/[d-f].py'), ('src', 'src-other/file.py')]:
            self.assertFalse(manage.paths_overlap(left, right), (left, right))
        self.assertFalse(manage.glob_intersects('src/**/file.py', 'src/deep/notfile.py'))
        tasks = [self.active('A', permitted_files=['src/**']), self.active('B', permitted_files=['src/a.py'])]
        self.assertTrue(manage.ownership_conflicts(tasks))
        tasks[1]['repository'] = 'packages'
        self.assertFalse(manage.ownership_conflicts(tasks))
        tasks[1]['repository'] = 'runtime'
        tasks[0]['coordinator_only'] = True
        self.assertFalse(manage.ownership_conflicts(tasks))

    def test_completion_requires_existing_evidence_and_matching_artifacts(self):
        for state in manage.COMPLETE:
            result = manage.validate({'tasks': [task('A', status=state)]}, self.root)
            self.assertIn('existing file-backed evidence', ' '.join(result['errors']))
        completed = self.complete()
        completed['evidence'] = ['missing.txt']
        self.assertIn('missing evidence file', ' '.join(manage.validate({'tasks': [completed]}, self.root)['errors']))
        completed['evidence'] = [{'path': 'evidence.txt'}]
        completed['artifact_hashes'] = {'evidence.txt': hashlib.sha256(b'checked output').hexdigest()}
        self.assertTrue(manage.validate({'tasks': [completed]}, self.root)['valid'])
        (self.root / 'evidence.txt').write_text('changed')
        self.assertIn('hash mismatch', ' '.join(manage.validate({'tasks': [completed]}, self.root)['errors']))
        (self.root / 'evidence.txt').unlink()
        self.assertIn('missing artifact', ' '.join(manage.validate({'tasks': [completed]}, self.root)['errors']))

    def test_interrupted_resume_never_reclaims_old_claim(self):
        active = self.active(last_checkpoint='1990-01-01T00:00:00Z')
        active['worktree'] = str(self.root / 'disappeared')
        active['artifact_hashes'] = {'missing.bin': 'a' * 64}
        self.ledger['tasks'][0] = active
        before = copy.deepcopy(self.ledger)
        packet = manage.resume(self.ledger, self.root)
        self.assertEqual(self.ledger, before)
        self.assertFalse(packet['reconciliation'][0]['worktree_exists'])
        self.assertIn('missing artifact', packet['reconciliation'][0]['evidence_issues'][0])
        self.assertIn('Confirm or interrupt', packet['reconciliation'][0]['required_action'])
        self.assertEqual(packet['ready'], [])

    def test_claim_required_metadata_and_rejections_leave_bytes_unchanged(self):
        self.write()
        original = self.path.read_bytes()
        for ident, owner, session, model, worktree in [('UNKNOWN', 'o', 's', 'm', str(self.root)), ('B', 'o', 's', 'm', str(self.root)), ('A', '', 's', 'm', str(self.root)), ('A', 'o', '', 'm', str(self.root)), ('A', 'o', 's', '', str(self.root)), ('A', 'o', 's', 'm', ''), ('A', 'o', 's', 'm', str(self.root / 'missing'))]:
            with self.subTest(ident=ident, owner=owner):
                with self.assertRaises(ValueError):
                    manage.claim(self.path, self.root, ident, owner, session, model, worktree)
                self.assertEqual(self.path.read_bytes(), original)
        claimed = manage.claim(self.path, self.root, 'A', 'o', 's', 'm', str(self.root))['claimed']
        self.assertEqual(claimed['attempt'], 1)
        self.assertEqual(claimed['status'], 'active')
        original = self.path.read_bytes()
        with self.assertRaises(ValueError):
            manage.claim(self.path, self.root, 'A', 'o', 's', 'm', str(self.root))
        self.assertEqual(self.path.read_bytes(), original)

    def test_completed_and_invalid_ledgers_reject_claims(self):
        self.ledger['tasks'][0] = self.complete()
        self.write()
        with self.assertRaisesRegex(ValueError, 'occupied or completed'):
            manage.claim(self.path, self.root, 'A', 'o', 's', 'm', str(self.root))
        self.ledger['tasks'].append(task('A'))
        self.write()
        with self.assertRaisesRegex(ValueError, 'invalid ledger'):
            manage.claim(self.path, self.root, 'B', 'o', 's', 'm', str(self.root))

    def test_conflicting_claim_is_rejected_before_write(self):
        self.ledger['tasks'] = [self.active(permitted_files=['src/**']), task('B', permitted_files=['src/file.py'])]
        self.write()
        original = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'ownership conflict'):
            manage.claim(self.path, self.root, 'B', 'o', 's', 'm', str(self.root))
        self.assertEqual(self.path.read_bytes(), original)

    def test_process_race_serializes_same_and_disjoint_claims(self):
        for identifiers, expected in [(['A', 'A'], ['claimed', 'rejected']), (['A', 'B'], ['claimed', 'claimed'])]:
            with self.subTest(identifiers=identifiers):
                self.ledger['tasks'] = [task('A'), task('B')]
                self.write()
                context = multiprocessing.get_context('fork')
                gate, outcomes = context.Event(), context.Queue()
                processes = [context.Process(target=claim_worker, args=(str(self.path), str(self.root), ident, gate, outcomes)) for ident in identifiers]
                for process in processes:
                    process.start()
                gate.set()
                for process in processes:
                    process.join(10)
                    self.assertEqual(process.exitcode, 0)
                self.assertEqual(sorted(outcomes.get(timeout=2) for _ in processes), expected)
                ledger = json.loads(self.path.read_text())
                self.assertEqual(sum(t['status'] == 'active' for t in ledger['tasks']), expected.count('claimed'))
                outcomes.close()

    def test_completed_failing_tests_are_not_valid(self):
        completed = self.complete()
        completed['tests'] = [{'check': 'acceptance', 'result': 'fail'}]
        result = manage.validate({'tasks': [completed]}, self.root)
        self.assertFalse(result['valid'])
        self.assertIn('failing test', ' '.join(result['errors']))
        completed['tests'][0]['result'] = 'pass'
        self.assertTrue(manage.validate({'tasks': [completed]}, self.root)['valid'])

    def test_malformed_fields_fail_closed(self):
        for field, value in [('evidence', None), ('evidence', 'description'), ('artifact_hashes', []), ('dependencies', None), ('dependencies', [{}]), ('status', []), ('permitted_files', None), ('attempt', 'one'), ('tests', None), ('tests', [{'result': []}])]:
            with self.subTest(field=field, value=value):
                malformed = task('A')
                malformed[field] = value
                ledger = {'tasks': [malformed]}
                self.assertFalse(manage.validate(ledger, self.root)['valid'])
                self.assertEqual(manage.status(ledger, self.root)['ready'], [])
                self.assertEqual(manage.resume(ledger, self.root)['next_ready_tasks'], [])
        for ledger in [[], {'tasks': None}, {'tasks': [None]}]:
            self.assertFalse(manage.validate(ledger, self.root)['valid'])
            self.assertEqual(manage.resume(ledger, self.root)['next_ready_tasks'], [])
        self.ledger['tasks'][0]['owner'] = 'interrupted-owner'
        self.write()
        with self.assertRaisesRegex(ValueError, 'unreconciled claim'):
            manage.claim(self.path, self.root, 'A', 'o', 's', 'm', str(self.root))

    def test_cli_json_and_error_exit(self):
        self.write()
        command = [sys.executable, str(Path(manage.__file__)), '--ledger', str(self.path), '--repo-root', str(self.root)]
        for action in ['validate', 'status', 'resume']:
            result = subprocess.run(command + [action], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIsInstance(json.loads(result.stdout), dict)
        self.path.write_text('{invalid')
        result = subprocess.run(command + ['validate'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('error', json.loads(result.stdout))


if __name__ == '__main__':
    unittest.main()
