"""GDP per capita analytics utilities.

This module replaces the earlier speculative "economic singularity" logic
with deterministic analytics focused on GDP per capita.  The
implementation centres on transforming recorded GDP and population values
into per-capita series, growth rates, and anomaly detection that can be
used by the wider KPI engine.  No stochastic simulation or mocked
deployments are performed here – the functions operate purely on the
records provided by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Iterable, List, Sequence, Tuple


DecimalType = Decimal  # Alias retained for clarity in type signatures.


@dataclass(frozen=True)
class GDPRecord:
    """Single observation of a country's GDP and population."""

    country: str
    year: int
    gdp_usd: Decimal
    population: int

    def gdp_per_capita(self) -> DecimalType:
        """Return GDP per capita rounded to two decimals."""

        if self.population <= 0:
            raise ValueError("Population must be positive to compute GDP per capita")
        value = self.gdp_usd / Decimal(self.population)
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class GDPPerCapitaDataset:
    """Collection of :class:`GDPRecord` grouped by country."""

    def __init__(self, records: Iterable[GDPRecord]):
        self._records: Dict[str, List[GDPRecord]] = {}
        for record in records:
            country_records = self._records.setdefault(record.country, [])
            country_records.append(record)
        for country in self._records:
            self._records[country].sort(key=lambda item: item.year)

    def countries(self) -> Sequence[str]:
        return tuple(sorted(self._records))

    def records_for(self, country: str) -> Sequence[GDPRecord]:
        if country not in self._records:
            raise KeyError(f"No GDP records available for country '{country}'")
        return tuple(self._records[country])


class GDPPerCapitaAnalyzer:
    """Derive GDP per capita metrics and anomalies from historical data."""

    def __init__(self, dataset: GDPPerCapitaDataset) -> None:
        self.dataset = dataset

    def per_capita_series(self, country: str) -> List[Tuple[int, DecimalType]]:
        """Return a list of ``(year, per_capita_value)`` pairs."""

        series = []
        for record in self.dataset.records_for(country):
            series.append((record.year, record.gdp_per_capita()))
        return series

    def growth_rates(self, country: str) -> List[Tuple[int, DecimalType]]:
        """Return annual GDP per capita growth rates as decimals.

        Each tuple contains ``(year, growth_rate)`` where ``year`` represents
        the later year in the pair and ``growth_rate`` is a Decimal expressing
        the proportional change between the current and previous year.
        """

        series = self.per_capita_series(country)
        growth: List[Tuple[int, DecimalType]] = []
        for idx in range(1, len(series)):
            year, current_value = series[idx]
            _, previous_value = series[idx - 1]
            if previous_value == 0:
                raise ZeroDivisionError(
                    "Cannot compute growth rate when previous per capita value is zero"
                )
            growth_value = (current_value - previous_value) / previous_value
            growth.append((year, growth_value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)))
        return growth

    def average_per_capita(self, country: str) -> DecimalType:
        """Compute the arithmetic mean GDP per capita for a country."""

        series = self.per_capita_series(country)
        if not series:
            raise ValueError(f"Country '{country}' does not contain any GDP records")
        total = sum(value for _, value in series)
        average = total / Decimal(len(series))
        return average.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def profit_relay_plan(
        self,
        country: str,
        target_growth_rate: DecimalType,
        safety_margin: DecimalType = Decimal("0"),
    ) -> List[Tuple[int, DecimalType]]:
        """Bridge growth imbalances to guarantee target per-capita profit.

        For each year after the first, this routine compares the realised GDP
        per capita against the minimum value required to satisfy the desired
        ``target_growth_rate`` plus an optional ``safety_margin``.  When the
        realised value undershoots the requirement, the shortfall is reported
        as the additional per-capita profit that must be relayed into the
        economy for that year.

        Returns a list of ``(year, shortfall)`` pairs with the shortfall
        rounded to two decimals.  Years that already meet or exceed the target
        are omitted, ensuring the plan reflects only genuine imbalances.
        """

        if target_growth_rate < 0:
            raise ValueError("Target growth rate must be non-negative")
        if safety_margin < 0:
            raise ValueError("Safety margin must be non-negative")

        shortfalls: List[Tuple[int, DecimalType]] = []
        series = self.per_capita_series(country)
        if len(series) < 2:
            return shortfalls

        multiplier = Decimal("1") + target_growth_rate + safety_margin
        for index in range(1, len(series)):
            year, current_value = series[index]
            _, previous_value = series[index - 1]
            required_value = previous_value * multiplier
            shortfall = required_value - current_value
            if shortfall > 0:
                shortfalls.append(
                    (year, shortfall.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
                )
        return shortfalls

    def profit_relay_total(
        self,
        country: str,
        target_growth_rate: DecimalType,
        safety_margin: DecimalType = Decimal("0"),
    ) -> DecimalType:
        """Sum the per-capita profit required to meet the growth objective."""

        plan = self.profit_relay_plan(country, target_growth_rate, safety_margin)
        total = sum(amount for _, amount in plan)
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def detect_unrealistic_growth(
        self,
        country: str,
        max_growth_rate: DecimalType = Decimal("0.25"),
    ) -> List[Tuple[int, DecimalType]]:
        """Flag years where GDP per capita growth exceeds ``max_growth_rate``.

        The returned list contains tuples of ``(year, growth_rate)`` representing
        the growth rate that violated the configured ceiling.  The default of
        ``0.25`` corresponds to a 25% year-over-year per capita increase, a
        conservative threshold for spotting illogical surges in the data.
        """

        if max_growth_rate <= 0:
            raise ValueError("Maximum growth rate threshold must be positive")

        anomalies: List[Tuple[int, DecimalType]] = []
        for year, growth_rate in self.growth_rates(country):
            if growth_rate > max_growth_rate:
                anomalies.append((year, growth_rate))
        return anomalies

    def summary(
        self,
        country: str,
        *,
        profit_relay_target: DecimalType | None = None,
        safety_margin: DecimalType = Decimal("0"),
    ) -> Dict[str, object]:
        """Summarise GDP per capita metrics for a country."""

        per_capita = self.per_capita_series(country)
        growth = self.growth_rates(country)
        summary: Dict[str, object] = {
            "country": country,
            "per_capita_series": per_capita,
            "growth_rates": growth,
            "average_per_capita": self.average_per_capita(country),
            "unrealistic_growth_years": self.detect_unrealistic_growth(country),
        }
        if profit_relay_target is not None:
            summary["profit_relay_plan"] = self.profit_relay_plan(
                country, profit_relay_target, safety_margin
            )
            summary["profit_relay_total"] = self.profit_relay_total(
                country, profit_relay_target, safety_margin
            )
        return summary


def build_analyzer(records: Iterable[GDPRecord]) -> GDPPerCapitaAnalyzer:
    """Helper to instantiate an analyzer directly from records."""

    dataset = GDPPerCapitaDataset(records)
    return GDPPerCapitaAnalyzer(dataset)


__all__ = [
    "GDPRecord",
    "GDPPerCapitaDataset",
    "GDPPerCapitaAnalyzer",
    "build_analyzer",
]

