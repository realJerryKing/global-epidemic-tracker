"""Observations with explicit source, period and nullable measurements."""
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum


class SourceType(str, Enum):
    WHO_DON = 'who_don'
    WHO_GHO = 'who_gho'
    OWID = 'owid'


def count(value):
    if value is None or value == '':
        return None
    try:
        n = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('invalid count') from None
    if not n.is_finite() or n < 0 or n != n.to_integral_value() or n > 2**53-1:
        raise ValueError('count must be a nonnegative JSON-safe integer')
    return int(n)


@dataclass
class OutbreakReport:
    outbreak_id: str
    disease: str
    source: SourceType
    source_url: str
    period_type: str
    period_label: str
    date_reported: str | None = None
    country_iso3: str | None = None
    location: str = 'Not specified'
    latitude: float | None = None
    longitude: float | None = None
    cases: int | None = None
    deaths: int | None = None
    description: str = ''
    legacy: bool = False
    news_evidence: list[dict] = field(default_factory=list)

    def to_dict(self):
        return {**asdict(self), 'source': self.source.value, 'country': self.location,
                'coordinate_type': 'country_center' if self.latitude is not None else None}
