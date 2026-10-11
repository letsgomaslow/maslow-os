#!/usr/bin/env python3
"""Explicit, local free-cloud-ai ledger operations. No scheduling or stale-claim reclamation.

Usage: python manage.py [--ledger PATH] [--repo-root PATH] validate|status|resume
       python manage.py claim TASK --owner NAME --session ID --model MODEL --worktree PATH
Evidence entries are file paths (or objects with a ``path``); relative paths resolve
against --repo-root. Artifact hashes map file paths to SHA-256 digests. All output
is JSON. Claim is the only mutation; coordinators retain control of transitions.
"""
import argparse
from collections import Counter, deque
from datetime import datetime, timezone
import fcntl
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile

STATUSES = {'queued', 'active', 'implementation-complete', 'verified', 'integrated', 'blocked'}
COMPLETE = {'implementation-complete', 'verified', 'integrated'}
OWNED = {'active', 'implementation-complete', 'verified', 'blocked'}
REQUIRED_CLAIM = ('owner', 'session', 'actual_model', 'worktree')


def glob_tokens(pattern):
    """Tokenize path globs; * stays in a segment, ** crosses separators."""
    tokens = []
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if pattern[index:index + 3] == '**/':
            tokens.extend([('dir_start', '**/'), ('dir_body', '**/')])
            index += 3
        elif char == '*':
            recursive = pattern[index:index + 2] == '**'
            tokens.append(('star', '**' if recursive else '*'))
            index += 2 if recursive else 1
        elif char == '[' and ']' in pattern[index + 1:]:
            end = pattern.index(']', index + 1)
            tokens.append(('char', pattern[index:end + 1]))
            index = end + 1
        else:
            tokens.append(('char', char))
            index += 1
    return tokens


def glob_intersects(left, right):
    """Intersect two glob NFAs without depending on existing filesystem contents."""
    a, b = glob_tokens(left), glob_tokens(right)
    # Character-class predicates change only at literal/range boundaries. Include
    # adjacent codepoints to witness intervals and complements without scanning
    # the complete Unicode alphabet.
    boundaries = {ord(c) for c in left + right} | {0, 0x10ffff}
    alphabet = {chr(n + delta) for n in boundaries for delta in (-1, 0, 1) if 0 <= n + delta <= 0x10ffff}
    queue, seen = deque([(0, 0)]), set()
    def accepts(token, char):
        kind, value = token
        if kind in {'dir_start', 'dir_body'}:
            return True
        if kind == 'star':
            return value == '**' or char != '/'
        return char != '/' and fnmatch.fnmatchcase(char, value) if value.startswith('[') or value == '?' else char == value
    while queue:
        i, j = queue.popleft()
        if (i, j) in seen:
            continue
        seen.add((i, j))
        if i == len(a) and j == len(b):
            return True
        if i < len(a) and a[i][0] == 'dir_start':
            queue.extend([(i + 2, j), (i + 1, j)])
        if i < len(a) and a[i][0] == 'star':
            queue.append((i + 1, j))
        if j < len(b) and b[j][0] == 'dir_start':
            queue.extend([(i, j + 2), (i, j + 1)])
        if j < len(b) and b[j][0] == 'star':
            queue.append((i, j + 1))
        if i < len(a) and j < len(b) and a[i][0] != 'dir_start' and b[j][0] != 'dir_start':
            for char in alphabet:
                if accepts(a[i], char) and accepts(b[j], char):
                    def destinations(tokens, position):
                        kind = tokens[position][0]
                        if kind == 'dir_body':
                            return [position, position + 1] if char == '/' else [position]
                        return [position] if kind == 'star' else [position + 1]
                    queue.extend((x, y) for x in destinations(a, i) for y in destinations(b, j))
    return False


def paths_overlap(left, right):
    # A literal directory owns its subtree even if no files exist yet.
    def variants(path):
        path = path.rstrip('/')
        choices = [path]
        if not any(c in path for c in '*?['):
            choices.append(path + '/**')
        if path.endswith('/**'):
            choices.append(path[:-3])
        return choices
    return any(glob_intersects(a, b) for a in variants(left) for b in variants(right))


def ownership_conflicts(tasks):
    owned = [t for t in tasks if isinstance(t.get('status'), str) and t.get('status') in OWNED and t.get('coordinator_only') is not True]
    conflicts = []
    for index, left in enumerate(owned):
        for right in owned[index + 1:]:
            if left.get('repository') != right.get('repository'):
                continue
            for a in left.get('permitted_files', []):
                for b in right.get('permitted_files', []):
                    if paths_overlap(a, b):
                        conflicts.append({'tasks': [left['id'], right['id']], 'repository': left.get('repository'), 'paths': [a, b]})
    return conflicts


def resolve_file(value, root):
    path = Path(value)
    return path if path.is_absolute() else root / path


