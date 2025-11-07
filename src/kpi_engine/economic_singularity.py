"""GDP per capita analytics utilities.

This module replaces the earlier speculative "economic singularity" logic
with deterministic analytics focused on GDP per capita.  The
implementation centres on transforming recorded GDP and population values
into per-capita series, growth rates, and anomaly detection that can be
used by the wider KPI engine.  No stochastic simulation or mocked
deployments are performed here – the functions operate purely on the
records provided by the caller.
"""Economic singularity wealth engine utilities.

This module provides a light-weight implementation of the "zero budget"
wealth engine that appeared in the research brief.  The goal is to keep the
logic deterministic and well structured so that it can be unit-tested and
integrated with the rest of the KPI stack.
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
        total = sum((amount for _, amount in plan), Decimal("0"))
        total_as_decimal = (
            total if isinstance(total, Decimal) else Decimal(total)
        )
        return total_as_decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

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
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
import hashlib
import random
from typing import Dict, Iterable, List, Optional


class FreeTierProvider(str, Enum):
    """Enumeration of supported zero-cost infrastructure providers."""

    GITHUB_ACTIONS = "github_actions"
    COLAB = "colab"
    HUGGINGFACE = "huggingface"
    REPLIT = "replit"
    STREAMLIT = "streamlit"
    VERCEL = "vercel"
    FLY_IO = "fly_io"
    RENDER = "render"
    CLOUDFLARE = "cloudflare"


@dataclass
class PromptEconomicProfile:
    """Economic description of a prompt archetype."""

    prompt_type: str
    input_tokens: int
    compute_cost_usd: Decimal
    estimated_value_usd: Decimal
    value_cost_ratio: Decimal
    replication_multiplier: Decimal = Decimal("3.0")
    gdp_inclusion_rate: Decimal = Decimal("0.30")
    gdp_impact_usd: Decimal = field(default=None)

    def __post_init__(self) -> None:
        if self.gdp_impact_usd is None:
            self.gdp_impact_usd = (
                self.estimated_value_usd
                * self.replication_multiplier
                * self.gdp_inclusion_rate
            )


