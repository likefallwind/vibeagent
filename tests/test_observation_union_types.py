import unittest

from vibeagent import observation_types, observation_union_types


class ObservationUnionTypesTests(unittest.TestCase):
    def test_observation_types_reexports_observation_union(self) -> None:
        self.assertIs(observation_types.Observation, observation_union_types.Observation)


if __name__ == "__main__":
    unittest.main()
