from __future__ import annotations
import csv
import io
import requests
from datetime import datetime
from ..models import OutbreakReport, SourceType, Severity


class OWIDMpoxCollector:
    SOURCE = SourceType.OWID
    CSV_URL = "https://catalog.ourworldindata.org/garden/who/latest/monkeypox/monkeypox.csv"

    def __init__(self, cache_dir: str = "data/cache"):
        self._session = requests.Session()

    def collect(self) -> list[OutbreakReport]:
        reports = []
        try:
            data = self._fetch_latest()
            for country, row in data.items():
                report = self._make_report(country, row)
                if report:
                    reports.append(report)
        except Exception:
            pass
        return reports

    def _fetch_latest(self) -> dict:
        resp = self._session.get(self.CSV_URL, timeout=30)
        if resp.status_code != 200:
            return {}

        reader = csv.DictReader(io.StringIO(resp.text))
        latest = {}
        for row in reader:
            country = row.get("country", "")
            date = row.get("date", "")
            total = row.get("total_cases", "")
            deaths = row.get("total_deaths", "")

            if not country or country in ("World", "Africa", "Europe", "Asia", "Americas"):
                continue
            if not total or not total.replace(".", "").isdigit():
                continue

            total_int = int(float(total))
            if total_int <= 0:
                continue

            if country not in latest or date > latest[country]["date"]:
                latest[country] = {
                    "date": date,
                    "cases": total_int,
                    "deaths": int(float(deaths)) if deaths and deaths.replace(".", "").isdigit() else 0,
                    "iso": row.get("iso_code", ""),
                }
        return latest

    def _make_report(self, country: str, row: dict) -> OutbreakReport | None:
        cases = row["cases"]
        if cases < 10:
            return None

        severity = Severity.LOW
        if cases > 10000:
            severity = Severity.VERY_HIGH
        elif cases > 1000:
            severity = Severity.HIGH
        elif cases > 100:
            severity = Severity.MODERATE

        try:
            date = datetime.strptime(row["date"], "%Y-%m-%d").date()
        except ValueError:
            date = datetime.utcnow().date()

        from .who_don import COUNTRY_COORDS
        iso = row.get("iso", "")
        coords = COUNTRY_COORDS.get(country.lower(), (None, None, None))
        lat = coords[1] if coords and len(coords) >= 3 else 0.0
        lon = coords[2] if coords and len(coords) >= 3 else 0.0

        return OutbreakReport(
            outbreak_id=f"owid_mpox_{iso}_{row['date']}",
            disease="Mpox",
            location=country,
            country=country,
            country_iso3=iso,
            latitude=lat,
            longitude=lon,
            cases=cases,
            deaths=row["deaths"],
            severity=severity,
            status="active" if (datetime.utcnow().date() - date).days < 90 else "ended",
            description=f"OWID: {cases:,} total cases, {row['deaths']:,} deaths as of {row['date']}",
            source=SourceType.OWID,
            source_url="https://ourworldindata.org/monkeypox",
            date_reported=date,
            news_verified=True,
            confidence="high",
        )
