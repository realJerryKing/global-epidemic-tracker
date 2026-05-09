from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models import OutbreakReport, NewsValidation, GlobalSummary, Severity, SourceType
from ..collectors.who_don import WHODONCollector
from ..collectors.who_gho import WHOGHOCollector
from ..collectors.owid import OWIDMpoxCollector
from ..validation.news_validator import NewsValidator


class EpidemicAggregator:
    def __init__(self, cache_dir: str = "data/cache"):
        self.who = WHODONCollector(cache_dir=cache_dir)
        self.gho = WHOGHOCollector(cache_dir=cache_dir)
        self.owid = OWIDMpoxCollector(cache_dir=cache_dir)
        self.validator = NewsValidator(cache_dir=cache_dir)
        self._outbreaks: list[OutbreakReport] = []
        self._validations: dict[str, NewsValidation] = {}
        self._last_fetch: Optional[datetime] = None

    def fetch_all(self, validate: bool = True, max_validations: int = 15) -> None:
        self._outbreaks = self.who.collect()
        self._outbreaks.extend(self.gho.collect())
        self._outbreaks.extend(self.owid.collect())
        self._deduplicate()

        if validate and self._outbreaks:
            self._validations = self.validator.validate_batch(self._outbreaks, max_validations=max_validations)
            for outbreak in self._outbreaks:
                v = self._validations.get(outbreak.outbreak_id)
                if v:
                    outbreak.news_verified = v.consistent
                    outbreak.news_sources = v.sources_matched
                    outbreak.news_summary = v.summary

        self._last_fetch = datetime.utcnow()

    def _deduplicate(self) -> None:
        seen = set()
        unique = []
        for o in self._outbreaks:
            key = (o.disease, o.country_iso3, o.date_reported.month, o.date_reported.year)
            if key not in seen:
                seen.add(key)
                unique.append(o)
        self._outbreaks = unique

    def get_outbreaks(self, disease: Optional[str] = None, country: Optional[str] = None,
                      severity: Optional[Severity] = None, verified_only: bool = False) -> list[OutbreakReport]:
        filtered = self._outbreaks
        if disease:
            d = disease.lower()
            filtered = [o for o in filtered if d in o.disease.lower()]
        if country:
            c = country.upper()
            filtered = [o for o in filtered if o.country_iso3 == c or o.country.upper() == c]
        if severity:
            filtered = [o for o in filtered if o.severity == severity]
        if verified_only:
            filtered = [o for o in filtered if o.news_verified]
        return filtered

    def get_global_summary(self) -> GlobalSummary:
        if not self._outbreaks:
            return GlobalSummary(last_update=self._last_fetch or datetime.utcnow())

        total_cases = sum(o.cases for o in self._outbreaks)
        total_deaths = sum(o.deaths for o in self._outbreaks)
        diseases = list(set(o.disease for o in self._outbreaks))
        countries = set(o.country_iso3 for o in self._outbreaks)

        severity_order = {Severity.LOW: 0, Severity.MODERATE: 1, Severity.HIGH: 2, Severity.VERY_HIGH: 3, Severity.UNKNOWN: 0}
        highest = max(self._outbreaks, key=lambda o: severity_order.get(o.severity, 0))

        return GlobalSummary(
            total_active_outbreaks=len(self._outbreaks),
            total_cases=total_cases,
            total_deaths=total_deaths,
            global_cfr=round(total_deaths / total_cases, 4) if total_cases > 0 else 0.0,
            diseases_tracked=diseases,
            countries_affected=len(countries),
            highest_severity=highest.severity,
            last_update=self._last_fetch or datetime.utcnow(),
            data_sources=list(set(o.source.value for o in self._outbreaks)),
        )

    def get_disease_summary(self) -> dict[str, dict]:
        disease_data = {}
        for o in self._outbreaks:
            if o.disease not in disease_data:
                disease_data[o.disease] = {"cases": 0, "deaths": 0, "outbreaks": 0, "countries": set(), "h2h": False}
            d = disease_data[o.disease]
            d["cases"] += o.cases
            d["deaths"] += o.deaths
            d["outbreaks"] += 1
            d["countries"].add(o.country_iso3)
            if o.h2h_transmission:
                d["h2h"] = True

        result = {}
        for disease, data in sorted(disease_data.items(), key=lambda x: -x[1]["cases"]):
            result[disease] = {
                "cases": data["cases"],
                "deaths": data["deaths"],
                "cfr": round(data["deaths"] / data["cases"], 4) if data["cases"] > 0 else 0.0,
                "outbreaks": data["outbreaks"],
                "countries": len(data["countries"]),
                "h2h_transmission": data["h2h"],
            }
        return result

    def get_validation_summary(self) -> dict:
        total = len(self._validations)
        verified = sum(1 for v in self._validations.values() if v.consistent)
        return {
            "total_validated": total,
            "verified": verified,
            "unverified": total - verified,
            "verification_rate": f"{verified / total:.0%}" if total > 0 else "N/A",
            "details": {k: v.to_dict() for k, v in self._validations.items()},
        }

    def to_json(self, output_path: str = "data/processed/epidemics.json") -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        data = {
            "last_update": datetime.utcnow().isoformat(),
            "summary": self.get_global_summary().to_dict(),
            "diseases": self.get_disease_summary(),
            "outbreaks": [o.to_dict() for o in self._outbreaks],
            "validations": self.get_validation_summary(),
        }
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return output_path

    def to_geojson(self, output_path: str = "data/processed/epidemics.geojson") -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        features = []
        for o in self._outbreaks:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [o.longitude, o.latitude]},
                "properties": {
                    "disease": o.disease,
                    "location": o.location,
                    "country": o.country_iso3,
                    "cases": o.cases,
                    "deaths": o.deaths,
                    "cfr": o.cfr,
                    "severity": o.severity.value,
                    "h2h": o.h2h_transmission,
                    "verified": o.news_verified,
                    "source_url": o.source_url,
                    "date": o.date_reported.isoformat(),
                },
            })
        geojson = {"type": "FeatureCollection", "features": features}
        with open(output_path, "w") as f:
            json.dump(geojson, f, indent=2)
        return output_path
