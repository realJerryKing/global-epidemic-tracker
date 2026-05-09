"""Global Epidemic Tracker - Models."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
    UNKNOWN = "unknown"


class SourceType(str, Enum):
    WHO_DON = "who_don"
    ECDC = "ecdc"
    CDC = "cdc"
    OWID = "owid"
    PROMED = "promed"
    NEWS = "news"


@dataclass
class OutbreakReport:
    outbreak_id: str
    disease: str
    location: str
    country: str
    country_iso3: str
    latitude: float
    longitude: float
    cases: int
    deaths: int
    cases_suspected: int = 0
    severity: Severity = Severity.UNKNOWN
    cfr: float = 0.0
    status: str = "active"
    description: str = ""
    source: SourceType = SourceType.WHO_DON
    source_url: str = ""
    date_reported: date = field(default_factory=lambda: datetime.utcnow().date())
    last_update: datetime = field(default_factory=datetime.utcnow)
    h2h_transmission: bool = False
    travel_associated: bool = False
    news_verified: bool = False
    news_sources: list[str] = field(default_factory=list)
    news_summary: str = ""
    confidence: str = "medium"

    def __post_init__(self):
        if self.cases > 0 and self.cfr == 0.0:
            self.cfr = round(self.deaths / self.cases, 4)

    def to_dict(self) -> dict:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, (date, datetime)):
                d[k] = v.isoformat()
            elif isinstance(v, Enum):
                d[k] = v.value
        return d


@dataclass
class NewsValidation:
    outbreak_id: str
    query: str
    articles_found: int = 0
    sources_matched: list[str] = field(default_factory=list)
    consistent: bool = False
    additional_cases: Optional[int] = None
    additional_deaths: Optional[int] = None
    summary: str = ""
    validation_time: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d


@dataclass
class GlobalSummary:
    total_active_outbreaks: int = 0
    total_cases: int = 0
    total_deaths: int = 0
    global_cfr: float = 0.0
    diseases_tracked: list[str] = field(default_factory=list)
    countries_affected: int = 0
    highest_severity: Severity = Severity.LOW
    last_update: datetime = field(default_factory=datetime.utcnow)
    data_sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
            elif isinstance(v, Enum):
                d[k] = v.value
        return d
