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



CONTINENT_MAP = {
    "AFG":"Asia","AGO":"Africa","ALB":"Europe","AMR":"Americas","ARE":"Asia","ARG":"Americas","ARM":"Asia","AUS":"Oceania","AUT":"Europe",
    "BDI":"Africa","BEL":"Europe","BEN":"Africa","BFA":"Africa","BGD":"Asia","BGR":"Europe","BIH":"Europe","BOL":"Americas","BRA":"Americas","BRN":"Asia","BTN":"Asia","BWA":"Africa",
    "CAF":"Africa","CAN":"Americas","CHE":"Europe","CHL":"Americas","CHN":"Asia","CIV":"Africa","CMR":"Africa","COD":"Africa","COG":"Africa","COL":"Americas","COM":"Africa","CRI":"Americas","CUB":"Americas","CZE":"Europe",
    "DEU":"Europe","DJI":"Africa","DNK":"Europe","DOM":"Americas","DZA":"Africa",
    "ECU":"Americas","EGY":"Africa","EMR":"Asia","ERI":"Africa","ESP":"Europe","EST":"Europe","ETH":"Africa","EUR":"Europe",
    "FIN":"Europe","FJI":"Oceania","FRA":"Europe",
    "GAB":"Africa","GBR":"Europe","GEO":"Asia","GHA":"Africa","GIN":"Africa","GLOBAL":"Global","GMB":"Africa","GNB":"Africa","GNQ":"Africa","GRC":"Europe","GTM":"Americas","GUY":"Americas",
    "HND":"Americas","HRV":"Europe","HTI":"Americas","HUN":"Europe",
    "IDN":"Asia","IND":"Asia","IRL":"Europe","IRN":"Asia","IRQ":"Asia","ISL":"Europe","ISR":"Asia","ITA":"Europe",
    "JAM":"Americas","JOR":"Asia","JPN":"Asia",
    "KAZ":"Asia","KEN":"Africa","KGZ":"Asia","KHM":"Asia","KOR":"Asia","KWT":"Asia",
    "LAO":"Asia","LBN":"Asia","LBR":"Africa","LBY":"Africa","LKA":"Asia","LUX":"Europe","LVA":"Europe",
    "MAR":"Africa","MDA":"Europe","MDG":"Africa","MDV":"Asia","MEX":"Americas","MLI":"Africa","MLT":"Europe","MMR":"Asia","MNG":"Asia","MOZ":"Africa","MRT":"Africa","MUL":"Global","MWI":"Africa","MYS":"Asia",
    "NAM":"Africa","NCL":"Oceania","NER":"Africa","NGA":"Africa","NIC":"Americas","NLD":"Europe","NOR":"Europe","NPL":"Asia","NZL":"Oceania",
    "OMN":"Asia","OWID_NAM":"Americas","OWID_OCE":"Oceania","OWID_SAM":"Americas",
    "PAK":"Asia","PAN":"Americas","PER":"Americas","PHL":"Asia","PNG":"Oceania","POL":"Europe","PRK":"Asia","PRT":"Europe","PRY":"Americas","PSE":"Asia",
    "QAT":"Asia",
    "ROU":"Europe","RUS":"Europe","RWA":"Africa",
    "SAU":"Asia","SDN":"Africa","SEAR":"Asia","SEN":"Africa","SGP":"Asia","SLE":"Africa","SLV":"Americas","SOM":"Africa","SRB":"Europe","SSD":"Africa","SVK":"Europe","SVN":"Europe","SWE":"Europe","SWZ":"Africa","SYR":"Asia",
    "TCD":"Africa","TGO":"Africa","THA":"Asia","TJK":"Asia","TKM":"Asia","TLS":"Asia","TTO":"Americas","TUN":"Africa","TUR":"Asia","TWN":"Asia","TZA":"Africa",
    "UGA":"Africa","UKR":"Europe","URY":"Americas","USA":"Americas","UZB":"Asia",
    "VEN":"Americas","VNM":"Asia",
    "WB_HI":"Global","WB_LI":"Global","WB_LMI":"Global","WB_UMI":"Global","WPR":"Asia",
    "YEM":"Asia",
    "ZAF":"Africa","ZMB":"Africa","ZWE":"Africa",
}