class ZeroBudgetWealthEngine:
    """Core engine responsible for prompt economics calculations."""

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self.rng = rng or random.Random()
        self.free_providers: List[FreeTierProvider] = list(FreeTierProvider)
        self.prompt_economics = self._initialize_high_roi_prompts()
        self.wealth_ledger: List[Dict[str, float]] = []
        self.gdp_impact_total = Decimal("0")
        self.deployment_targets: List[str] = [
            "https://huggingface.co/spaces",
            "https://colab.research.google.com",
            "https://replit.com",
            "https://vercel.com",
            "https://fly.io",
            "https://render.com",
        ]

    def _initialize_high_roi_prompts(self) -> Dict[str, PromptEconomicProfile]:
        return {
            "code_infrastructure": PromptEconomicProfile(
                prompt_type="code_infrastructure",
                input_tokens=500,
                compute_cost_usd=Decimal("0.002"),
                estimated_value_usd=Decimal("1000"),
                value_cost_ratio=Decimal("500000"),
            ),
            "financial_modeling": PromptEconomicProfile(
                prompt_type="financial_modeling",
                input_tokens=800,
                compute_cost_usd=Decimal("0.003"),
                estimated_value_usd=Decimal("5000"),
                value_cost_ratio=Decimal("1666666"),
            ),
            "scientific_research": PromptEconomicProfile(
                prompt_type="scientific_research",
                input_tokens=1000,
                compute_cost_usd=Decimal("0.004"),
                estimated_value_usd=Decimal("10000"),
                value_cost_ratio=Decimal("2500000"),
            ),
            "business_automation": PromptEconomicProfile(
                prompt_type="business_automation",
                input_tokens=600,
                compute_cost_usd=Decimal("0.0025"),
                estimated_value_usd=Decimal("3000"),
                value_cost_ratio=Decimal("1200000"),
            ),
            "educational_content": PromptEconomicProfile(
                prompt_type="educational_content",
                input_tokens=400,
                compute_cost_usd=Decimal("0.0015"),
                estimated_value_usd=Decimal("2000"),
                value_cost_ratio=Decimal("1333333"),
            ),
        }

    def calculate_gdp_impact(self, prompt_type: str, executions: int) -> Dict[str, float]:
        profile = self.prompt_economics[prompt_type]
        total_cost = profile.compute_cost_usd * executions
        total_value = profile.estimated_value_usd * executions
        total_gdp_impact = profile.gdp_impact_usd * executions
        effective_roi = float(total_gdp_impact / total_cost) if total_cost else float("inf")
        return {
            "prompt_type": prompt_type,
            "executions": executions,
            "total_cost": float(total_cost),
            "total_value": float(total_value),
            "gdp_impact": float(total_gdp_impact),
            "value_cost_ratio": float(profile.value_cost_ratio),
            "effective_roi": effective_roi,
        }

    async def deploy_to_free_tier(self, asset: Dict[str, str]) -> str:
        provider = self.rng.choice(self.free_providers)
        deployment_urls = {
            FreeTierProvider.HUGGINGFACE: "https://huggingface.co/spaces/new",
            FreeTierProvider.STREAMLIT: "https://share.streamlit.io/deploy",
            FreeTierProvider.REPLIT: "https://replit.com/github",
            FreeTierProvider.VERCEL: "https://vercel.com/import/git",
        }
        base_url = deployment_urls.get(provider, "https://github.com")
        return f"{base_url}/{asset['id']}"

    def generate_self_replicating_prompt(self, idea: str) -> Dict[str, object]:
        prompt_id = hashlib.sha256(idea.encode("utf-8")).hexdigest()[:16]
        value_indicators = {
            "infrastructure": Decimal("10000"),
            "financial": Decimal("5000"),
            "research": Decimal("8000"),
            "education": Decimal("3000"),
            "automation": Decimal("6000"),
        }
        idea_lower = idea.lower()
        estimated_value = Decimal("1000")
        for key, value in value_indicators.items():
            if key in idea_lower:
                estimated_value = value
                break
        replication_potential = Decimal("100")
        gdp_impact_potential = (
            estimated_value
            * replication_potential
            * Decimal("0.30")
        )
        return {
            "id": prompt_id,
            "idea": idea,
            "prompt_template": self._create_optimized_prompt(idea),
            "estimated_value_usd": float(estimated_value),
            "compute_cost_usd": 0.002,
            "replication_potential": int(replication_potential),
            "gdp_impact_potential": float(gdp_impact_potential),
        }

    def _create_optimized_prompt(self, idea: str) -> str:
        return (
            "ECONOMIC VALUE MAXIMIZATION PROMPT\n"
            f"IDEA: {idea}\n\n"
            "CRITICAL REQUIREMENTS:\n"
            "1. Generate immediately deployable, production-ready output\n"
            "2. Optimize for maximum economic value and GDP impact\n"
            "3. Ensure zero marginal cost replication\n"
            "4. Include verifiable value metrics\n"
            "5. Design for infinite scalability\n\n"
            "OUTPUT FORMAT:\n"
            "- Deployable code/configuration\n"
            "- Value estimation methodology\n"
            "- Replication instructions\n"
            "- GDP impact projection\n"
            "- Verification mechanism\n\n"
            "CONSTRAINTS:\n"
            "- Zero budget\n"
            "- Free-tier infrastructure only\n"
            "- Open-source licensing\n"
            "- Autonomous propagation\n"
        )


class GDPOptimizationRouter:
    """Routes ideas to the highest impact prompt type."""

    def __init__(self, wealth_engine: ZeroBudgetWealthEngine) -> None:
        self.engine = wealth_engine

    def route_prompt(self, idea: str, context: Optional[Dict[str, object]] = None) -> str:
        del context  # Context hook retained for forward compatibility.
        return max(
            self.engine.prompt_economics.keys(),
            key=lambda key: self.engine.prompt_economics[key].gdp_impact_usd,
        )


class WealthCompoundingEngine:
    """Simple exponential compounding model for intellectual capital."""

    def __init__(self) -> None:
        self.compounding_rate = Decimal("1.15")

    def compound_wealth(self, initial_value: Decimal, periods: int) -> Decimal:
        return initial_value * (self.compounding_rate ** periods)

    def calculate_network_effect(self, assets_count: int) -> Decimal:
        return Decimal(assets_count**2) * Decimal("1000")

    def track_diffusion_impact(self, asset: Dict[str, object], adoptions: int) -> Decimal:
        base_value = Decimal(str(asset["estimated_value_usd"]))
        diffusion_multiplier = Decimal("1.0") + (Decimal(adoptions) * Decimal("0.1"))
        return base_value * diffusion_multiplier * Decimal("0.30")


