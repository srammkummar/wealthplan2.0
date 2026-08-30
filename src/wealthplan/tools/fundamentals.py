"""Historical company fundamentals from SEC company facts."""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from pydantic import BaseModel

from wealthplan.config import Settings
from wealthplan.ingestion.pipeline import SecEdgarClient
from wealthplan.resilience import TimestampedTTLCache, retry_call


ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}
CONCEPTS = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "Revenues",
    ],
    "diluted_eps": ["EarningsPerShareDiluted"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capital_expenditures": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "share_repurchases": ["PaymentsForRepurchaseOfCommonStock"],
}


class AnnualFundamentals(BaseModel):
    fiscal_year: int
    revenue_millions: float
    diluted_eps: float | None = None
    operating_cash_flow_millions: float | None = None
    capital_expenditures_millions: float | None = None
    free_cash_flow_millions: float | None = None
    share_repurchases_millions: float | None = None


class FundamentalsSnapshot(BaseModel):
    ticker: str
    company: str
    as_of: str
    annual: AnnualFundamentals
    valuation_available: bool
    snapshot_label: str
    source_url: str
    notes: list[str]
    cik: str | None = None
    accession_number: str | None = None
    retrieved_at: str | None = None
    cache_status: str | None = None


APPLE_FY2025 = FundamentalsSnapshot(
    ticker="AAPL",
    company="Apple Inc.",
    as_of="2025-09-27",
    annual=AnnualFundamentals(
        fiscal_year=2025,
        revenue_millions=416_161,
        diluted_eps=7.46,
        operating_cash_flow_millions=111_482,
        capital_expenditures_millions=12_715,
        free_cash_flow_millions=98_767,
        share_repurchases_millions=89_300,
    ),
    valuation_available=False,
    snapshot_label="Fixed historical demo snapshot; not live market data.",
    source_url=(
        "https://www.sec.gov/Archives/edgar/data/320193/"
        "000032019325000079/aapl-20250927.htm"
    ),
    notes=[
        "Free cash flow is calculated as operating cash flow minus payments for property, plant, and equipment.",
        "Current price and valuation multiples are intentionally unavailable.",
        "The original n8n eight-quarter series can be added later from a sanitized public-data specification.",
    ],
    cik="0000320193",
    accession_number="0000320193-25-000079",
)


class CompanyFactsSource(Protocol):
    def resolve_ticker(self, ticker: str) -> dict[str, str]: ...

    def get_company_facts(self, cik: str) -> dict[str, Any]: ...


def _is_annual_duration(fact: dict[str, Any]) -> bool:
    if fact.get("form") not in ANNUAL_FORMS or not fact.get("start"):
        return False
    try:
        duration = date.fromisoformat(fact["end"]) - date.fromisoformat(fact["start"])
    except (KeyError, TypeError, ValueError):
        return False
    return duration.days >= 250


def _latest_fact(
    payload: dict[str, Any],
    concept_names: list[str],
    unit: str,
    *,
    target_end: str | None = None,
) -> tuple[str, dict[str, Any]] | None:
    taxonomy = payload.get("facts", {}).get("us-gaap", {})
    candidates: list[tuple[str, dict[str, Any]]] = []
    for concept_name in concept_names:
        concept = taxonomy.get(concept_name, {})
        for fact in concept.get("units", {}).get(unit, []):
            if not _is_annual_duration(fact):
                continue
            if target_end and fact.get("end") != target_end:
                continue
            candidates.append((concept_name, fact))
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (item[1].get("end", ""), item[1].get("filed", "")),
    )


def _millions(fact: dict[str, Any] | None) -> float | None:
    if fact is None or fact.get("val") is None:
        return None
    return round(float(fact["val"]) / 1_000_000, 3)


