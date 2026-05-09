from __future__ import annotations
import requests
from datetime import datetime
from ..models import OutbreakReport, SourceType, Severity

GHO_INDICATORS = {
    "WHS3_62": "Measles",
    "WHS3_41": "Diphtheria",
    "WHS3_50": "Yellow Fever",
    "WHS3_49": "Poliomyelitis",
    "WHS3_56": "Neonatal Tetanus",
    "WHS3_57": "Rubella",
    "WHS3_53": "Mumps",
    "WHS3_42": "Japanese Encephalitis",
}

ISO3_TO_NAME = {
    "AFG":"Afghanistan","AGO":"Angola","ARG":"Argentina","AUS":"Australia","BGD":"Bangladesh",
    "BRA":"Brazil","CHN":"China","COD":"DR Congo","COG":"Congo","EGY":"Egypt","ETH":"Ethiopia",
    "FRA":"France","DEU":"Germany","GHA":"Ghana","GIN":"Guinea","IND":"India","IDN":"Indonesia",
    "IRN":"Iran","IRQ":"Iraq","ITA":"Italy","JPN":"Japan","KEN":"Kenya","MEX":"Mexico",
    "NGA":"Nigeria","PAK":"Pakistan","PER":"Peru","PHL":"Philippines","POL":"Poland",
    "RUS":"Russia","SAU":"Saudi Arabia","ZAF":"South Africa","KOR":"South Korea","ESP":"Spain",
    "SDN":"Sudan","THA":"Thailand","TUR":"Turkey","UGA":"Uganda","UKR":"Ukraine",
    "GBR":"United Kingdom","USA":"United States","VNM":"Vietnam","YEM":"Yemen","ZWE":"Zimbabwe",
    "MMR":"Myanmar","NPL":"Nepal","SVK":"Slovakia","COL":"Colombia",
}

ISO3_TO_COORDS = {
    "AFG":(33.9,67.7),"AGO":(-11.2,17.9),"ARG":(-38.4,-63.6),"AUS":(-25.3,133.8),
    "BGD":(23.7,90.4),"BRA":(-14.2,-51.9),"CHN":(35.9,104.2),"COD":(-4.0,21.8),
    "COG":(-4.0,21.8),"EGY":(26.8,30.8),"ETH":(9.1,40.5),"FRA":(46.2,2.2),
    "DEU":(51.2,10.4),"GHA":(7.9,-1.0),"GIN":(9.9,-11.9),"IND":(20.6,79.0),
    "IDN":(-0.8,113.9),"IRN":(32.4,53.7),"IRQ":(33.2,43.7),"ITA":(41.9,12.6),
    "JPN":(36.2,138.3),"KEN":(-0.02,37.9),"MEX":(23.6,-102.6),"NGA":(9.1,8.7),
    "PAK":(30.4,69.3),"PER":(-9.2,-75.0),"PHL":(12.9,122.0),"POL":(51.9,19.1),
    "RUS":(61.5,105.3),"SAU":(23.9,45.1),"ZAF":(-30.6,22.9),"KOR":(35.9,127.8),
    "ESP":(40.5,-3.7),"SDN":(12.9,30.2),"THA":(15.9,100.9),"TUR":(38.9,35.2),
    "UGA":(1.4,32.3),"UKR":(48.4,31.2),"GBR":(55.4,-3.4),"USA":(37.1,-95.7),
    "VNM":(14.1,108.3),"YEM":(15.6,48.5),"ZWE":(-19.0,29.2),
    "MMR":(21.9,95.9),"NPL":(28.4,84.1),"SVK":(48.7,19.7),"COL":(4.6,-74.3),
}


class WHOGHOCollector:
    SOURCE = SourceType.WHO_DON
    BASE_URL = "https://ghoapi.azureedge.net/api"

    def __init__(self, cache_dir: str = "data/cache"):
        self._session = requests.Session()

    def collect(self) -> list[OutbreakReport]:
        reports = []
        for code, disease in GHO_INDICATORS.items():
            try:
                data = self._fetch_indicator(code)
                for row in data:
                    report = self._parse_row(row, disease)
                    if report and report.cases > 0:
                        reports.append(report)
            except Exception:
                continue
        return reports

    def _fetch_indicator(self, code: str) -> list[dict]:
        url = f"{self.BASE_URL}/{code}?$orderby=TimeDim desc&$top=50"
        resp = self._session.get(url, timeout=15)
        if resp.status_code != 200:
            return []
        return resp.json().get("value", [])

    def _parse_row(self, row: dict, disease: str) -> OutbreakReport | None:
        country = row.get("SpatialDim", "")
        year = row.get("TimeDim", "")
        value = row.get("NumericValue")

        if not value or not country or not year:
            return None

        cases = int(float(value))
        if cases <= 0:
            return None

        # Only include recent data (2023+)
        try:
            if int(year) < 2023:
                return None
        except ValueError:
            return None

        name = ISO3_TO_NAME.get(country, country)
        coords = ISO3_TO_COORDS.get(country, (0.0, 0.0))

        severity = Severity.LOW
        if cases > 10000:
            severity = Severity.VERY_HIGH
        elif cases > 1000:
            severity = Severity.HIGH
        elif cases > 100:
            severity = Severity.MODERATE

        return OutbreakReport(
            outbreak_id=f"gho_{country}_{disease}_{year}",
            disease=disease,
            location=name,
            country=name,
            country_iso3=country,
            latitude=coords[0],
            longitude=coords[1],
            cases=cases,
            deaths=0,
            severity=severity,
            status="active",
            description=f"WHO GHO: {cases:,} reported cases in {year}",
            source=SourceType.WHO_DON,
            source_url=f"https://www.who.int/data/gho/data/indicators/indicator-details/GHO/{disease.lower().replace(' ','-')}",
            date_reported=datetime(int(year), 12, 31).date(),
            news_verified=True,
            confidence="high",
        )