def evidence_issues(task, root):
    issues = []
    entries = task.get('evidence', [])
    if not isinstance(entries, list):
        issues.append('evidence must be a list of file paths or path objects')
        entries = []
    if isinstance(task.get('status'), str) and task.get('status') in COMPLETE and not entries:
        issues.append('completion requires existing file-backed evidence')
    for entry in entries:
        path = entry.get('path') if isinstance(entry, dict) else entry
        if not isinstance(path, str) or not path.strip() or not resolve_file(path, root).is_file():
            issues.append(f'missing evidence file: {path!r}')
    artifacts = task.get('artifact_hashes', {})
    if not isinstance(artifacts, dict):
        issues.append('artifact_hashes must map paths to SHA-256 digests')
        artifacts = {}
    for path, digest in artifacts.items():
        if not isinstance(path, str) or not path.strip():
            issues.append('artifact path must be a nonempty string')
            continue
        artifact = resolve_file(path, root)
        if not artifact.is_file():
            issues.append(f'missing artifact: {path}')
        elif not isinstance(digest, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', digest):
            issues.append(f'invalid SHA-256: {path}')
        else:
            with artifact.open('rb') as handle:
                actual = hashlib.file_digest(handle, 'sha256').hexdigest()
            if actual.lower() != digest.lower():
                issues.append(f'artifact hash mismatch: {path}')
    return issues


def validate(ledger, root):
    errors, warnings = [], []
    if not isinstance(ledger, dict):
        return {'valid': False, 'errors': ['ledger must be an object'], 'warnings': []}
    tasks = ledger.get('tasks')
    if not isinstance(tasks, list) or any(not isinstance(t, dict) for t in tasks):
        return {'valid': False, 'errors': ['tasks must be a list of objects'], 'warnings': []}
    ids = [t.get('id') for t in tasks]
    if any(not isinstance(i, str) or not re.fullmatch(r'[A-Z0-9]+(?:-[A-Z0-9]+)*', i) for i in ids):
        return {'valid': False, 'errors': ['invalid task ID'], 'warnings': []}
    errors.extend(f'duplicate task ID: {i}' for i, count in Counter(ids).items() if count > 1)
    by_id = {t['id']: t for t in tasks}
    for task in tasks:
        ident = task['id']
        if not isinstance(task.get('status'), str) or task.get('status') not in STATUSES:
            errors.append(f'{ident}: invalid status')
        dependencies = task.get('dependencies', [])
        if not isinstance(dependencies, list) or any(not isinstance(d, str) for d in dependencies):
            errors.append(f'{ident}: dependencies must be strings')
            continue
        for dep in dependencies:
            if dep not in by_id:
                errors.append(f'{ident}: missing dependency {dep}')
        if not isinstance(task.get('repository'), str) or not task['repository'].strip():
            errors.append(f'{ident}: repository required')
        files = task.get('permitted_files', [])
        if not isinstance(files, list) or not files or any(not isinstance(p, str) or not p or PurePosixPath(p).is_absolute() or '..' in PurePosixPath(p).parts for p in files):
            errors.append(f'{ident}: permitted_files must be nonempty repository-relative paths')
        if not isinstance(task.get('attempt', 0), int) or isinstance(task.get('attempt', 0), bool) or task.get('attempt', 0) < 0:
            errors.append(f'{ident}: attempt must be a nonnegative integer')
        if task.get('status') == 'queued' and any(task.get(field) for field in REQUIRED_CLAIM):
            errors.append(f'{ident}: queued task has unreconciled claim metadata')
        if isinstance(task.get('status'), str) and task.get('status') in OWNED:
            for field in REQUIRED_CLAIM:
                if not isinstance(task.get(field), str) or not task[field].strip():
                    errors.append(f'{ident}: claim missing {field}')
            warnings.append(f'{ident}: confirm worker/session liveness and reconcile worktree, report, commits and artifacts before dispatch')
        tests = task.get('tests', [])
        if not isinstance(tests, list):
            errors.append(f'{ident}: tests must be a list of check/result objects')
        else:
            for test in tests:
                if not isinstance(test, dict) or not isinstance(test.get('check'), str) or not test['check'].strip() or test.get('result') not in ('pass', 'fail', 'skip', 'error', 'unavailable'):
                    errors.append(f'{ident}: invalid test check/result')
                elif isinstance(task.get('status'), str) and task.get('status') in COMPLETE and test['result'] in ('fail', 'error'):
                    errors.append(f'{ident}: completed task has failing test: {test["check"]}')
        errors.extend(f'{ident}: {issue}' for issue in evidence_issues(task, root))
    visiting, visited = set(), set()
    def visit(ident):
        if ident in visiting:
            errors.append(f'dependency cycle involving {ident}')
            return
        if ident in visited:
            return
        visiting.add(ident)
        deps = by_id[ident].get('dependencies', [])
        for dep in deps if isinstance(deps, list) else []:
            if isinstance(dep, str) and dep in by_id:
                visit(dep)
        visiting.remove(ident)
        visited.add(ident)
    for ident in by_id:
        visit(ident)
    # Skip malformed path collections; their diagnostics above already fail closed.
    if not any('permitted_files' in e for e in errors):
        errors.extend(f'ownership conflict: {c}' for c in ownership_conflicts(tasks))
    return {'valid': not errors, 'errors': errors, 'warnings': warnings}


def ready_tasks(ledger):
    by_id = {t['id']: t for t in ledger['tasks']}
    return [t for t in ledger['tasks'] if t.get('status') == 'queued' and all(by_id.get(d, {}).get('status') == 'integrated' for d in t.get('dependencies', []))]


def status(ledger, root):
    validation = validate(ledger, root)
    if not isinstance(ledger, dict) or not isinstance(ledger.get('tasks'), list):
        return {'ready': [], 'validation': validation}
    return {'program': ledger.get('program'), 'phase': ledger.get('current_phase'), 'counts': dict(Counter(str(t.get('status')) for t in ledger.get('tasks', []) if isinstance(t, dict))), 'ready': [t['id'] for t in ready_tasks(ledger)] if validation['valid'] else [], 'validation': validation}


def resume(ledger, root):
    result = status(ledger, root)
    if not isinstance(ledger, dict) or not isinstance(ledger.get('tasks'), list):
        result['reconciliation'] = []
        result['next_ready_tasks'] = []
        return result
    result['latest_handoff'] = ledger.get('latest_handoff')
    result['reconciliation'] = []
    for task in ledger.get('tasks', []):
        if not isinstance(task, dict) or not isinstance(task.get('status'), str) or task.get('status') not in OWNED:
            continue
        worktree = task.get('worktree')
        reconciliation = {key: task.get(key) for key in (
            'id', 'status', 'owner', 'session', 'worker', 'actual_model', 'worktree',
            'branch', 'base_revision', 'last_checkpoint', 'implementation_commits',
            'integration_commits', 'next_action')}
        reconciliation.update(
            worktree_exists=bool(isinstance(worktree, str) and worktree and resolve_file(worktree, root).is_dir()),
            evidence_issues=evidence_issues(task, root),
            required_action='Confirm or interrupt live worker; reconcile Git/worktree, task report and artifacts. Never reclaim based on timestamp.')
        result['reconciliation'].append(reconciliation)
    result['next_ready_tasks'] = [t for t in ready_tasks(ledger)] if result['validation']['valid'] else []
    return result


def claim(ledger_path, root, ident, owner, session, model, worktree, worker=None, branch=None, base_revision=None):
    # The lock is a stable sidecar: locking the replaced ledger inode is unsafe.
    with Path(str(ledger_path) + '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger = json.loads(ledger_path.read_text())
        validation = validate(ledger, root)
        if not validation['valid']:
            raise ValueError('invalid ledger: ' + '; '.join(validation['errors']))
        for name, value in [('owner', owner), ('session', session), ('actual_model', model), ('worktree', worktree)]:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'{name} is required')
        if not resolve_file(worktree, root).is_dir():
            raise ValueError('worktree does not exist')
        task = next((t for t in ledger['tasks'] if t['id'] == ident), None)
        if task is None:
            raise ValueError(f'unknown task: {ident}')
        if task['status'] != 'queued':
            raise ValueError(f'task is occupied or completed: {ident} ({task["status"]})')
        if task not in ready_tasks(ledger):
            raise ValueError(f'task dependencies are not integrated: {ident}')
        task.update(status='active', owner=owner, session=session, actual_model=model, worktree=str(resolve_file(worktree, root).resolve()), worker=worker, branch=branch, base_revision=base_revision, attempt=task.get('attempt', 0) + 1, last_checkpoint=datetime.now(timezone.utc).isoformat())
        validation = validate(ledger, root)
        if not validation['valid']:
            raise ValueError('claim rejected: ' + '; '.join(validation['errors']))
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', dir=ledger_path.parent, prefix='.' + ledger_path.name + '.', delete=False) as handle:
                temp_path = Path(handle.name)
                os.chmod(temp_path, ledger_path.stat().st_mode & 0o777)
                json.dump(ledger, handle, indent=2)
                handle.write('\n')
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, ledger_path)
            directory = os.open(ledger_path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
        return {'claimed': task}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, default=Path(__file__).with_name('tasks.json'))
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[3])
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('validate', 'status', 'resume'):
        commands.add_parser(command)
    claimant = commands.add_parser('claim')
    claimant.add_argument('task')
    for option in ('owner', 'session', 'model', 'worktree'):
        claimant.add_argument('--' + option, required=True)
    for option in ('worker', 'branch', 'base-revision'):
        claimant.add_argument('--' + option)
    args = parser.parse_args()
    try:
        if args.command == 'claim':
            result = claim(args.ledger.resolve(), args.repo_root.resolve(), args.task, args.owner, args.session, args.model, args.worktree, args.worker, args.branch, args.base_revision)
        else:
            ledger = json.loads(args.ledger.read_text())
            result = globals()[args.command](ledger, args.repo_root.resolve())
        print(json.dumps(result, indent=2))
        valid = result.get('valid', result.get('validation', {}).get('valid', True))
        return 0 if valid else 1
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({'error': str(error)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
