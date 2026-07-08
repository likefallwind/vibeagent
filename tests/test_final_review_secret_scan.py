import unittest

from vibeagent import final_review_secret_scan


class FinalReviewSecretScanTests(unittest.TestCase):
    def test_assignment_confidence_ignores_scan_metadata_names(self) -> None:
        self.assertFalse(
            final_review_secret_scan.secret_like_assignment_is_high_confidence(
                "secret_findings",
                "safety_scan.secret_findings",
            )
        )
        self.assertFalse(
            final_review_secret_scan.secret_like_assignment_is_high_confidence(
                "secret_findings_total",
                "safety_scan.secret_findings_total",
            )
        )

    def test_assignment_confidence_keeps_long_token_values(self) -> None:
        self.assertTrue(
            final_review_secret_scan.secret_like_assignment_is_high_confidence(
                "api_token",
                "prod-abcdefghijklmnopqrstuvwxyz012345",
            )
        )


if __name__ == "__main__":
    unittest.main()
