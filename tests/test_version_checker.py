import unittest
from mod_updater.version_checker import (
    parse_version_tuple,
    is_candidate_newer,
    select_best_version,
)


class TestVersionChecker(unittest.TestCase):
    def test_parse_version_tuple(self):
        nums, rest = parse_version_tuple("1.21.1+fabric")
        self.assertEqual(nums, [1, 21, 1])
        self.assertEqual(rest, "+fabric")

        nums, rest = parse_version_tuple("v0.5.8")
        self.assertEqual(nums, [0, 5, 8])

    def test_is_candidate_newer(self):
        # Candidate clearly newer
        self.assertTrue(is_candidate_newer("1.0.0", "1.1.0"))
        self.assertTrue(is_candidate_newer("0.5.0", "0.5.1"))
        self.assertTrue(is_candidate_newer("1.20.1", "1.21.0"))

        # Candidate is older
        self.assertFalse(is_candidate_newer("1.2.0", "1.1.0"))
        self.assertFalse(is_candidate_newer("2.0.0", "1.9.9"))

        # Same version
        self.assertFalse(is_candidate_newer("1.2.3", "1.2.3"))

        # Unknown installed version should trigger update
        self.assertTrue(is_candidate_newer("Unknown", "1.0.0"))
        self.assertTrue(is_candidate_newer(None, "1.0.0"))

    def test_select_best_version(self):
        versions = [
            {
                "version_number": "1.0.0-beta.1",
                "version_type": "beta",
                "game_versions": ["1.21.1"],
                "loaders": ["fabric"],
            },
            {
                "version_number": "0.9.0",
                "version_type": "release",
                "game_versions": ["1.21.1"],
                "loaders": ["fabric"],
            },
            {
                "version_number": "2.0.0",
                "version_type": "release",
                "game_versions": ["1.20.1"],
                "loaders": ["fabric"],
            },
        ]

        # Prioritizes release for matching game version
        best = select_best_version(versions, "1.21.1", "fabric")
        self.assertIsNotNone(best)
        self.assertEqual(best["version_number"], "0.9.0")

        # Falls back to beta if no release available
        beta_only = [v for v in versions if v["version_type"] != "release"]
        best_beta = select_best_version(beta_only, "1.21.1", "fabric")
        self.assertIsNotNone(best_beta)
        self.assertEqual(best_beta["version_number"], "1.0.0-beta.1")

        # None if no match
        no_match = select_best_version(versions, "1.19.4", "fabric")
        self.assertIsNone(no_match)


if __name__ == "__main__":
    unittest.main()
