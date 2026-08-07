import unittest

from vibeagent import final_review_readiness
from vibeagent import final_review_readiness_reports
from vibeagent import final_review_readiness_types


class FinalReviewReadinessModuleTests(unittest.TestCase):
    def test_readiness_module_reexports_split_types_and_helpers(self) -> None:
        self.assertIs(
            final_review_readiness.FinalReviewReadiness,
            final_review_readiness_types.FinalReviewReadiness,
        )
        self.assertIs(
            final_review_readiness.FinalReviewReadinessInputs,
            final_review_readiness_types.FinalReviewReadinessInputs,
        )
        self.assertIs(
            final_review_readiness.build_final_review_blocking_issues,
            final_review_readiness_reports.build_final_review_blocking_issues,
        )
        self.assertIs(
            final_review_readiness.build_final_review_warnings,
            final_review_readiness_reports.build_final_review_warnings,
        )
        self.assertIs(
            final_review_readiness.append_conflict_blockers,
            final_review_readiness_reports.append_conflict_blockers,
        )
        self.assertIs(
            final_review_readiness.git_operation_items,
            final_review_readiness_reports.git_operation_items,
        )


if __name__ == "__main__":
    unittest.main()