PATHOGEN_TYPES = {
    "Cholera":"Bacteria","Ebola Virus Disease":"Virus","Marburg Virus Disease":"Virus",
    "Mpox":"Virus","Dengue":"Virus","Measles":"Virus","Influenza":"Virus",
    "Hantavirus":"Virus","Yellow Fever":"Virus","Diphtheria":"Bacteria",
    "Lassa Fever":"Virus","Nipah Virus Infection":"Virus","Malaria":"Parasite",
    "Avian Influenza":"Virus","COVID":"Virus","SARS":"Virus","Plague":"Bacteria",
    "Anthrax":"Bacteria","Rabies":"Virus","Rift Valley Fever":"Virus",
    "West Nile Virus":"Virus","Crimean-Congo Hemorrhagic Fever":"Virus",
    "Hepatitis E":"Virus","Legionellosis":"Bacteria","Chikungunya":"Virus",
    "Zika virus disease":"Virus","Typhoid fever":"Bacteria",
    "Meningococcal Meningitis":"Bacteria","Poliomyelitis":"Virus",
    "Japanese Encephalitis":"Virus","Rubella":"Virus","Mumps":"Virus",
    "Neonatal Tetanus":"Bacteria","MERS":"Virus","Acute Unknown Illness":"Unknown",
    "Novel coronavirus infection":"Virus","Oropouche Virus Disease":"Virus",
    "Sudan Virus Disease":"Virus","HIV cases":"Virus","Botulism":"Bacteria",
    "Enterovirus":"Virus","Enterovirus Infection":"Virus",
    "Epidemic encephalitis":"Virus","Leptospirosis":"Bacteria",
    "Listeriosis":"Bacteria","Psittacosis":"Bacteria","Shigellosis":"Bacteria",
    "Bloody diarrhoea":"Unknown","Undiagnosed disease":"Unknown",
    "Cases of Undiagnosed Febrile Illness":"Unknown",
    "Western Equine Encephalitis":"Virus","Chapare haemorrhagic fever":"Virus",
    "Iatrogenic Botulism":"Bacteria",
    "Upsurge of respiratory illnesses among children":"Unknown",
    "Middle East Respiratory Syndrome Coronavirus":"Virus",
    "Middle East respiratory syndrome coronavirus":"Virus",
}

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
        # Normalize disease names to merge duplicates
        DISEASE_NORMALIZE = {
            "Novel coronavirus infection": "COVID",
            "Middle East Respiratory Syndrome Coronavirus": "MERS",
            "Middle East respiratory syndrome coronavirus": "MERS",
            "Chikungunya virus disease": "Chikungunya",
            "Western equine encephalitis": "Western Equine Encephalitis",
        }
        for o in self._outbreaks:
            if o.disease in DISEASE_NORMALIZE:
                o.disease = DISEASE_NORMALIZE[o.disease]
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
                      severity: Optional[Severity] = None, verified_only: bool = False,
                      continent: Optional[str] = None, pathogen_type: Optional[str] = None) -> list[OutbreakReport]:
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
        if continent:
            filtered = [o for o in filtered if CONTINENT_MAP.get(o.country_iso3, "") == continent]
        if pathogen_type:
            filtered = [o for o in filtered if PATHOGEN_TYPES.get(o.disease, "") == pathogen_type]
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
        outbreaks_enriched = []
        for o in self._outbreaks:
            d = o.to_dict()
            d["continent"] = CONTINENT_MAP.get(o.country_iso3, "Unknown")
            d["pathogen_type"] = PATHOGEN_TYPES.get(o.disease, "Unknown")
            outbreaks_enriched.append(d)
        data = {
            "last_update": datetime.utcnow().isoformat(),
            "summary": self.get_global_summary().to_dict(),
            "diseases": self.get_disease_summary(),
            "outbreaks": outbreaks_enriched,
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