def snapshot_from_company_facts(
    payload: dict[str, Any], *, ticker: str, cik: str
) -> FundamentalsSnapshot | None:
    """Build a latest-annual US-GAAP snapshot without live market data."""

    revenue_match = _latest_fact(payload, CONCEPTS["revenue"], "USD")
    if revenue_match is None:
        return None
    revenue_concept, revenue_fact = revenue_match
    target_end = revenue_fact["end"]

    eps_match = _latest_fact(
        payload, CONCEPTS["diluted_eps"], "USD/shares", target_end=target_end
    )
    operating_match = _latest_fact(
        payload, CONCEPTS["operating_cash_flow"], "USD", target_end=target_end
    )
    capex_match = _latest_fact(
        payload, CONCEPTS["capital_expenditures"], "USD", target_end=target_end
    )
    repurchases_match = _latest_fact(
        payload, CONCEPTS["share_repurchases"], "USD", target_end=target_end
    )

    operating = _millions(operating_match[1] if operating_match else None)
    capex = _millions(capex_match[1] if capex_match else None)
    free_cash_flow = (
        round(operating - capex, 3)
        if operating is not None and capex is not None
        else None
    )
    fiscal_year = int(revenue_fact.get("fy") or target_end[:4])
    accession = revenue_fact.get("accn")
    concepts_used = [revenue_concept]
    for match in (eps_match, operating_match, capex_match, repurchases_match):
        if match:
            concepts_used.append(match[0])

    return FundamentalsSnapshot(
        ticker=ticker.strip().upper(),
        company=payload.get("entityName", ticker.strip().upper()),
        as_of=target_end,
        annual=AnnualFundamentals(
            fiscal_year=fiscal_year,
            revenue_millions=_millions(revenue_fact) or 0.0,
            diluted_eps=(
                round(float(eps_match[1]["val"]), 4) if eps_match else None
            ),
            operating_cash_flow_millions=operating,
            capital_expenditures_millions=capex,
            free_cash_flow_millions=free_cash_flow,
            share_repurchases_millions=_millions(
                repurchases_match[1] if repurchases_match else None
            ),
        ),
        valuation_available=False,
        snapshot_label="Historical SEC company facts; not live market data.",
        source_url=(
            "https://data.sec.gov/api/xbrl/companyfacts/"
            f"CIK{str(cik).zfill(10)}.json"
        ),
        notes=[
            "Values come from the latest matching annual SEC facts and may be unavailable when an issuer uses different taxonomy concepts.",
            "Free cash flow is calculated as operating cash flow minus payments to acquire property, plant, and equipment when both facts are available.",
            "Current price and valuation multiples are unavailable because SEC company facts are historical filing data, not a live market-data feed.",
            f"US-GAAP concepts used: {', '.join(concepts_used)}.",
        ],
        cik=str(cik).zfill(10),
        accession_number=accession,
    )


class SecCompanyFactsService:
    """Resolve tickers and return cached annual SEC fundamentals snapshots."""

    def __init__(
        self,
        settings: Settings,
        *,
        source: CompanyFactsSource | None = None,
        cache_ttl_seconds: float | None = None,
        retry_attempts: int | None = None,
    ) -> None:
        self.source = source
        if self.source is None and settings.sec_user_agent:
            self.source = SecEdgarClient(
                settings.sec_user_agent,
                request_interval_seconds=settings.sec_request_interval_seconds,
            )
        self.retry_attempts = max(
            1,
            settings.external_retry_attempts
            if retry_attempts is None
            else retry_attempts,
        )
        self._cache = TimestampedTTLCache[str, FundamentalsSnapshot](
            settings.sec_cache_ttl_seconds
            if cache_ttl_seconds is None
            else cache_ttl_seconds
        )

    def get(self, ticker: str) -> FundamentalsSnapshot | None:
        normalized = ticker.strip().upper()
        cached = self._cache.get_fresh(normalized)
        if cached is not None:
            return cached.value.model_copy(
                deep=True,
                update={
                    "retrieved_at": cached.stored_at_iso,
                    "cache_status": "fresh_cache",
                },
            )
        if self.source is None:
            snapshot = get_company_fundamentals(normalized)
            if snapshot is None:
                return None
            record = self._cache.set(normalized, snapshot)
            return snapshot.model_copy(
                deep=True,
                update={
                    "retrieved_at": record.stored_at_iso,
                    "cache_status": "offline_fallback",
                },
            )

        def load_snapshot() -> FundamentalsSnapshot | None:
            resolved = self.source.resolve_ticker(normalized)
            payload = self.source.get_company_facts(resolved["cik"])
            return snapshot_from_company_facts(
                payload, ticker=normalized, cik=resolved["cik"]
            )

        try:
            snapshot, _attempts = retry_call(
                load_snapshot,
                attempts=self.retry_attempts,
                is_retryable=lambda exc: not isinstance(
                    exc, (LookupError, ValueError)
                ),
            )
        except (LookupError, ValueError):
            raise
        except Exception as exc:
            stale = self._cache.get_stale(normalized)
            if stale is not None:
                return stale.value.model_copy(
                    deep=True,
                    update={
                        "retrieved_at": stale.stored_at_iso,
                        "cache_status": "stale_cache",
                        "notes": [
                            *stale.value.notes,
                            (
                                "The SEC service was temporarily unavailable; "
                                f"showing cached data retrieved at {stale.stored_at_iso}."
                            ),
                        ],
                    },
                )
            raise RuntimeError(
                f"SEC company facts are temporarily unavailable for {normalized} "
                f"after {self.retry_attempts} attempts."
            ) from exc

        if snapshot is None:
            return None
        record = self._cache.set(normalized, snapshot)
        return snapshot.model_copy(
            deep=True,
            update={
                "retrieved_at": record.stored_at_iso,
                "cache_status": "live",
            },
        )


def get_company_fundamentals(ticker: str) -> FundamentalsSnapshot | None:
    """Return the offline AAPL fallback without inventing other ticker data."""

    if ticker.strip().upper() == "AAPL":
        return APPLE_FY2025.model_copy(deep=True)
    return None
