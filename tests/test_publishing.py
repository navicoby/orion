"""Offline regression tests; publishing targets temporary local Git repositories."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/save_and_push.py'
spec = importlib.util.spec_from_file_location('publisher', SCRIPT)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


def run(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class PublishingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.remote = self.base / 'remote.git'
        self.root = self.base / 'vault'
        run('git', 'init', '--bare', '--initial-branch=main', str(self.remote))
        run('git', 'clone', str(self.remote), str(self.root))
        run('git', 'config', 'user.name', 'Test Author', cwd=self.root)
        run('git', 'config', 'user.email', 'test@users.noreply.github.com', cwd=self.root)
        (self.root / 'README.md').write_text('Existing public material\n')
        run('git', 'add', 'README.md', cwd=self.root)
        run('git', 'commit', '-m', 'Initial test fixture', cwd=self.root)
        run('git', 'push', '-u', 'origin', 'main', cwd=self.root)
        self.before = self.head()

    def head(self):
        return run('git', '--git-dir', str(self.remote), 'rev-parse', 'main')

    def report(self, content='Public research notes.\n'):
        return publisher.save_report(self.root, content)

    def test_default_only_saves_locally(self):
        run(sys.executable, str(SCRIPT), '--vault-path', str(self.root), '--content', 'Public notes')
        self.assertEqual(self.before, self.head())
        self.assertEqual(self.before, run('git', 'rev-parse', 'HEAD', cwd=self.root))
        self.assertEqual(1, len(list((self.root / 'Research').glob('*.md'))))

    def test_duplicate_does_not_overwrite(self):
        first = self.report('First')
        second = self.report('Second')
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_text(), 'First')

    def test_rejects_traversal(self):
        with self.assertRaises(ValueError):
            publisher.save_report(self.root, 'Text', '../outside')
        self.assertFalse((self.base / 'outside').exists())

    def test_rejects_symlink_directory(self):
        (self.root / 'Research').symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.report()

    def test_rejects_symlink_file_cli(self):
        (self.root / 'Research').mkdir()
        (self.root / 'Research/link.md').symlink_to(self.root / 'README.md')
        result = subprocess.run([sys.executable, str(SCRIPT), '--vault-path', str(self.root), '--report', 'Research/link.md', '--publish'], capture_output=True)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(self.before, self.head())

    def test_rejects_staged_private_notes(self):
        report = self.report()
        (self.root / 'private.txt').write_text('Private note')
        run('git', 'add', 'private.txt', cwd=self.root)
        with self.assertRaises(RuntimeError):
            publisher.publish_report(self.root, report)
        self.assertEqual(self.before, self.head())
        self.assertEqual('private.txt', run('git', 'diff', '--cached', '--name-only', cwd=self.root))

    def test_rejects_existing_unpushed_commit(self):
        report = self.report()
        (self.root / 'private.txt').write_text('Private note')
        run('git', 'add', 'private.txt', cwd=self.root)
        run('git', 'commit', '-m', 'Local-only note', cwd=self.root)
        with self.assertRaises(RuntimeError):
            publisher.publish_report(self.root, report)
        self.assertEqual(self.before, self.head())

    def test_rejects_personal_email_and_path(self):
        for content in ['Contact: example' + '@gmail.com', '/Users/' + 'SAMPLE/Documents/notes']:
            report = self.report(content)
            with self.assertRaises(ValueError):
                publisher.publish_report(self.root, report)
        self.assertEqual(self.before, self.head())

    def test_rejects_personal_commit_email(self):
        run('git', 'config', 'user.email', 'test@example.org', cwd=self.root)
        with self.assertRaises(RuntimeError):
            publisher.publish_report(self.root, self.report())
        self.assertEqual(self.before, self.head())

    def test_missing_scanner_fails_closed(self):
        report = self.report()
        with patch.object(publisher.shutil, 'which', return_value=None):
            with self.assertRaises(RuntimeError):
                publisher.publish_report(self.root, report)
        self.assertEqual(self.before, self.head())

    def test_secret_rejected_by_real_scanner(self):
        synthetic = 'gh' + 'p_' + 'Q7r9X2m5Lp8aT4v6Y1c3N0kZsDgFhJbWqEuR'
        report = self.report('GITHUB_TOKEN=' + synthetic)
        with self.assertRaisesRegex(RuntimeError, "비밀정보 검사 미통과"):
            publisher.publish_report(self.root, report)
        self.assertEqual(self.before, self.head())

    def test_publishes_only_report(self):
        report = publisher.save_report(self.root, 'Reviewed public notes.\n', '검토완료')
        (self.root / 'README.md').write_text('Unrelated local edit\n')
        (self.root / 'private.txt').write_text('Untracked personal note\n')
        publisher.publish_report(self.root, report)
        self.assertNotEqual(self.before, self.head())
        files = run('git', '--git-dir', str(self.remote), 'ls-tree', '-r', '--name-only', 'main')
        self.assertNotIn('private.txt', files)
        self.assertEqual('Existing public material', run('git', '--git-dir', str(self.remote), 'show', 'main:README.md'))
        self.assertEqual('Unrelated local edit\n', (self.root / 'README.md').read_text())
        self.assertEqual('Untracked personal note\n', (self.root / 'private.txt').read_text())
        self.assertEqual('Reviewed public notes.', run('git', '--git-dir', str(self.remote), 'show', 'main:' + report.relative_to(self.root).as_posix()))


if __name__ == '__main__':
    unittest.main()
