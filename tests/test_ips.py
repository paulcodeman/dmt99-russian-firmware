import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from ips import apply, encode, MAX_IMAGE

class IpsTests(unittest.TestCase):
    def test_changed_entries_and_append_round_trip(self):
        original = bytes(range(256)) * 4
        modified = bytearray(original)
        modified[908:912] = b'JUMP'
        modified[10:14] = b'VERS'
        modified.extend(b'\xff'*72 + b'OVERLAY'*10000)
        self.assertEqual(apply(original, encode(original, modified)), modified)

    def test_invalid_or_truncated_patch_is_rejected(self):
        for patch in [b'', b'PATCH', b'PATCHEOFextra', b'PATCH\0\0\0\0\x04xx', b'PATCH\0\0\0\0\0EOF']:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                apply(b'original', patch)

    def test_application_limit_is_enforced(self):
        bad = b'PATCH' + (MAX_IMAGE-1).to_bytes(3,'big') + b'\0\x02xxEOF'
        with self.assertRaises(ValueError):
            apply(b'', bad)
        with self.assertRaises(ValueError):
            encode(b'', bytes(MAX_IMAGE+1))

if __name__ == '__main__':
    unittest.main()
