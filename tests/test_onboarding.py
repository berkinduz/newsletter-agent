import base64
from copy import deepcopy
from email import policy
from email.parser import BytesParser
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from sincap import core, mime, onboarding as o, render
from test_core import fixtures, NOW, ROOT
import test_mime


def bundle_fixture():
    profile, issue = fixtures()
    profile['delivery']['recipients'].append({'id': 'other', 'email': 'other@example.invalid'})
    rows, _, key = core.select_articles(profile, issue, core.new_history(), NOW, demo=True)
    html, plain, assets, _ = render.render(profile, issue, rows, 1, Path('missing'))
    raw, state = mime.package(profile, key, 1, html, plain, assets, NOW)
    return {'html': html, 'plain': plain, 'assets': assets, 'raw': raw, 'delivery': state}


class MailOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.bundle = bundle_fixture()
        self.connection = o.mail_connection('fixture-account', {'email': 'owner@example.invalid'})

    def test_self_test_retargets_only_verified_self_and_preserves_original(self):
        original = deepcopy(self.bundle)
        with patch('socket.socket', side_effect=AssertionError('Offline only')):
            test = o.self_test_bundle(self.bundle, self.connection, 'test/transport-fixture')
            args = o.gmail_draft_args(test, self.connection)
            self.assertEqual(args['to'], 'owner@example.invalid')
            self.assertNotIn('cc', args)
            self.assertNotIn('bcc', args)
            self.assertTrue(args['subject'].startswith('[TEST Sincap Post]'))
            self.assertTrue(o.verify_gmail_raw(test, base64.urlsafe_b64encode(test['raw']).decode()))
        self.assertEqual(self.bundle, original)
        for key in ('production/fixture', 'test/injected\r\nHeader: value'):
            with self.assertRaises(ValueError):
                o.self_test_bundle(self.bundle, self.connection, key)
        self.assertIsNone(o.new_installation('fixture')['mail'])

    def test_wrong_account_and_mutated_provider_message_stop_roundtrip(self):
        wrong = {**self.connection, 'email': 'wrong@example.invalid'}
        with self.assertRaisesRegex(ValueError, 'verified account'):
            o.gmail_draft_args(self.bundle, wrong)
        for header, value in [('To', 'extra@example.invalid'), ('Subject', 'Different content')]:
            message = BytesParser(policy=policy.SMTP).parsebytes(self.bundle['raw'])
            message.replace_header(header, value)
            with self.subTest(header=header), self.assertRaises(ValueError):
                o.verify_gmail_raw(self.bundle, base64.urlsafe_b64encode(message.as_bytes()).decode())
        with self.assertRaises(ValueError):
            o.verify_gmail_raw(self.bundle, 'not a complete raw message!')
        changed = {**self.bundle, 'plain': self.bundle['plain'] + 'changed'}
        with self.assertRaisesRegex(ValueError, 'editorial hash'):
            o.gmail_draft_args(changed, self.connection)

    def test_cli_persists_private_installation_and_loadable_delivery_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            local = Path(temporary) / 'local'
            def command(*args):
                return subprocess.run([sys.executable, '-B', '-m', 'sincap', *map(str, args)],
                                      cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(command('init', '--directory', local).returncode, 0)
            record = local / 'installation.json'
            self.assertEqual(record.stat().st_mode & 0o777, 0o600)
            self.assertFalse(json.loads(record.read_text())['scheduler']['target_verified'])
            before = record.read_bytes()
            self.assertEqual(command('init', '--directory', local).returncode, 1)
            self.assertEqual(before, record.read_bytes())
            output = local / 'preview'
            result = command('prepare', '--demo', '--profile', local / 'profile.json',
                             '--input', ROOT / 'examples/issue.json', '--at', NOW.isoformat(), '--out', output)
            self.assertEqual(result.returncode, 0, result.stderr)
            bundle = o.load_bundle(output)
            args = o.gmail_draft_args(bundle, self.connection)
            self.assertEqual(args['payload']['mime_type'], 'multipart/alternative')
            self.assertEqual([p['mime_type'] for p in args['payload']['parts']], ['text/plain', 'text/html'])
            self.assertEqual((output / 'delivery.json').stat().st_mode & 0o777, 0o600)


@unittest.skipUnless(importlib.util.find_spec('PIL'), 'Existing Pillow required for real CID byte tests')
class ImageOnboardingTests(unittest.TestCase):
    def test_three_images_fit_gmail_tree_and_changed_asset_is_rejected(self):
        fixture = test_mime.InlineImageTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        root = fixture.root
        (root / 'issue.json').write_text(json.dumps(fixture.issue))
        output = root / 'preview'
        result = subprocess.run([sys.executable, '-B', '-m', 'sincap', 'prepare', '--demo',
            '--profile', str(ROOT / 'examples/profile.json'), '--input', str(root / 'issue.json'),
            '--at', NOW.isoformat(), '--images-root', str(root), '--out', str(output)],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        bundle = o.load_bundle(output)
        connection = o.mail_connection('fixture-account', {'email': 'owner@example.invalid'})
        args = o.gmail_draft_args(bundle, connection)
        parts = args['payload']['parts']
        self.assertEqual(args['payload']['mime_type'], 'multipart/related')
        self.assertEqual(parts[0]['mime_type'], 'multipart/alternative')
        self.assertEqual(len(parts[1:]), 3)
        self.assertEqual([base64.urlsafe_b64decode(p['body']['base64_url_content']) for p in parts[1:]],
                         [asset['data'] for asset in bundle['assets']])
        self.assertEqual([p['content_id'] for p in parts[1:]], ['<' + a['cid'] + '>' for a in bundle['assets']])
        self.assertTrue(o.verify_gmail_raw(bundle, base64.urlsafe_b64encode(bundle['raw']).decode()))
        # Only retained raw bytes + the JSON contract travel to the next task.
        contract = json.loads(json.dumps(o.bundle_contract(bundle)))
        restored = o.restore_bundle(bundle['raw'], contract)
        self.assertEqual(o.gmail_draft_args(restored, connection), args)
        with self.assertRaisesRegex(ValueError, 'Retained MIME bytes'):
            o.restore_bundle(bundle['raw'] + b'changed', contract)
        (output / 'assets' / bundle['assets'][0]['filename']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'image bytes'):
            o.load_bundle(output)


class SharedStateOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.bundle = o.self_test_bundle(bundle_fixture(),
            o.mail_connection('fixture-account', {'email': 'owner@example.invalid'}), 'test/reservation-fixture')
        self.snapshot = {'version': 0, 'data': {'profile_id': 'fixture', 'history': core.new_history(), 'deliveries': {}}}

    def test_reservation_readback_and_repeat_guard_keep_test_out_of_history(self):
        candidate = o.reserve_bundle(self.snapshot, self.bundle, 'fixture-operation')
        self.assertEqual(candidate['data']['history'], self.snapshot['data']['history'])
        self.assertFalse(candidate['data']['deliveries'])
        self.assertEqual(candidate['data']['test_deliveries']['test/reservation-fixture']['status'], 'sending')
        self.assertTrue(o.verify_library_commit(candidate, deepcopy(candidate), 7, 10))
        with self.assertRaises(ValueError):
            o.reserve_bundle(candidate, self.bundle, 'second-operation')
        wrong = deepcopy(candidate)
        wrong['last_operation'] = 'another-writer'
        with self.assertRaisesRegex(ValueError, 'readback differs'):
            o.verify_library_commit(candidate, wrong, 7, 10)
        with self.assertRaisesRegex(ValueError, 'newer provider version'):
            o.verify_library_commit(candidate, candidate, 7, 7)

    def test_guarded_replace_distinguishes_provider_version_from_domain_version(self):
        probe = {'version': 0, 'data': {'probe_only': True, 'marker': 'initial'}}
        candidate = o.library_candidate(probe, {'probe_only': True, 'marker': 'A'}, 'probe-A')
        with tempfile.TemporaryDirectory() as task_a, tempfile.TemporaryDirectory() as task_b:
            path_a = Path(task_a) / 'candidate.json'
            path_b = Path(task_b) / 'candidate.json'
            path_a.write_text(json.dumps(candidate))
            path_b.write_text(json.dumps(o.library_candidate(probe, {'probe_only': True, 'marker': 'B'}, 'probe-B')))
            first = o.library_replace_args('fixture-probe-reference', 7, path_a)
            stale = o.library_replace_args('fixture-probe-reference', 7, path_b)
            remote = {'provider_version': 7, 'document': deepcopy(probe)}
            def simulated_replace(args):
                if args['expected_current_version'] != remote['provider_version']:
                    raise ValueError('Synthetic provider version conflict')
                remote.update(provider_version=10, document=json.loads(Path(args['file']).read_text()))
            simulated_replace(first)
            with self.assertRaisesRegex(ValueError, 'version conflict'):
                simulated_replace(stale)
            self.assertTrue(o.verify_library_commit(candidate, remote['document'], 7, remote['provider_version']))
            self.assertEqual(candidate['version'], 1)
            for unknown in (None, '7', True, False, -1, 7.0):
                with self.assertRaises(ValueError):
                    o.library_replace_args('fixture-probe-reference', unknown, path_a)
        # This tests argument/readback guards, not a real cross-Cloud CAS service.

    def test_ignored_precondition_can_only_damage_the_disposable_probe(self):
        installation = o.new_installation('fixture')
        installation['shared_state'].update(library_file_id='fixture-canonical-reference',
            probe_library_file_id='fixture-probe-reference')
        canonical_before = deepcopy(self.snapshot)
        probe = {'version': 0, 'data': {'probe_only': True, 'marker': 'initial'}}
        candidate_a = o.library_candidate(probe, {'probe_only': True, 'marker': 'A'}, 'probe-A')
        candidate_b = o.library_candidate(probe, {'probe_only': True, 'marker': 'B'}, 'probe-B')
        documents = {'fixture-canonical-reference': deepcopy(canonical_before),
                     'fixture-probe-reference': deepcopy(candidate_a)}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'stale-probe.json'
            path.write_text(json.dumps(candidate_b))
            request = o.library_replace_args(installation['shared_state']['probe_library_file_id'], 0, path)
            # Broken provider ignores stale expected_current_version=0 after A committed.
            documents[request['library_file_id']] = json.loads(Path(request['file']).read_text())
            with self.assertRaisesRegex(ValueError, 'readback differs'):
                o.verify_library_commit(candidate_a, documents['fixture-probe-reference'], 0, 2)
        self.assertEqual(documents['fixture-canonical-reference'], canonical_before)
        self.assertEqual(documents['fixture-probe-reference']['data']['marker'], 'B')

    def test_first_library_cas_preserves_provider_zero_and_requires_valid_readback(self):
        candidate = o.reserve_bundle(self.snapshot, self.bundle, 'first-operation')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'first-candidate.json'
            path.write_text(json.dumps(candidate))
            request = o.library_replace_args('fixture-library-reference', 0, path)
            self.assertEqual(request['expected_current_version'], 0)
            self.assertTrue(o.verify_library_commit(candidate, deepcopy(candidate), 0, 1))
        for before, after in [(-1, 0), (0, 0), (True, 1), (0, True), (None, 1), (0, 1.0)]:
            with self.subTest(before=before, after=after), self.assertRaises(ValueError):
                o.verify_library_commit(candidate, candidate, before, after)

    def test_no_scheduler_production_key_or_missing_state_reference(self):
        with self.assertRaises(ValueError):
            o.scheduled_test_prompt('fixture-library-reference', 'fixture-revision', 'production/fixture')
        with self.assertRaises(ValueError):
            o.scheduled_test_prompt('', 'fixture-revision', 'test/fixture')
