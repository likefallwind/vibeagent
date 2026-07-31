import unittest
from typing import get_args

from vibeagent import observation_edit_union_types, observation_union_types
from vibeagent.observation_edit_path_types import MoveFileObservation
from vibeagent.observation_edit_types import EditFileObservation
from vibeagent.observation_file_mutation_types import JsonSetObservation, WriteFileObservation


class ObservationEditUnionTypesTests(unittest.TestCase):
    def test_main_observation_union_includes_representative_edit_types(self) -> None:
        observation_members = set(get_args(observation_union_types.Observation))

        self.assertIn(WriteFileObservation, observation_members)
        self.assertIn(JsonSetObservation, observation_members)
        self.assertIn(EditFileObservation, observation_members)
        self.assertIn(MoveFileObservation, observation_members)

    def test_edit_aliases_include_representative_types(self) -> None:
        file_mutation_members = set(get_args(observation_edit_union_types.FileMutationObservation))
        edit_members = set(get_args(observation_edit_union_types.EditObservation))

        self.assertIn(WriteFileObservation, file_mutation_members)
        self.assertIn(JsonSetObservation, file_mutation_members)
        self.assertIn(EditFileObservation, edit_members)
        self.assertIn(MoveFileObservation, edit_members)


if __name__ == "__main__":
    unittest.main()
