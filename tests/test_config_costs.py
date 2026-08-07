from dataclasses import dataclass
from decimal import Decimal
import unittest

from vibeagent import config
from vibeagent import config_costs
from vibeagent import session_costs
from vibeagent import session_usage


@dataclass(frozen=True)
class TestCostRates:
    input_usd_per_million: Decimal | None = None
    output_usd_per_million: Decimal | None = None
    cache_creation_usd_per_million: Decimal | None = None
    cache_read_usd_per_million: Decimal | None = None


class ConfigCostsTests(unittest.TestCase):
    def test_config_reexports_cost_rate_parser(self) -> None:
        self.assertIs(config.parse_cost_rate, config_costs.parse_cost_rate)

    def test_session_usage_reexports_cost_helpers(self) -> None:
        self.assertIs(session_usage.decimal_rate_string, session_costs.decimal_rate_string)
        self.assertIs(session_usage.decimal_usd_string, session_costs.decimal_usd_string)
        self.assertIs(session_usage.format_usd, session_costs.format_usd)
        self.assertIs(session_usage.missing_cost_rate_names, session_costs.missing_cost_rate_names)
        self.assertIs(session_usage.serialize_cost_rates, session_costs.serialize_cost_rates)
        self.assertIs(session_usage.token_cost, session_costs.token_cost)
        self.assertIs(session_usage.usage_has_tokens, session_costs.usage_has_tokens)

    def test_cost_rate_helpers_keep_existing_behavior(self) -> None:
        self.assertEqual(config_costs.parse_cost_rate("0.25", "RATE"), (Decimal("0.25"), None))
        self.assertEqual(config_costs.parse_cost_rate("", "RATE"), (None, None))
        self.assertEqual(config_costs.parse_cost_rate("-1", "RATE"), (None, "RATE must be a non-negative decimal."))
        self.assertEqual(config_costs.parse_cost_rate("bad", "RATE"), (None, "RATE must be a non-negative decimal."))

    def test_resolve_cost_rates_uses_supplied_factory(self) -> None:
        rates, errors = config_costs.resolve_cost_rates(
            {
                "VIBEAGENT_INPUT_USD_PER_MILLION": "0.30",
                "VIBEAGENT_OUTPUT_USD_PER_MILLION": "1.20",
                "VIBEAGENT_CACHE_CREATION_USD_PER_MILLION": "0.10",
                "VIBEAGENT_CACHE_READ_USD_PER_MILLION": "0.03",
            },
            cost_rates_factory=TestCostRates,
        )

        self.assertEqual(errors, [])
        self.assertEqual(rates.input_usd_per_million, Decimal("0.30"))
        self.assertEqual(rates.output_usd_per_million, Decimal("1.20"))
        self.assertEqual(rates.cache_creation_usd_per_million, Decimal("0.10"))
        self.assertEqual(rates.cache_read_usd_per_million, Decimal("0.03"))


if __name__ == "__main__":
    unittest.main()