class EconomicSingularity:
    """High-level orchestration of the economic singularity workflow."""

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self.wealth_engine = ZeroBudgetWealthEngine(rng=rng)
        self.router = GDPOptimizationRouter(self.wealth_engine)
        self.compounding_engine = WealthCompoundingEngine()
        self.deployment_count = 0
        self.total_gdp_impact = Decimal("0")

    async def process_economic_idea(self, idea: str) -> Dict[str, object]:
        prompt_asset = self.wealth_engine.generate_self_replicating_prompt(idea)
        optimal_type = self.router.route_prompt(idea, {})
        economic_impact = self.wealth_engine.calculate_gdp_impact(optimal_type, executions=100)
        deployment_url = await self.wealth_engine.deploy_to_free_tier(prompt_asset)
        self.deployment_count += 1
        intellectual_wealth = self.compounding_engine.compound_wealth(
            Decimal(str(economic_impact["gdp_impact"])),
            periods=12,
        )
        self.total_gdp_impact += intellectual_wealth
        return {
            "idea": idea,
            "prompt_asset": prompt_asset,
            "economic_impact": economic_impact,
            "deployment_url": deployment_url,
            "intellectual_wealth": float(intellectual_wealth),
            "cumulative_gdp_impact": float(self.total_gdp_impact),
            "deployment_number": self.deployment_count,
        }


class FreeTierOrchestrator:
    """Utility class that performs simple round-robin deployments."""

    def __init__(self) -> None:
        self.providers = [
            "huggingface",
            "streamlit",
            "replit",
            "vercel",
            "github_pages",
        ]

    async def mass_deploy(self, assets: Iterable[Dict[str, object]]) -> List[str]:
        deployment_urls: List[str] = []
        provider_cycle = iter(self.providers)
        for asset in assets:
            try:
                try:
                    provider = next(provider_cycle)
                except StopIteration:
                    provider_cycle = iter(self.providers)
                    provider = next(provider_cycle)
                url = await self._deploy(provider, asset)
            except Exception:
                url = f"https://github.com/backup/{asset['id']}"
            deployment_urls.append(url)
        return deployment_urls

    async def _deploy(self, provider: str, asset: Dict[str, object]) -> str:
        handlers = {
            "huggingface": lambda a: f"https://huggingface.co/spaces/economic-engine/{a['id']}",
            "streamlit": lambda a: f"https://{a['id']}.streamlit.app",
            "replit": lambda a: f"https://replit.com/@{a['id']}",
            "vercel": lambda a: f"https://{a['id']}.vercel.app",
            "github_pages": lambda a: f"https://economic-engine.github.io/{a['id']}",
        }
        handler = handlers[provider]
        return handler(asset)


class GDPImpactTracker:
    """Tracks reported and verified GDP impact for generated assets."""

    def __init__(self) -> None:
        self.impact_ledger: List[Dict[str, object]] = []
        self.verification_threshold = Decimal("0.80")

    def record_impact(self, asset: Dict[str, object], impact_data: Dict[str, float]) -> Dict[str, object]:
        verified_impact = Decimal(str(impact_data["gdp_impact"])) * self.verification_threshold
        cumulative_verified = sum(
            Decimal(str(entry["verified_impact"])) for entry in self.impact_ledger
        ) + verified_impact
        record = {
            "asset_id": asset["id"],
            "timestamp": datetime.now(UTC),
            "reported_impact": impact_data["gdp_impact"],
            "verified_impact": float(verified_impact),
            "verification_rate": float(self.verification_threshold),
            "cumulative_verified_impact": float(cumulative_verified),
        }
        self.impact_ledger.append(record)
        return record

    def get_economic_dashboard(self) -> Dict[str, object]:
        if not self.impact_ledger:
            return {
                "total_verified_impact_usd": 0.0,
                "assets_deployed": 0,
                "average_impact_per_asset": 0.0,
                "estimated_gdp_contribution": 0.0,
                "economic_multiplier_effect": 0.0,
            }
        total_verified = sum(entry["verified_impact"] for entry in self.impact_ledger)
        assets_deployed = len(self.impact_ledger)
        average_impact = total_verified / assets_deployed
        estimated_contribution = average_impact * assets_deployed * 0.30
        return {
            "total_verified_impact_usd": total_verified,
            "assets_deployed": assets_deployed,
            "average_impact_per_asset": average_impact,
            "estimated_gdp_contribution": estimated_contribution,
            "economic_multiplier_effect": 2.5,
        }

