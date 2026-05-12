from __future__ import annotations

import re
from datetime import datetime

from ..models import OutbreakReport, SourceType, Severity


DISEASE_ALIASES = {
    "cholera": "Cholera",
    "yellow fever": "Yellow Fever",
    "ebola": "Ebola Virus Disease",
    "marburg": "Marburg Virus Disease",
    "meningitis": "Meningococcal Meningitis",
    "meningococcal": "Meningococcal Meningitis",
    "polio": "Poliomyelitis",
    "poliomyelitis": "Poliomyelitis",
    "measles": "Measles",
    "dengue": "Dengue",
    "mpox": "Mpox",
    "monkeypox": "Mpox",
    "hantavirus": "Hantavirus",
    "influenza": "Influenza",
    "avian influenza": "Avian Influenza",
    "mers": "MERS",
    "sars": "SARS",
    "nipah": "Nipah Virus Infection",
    "rift valley": "Rift Valley Fever",
    "west nile": "West Nile Virus",
    "oropouche": "Oropouche Virus Disease",
    "rabies": "Rabies",
    "listeriosis": "Listeriosis",
    "plague": "Plague",
    "anthrax": "Anthrax",
    "lassa": "Lassa Fever",
    "crimean-congo": "Crimean-Congo Hemorrhagic Fever",
    "cchf": "Crimean-Congo Hemorrhagic Fever",
    "sudan virus": "Sudan Virus Disease",
    "acute": "Acute Unknown Illness",
}

COUNTRY_COORDS = {
    "afghanistan": ("AFG", 33.9, 67.7), "algeria": ("DZA", 28.0, 1.7),
    "angola": ("AGO", -11.2, 17.9), "argentina": ("ARG", -38.4, -63.6),
    "australia": ("AUS", -25.3, 133.8), "bangladesh": ("BGD", 23.7, 90.4),
    "brazil": ("BRA", -14.2, -51.9), "burkina faso": ("BFA", 12.2, -1.5),
    "burundi": ("BDI", -3.4, 29.9), "cambodia": ("KHM", 12.6, 105.0),
    "cameroon": ("CMR", 7.4, 12.4), "central african republic": ("CAF", 6.6, 20.9),
    "chad": ("TCD", 15.5, 18.7), "chile": ("CHL", -35.7, -71.5),
    "china": ("CHN", 35.9, 104.2), "colombia": ("COL", 4.6, -74.3),
    "congo": ("COG", -4.0, 21.8), "democratic republic of the congo": ("COD", -4.0, 21.8),
    "costa rica": ("CRI", 9.7, -83.8), "cote d'ivoire": ("CIV", 7.5, -5.5),
    "ivory coast": ("CIV", 7.5, -5.5), "cuba": ("CUB", 21.5, -77.8),
    "djibouti": ("DJI", 11.8, 42.6), "dominican republic": ("DOM", 18.7, -70.2),
    "ecuador": ("ECU", -1.8, -78.2), "egypt": ("EGY", 26.8, 30.8),
    "el salvador": ("SLV", 13.8, -88.9), "ethiopia": ("ETH", 9.1, 40.5),
    "fiji": ("FJI", -17.7, 178.0), "france": ("FRA", 46.2, 2.2),
    "gabon": ("GAB", -0.8, 11.6), "germany": ("DEU", 51.2, 10.4),
    "ghana": ("GHA", 7.9, -1.0), "greece": ("GRC", 39.1, 21.8),
    "guatemala": ("GTM", 15.8, -90.2), "guinea": ("GIN", 9.9, -11.9),
    "haiti": ("HTI", 18.9, -72.3), "honduras": ("HND", 15.2, -86.2),
    "india": ("IND", 20.6, 79.0), "indonesia": ("IDN", -0.8, 113.9),
    "iran": ("IRN", 32.4, 53.7), "iraq": ("IRQ", 33.2, 43.7),
    "israel": ("ISR", 31.0, 34.9), "italy": ("ITA", 41.9, 12.6),
    "jamaica": ("JAM", 18.1, -77.3), "japan": ("JPN", 36.2, 138.3),
    "jordan": ("JOR", 30.6, 36.2), "kazakhstan": ("KAZ", 48.0, 66.9),
    "kenya": ("KEN", -0.02, 37.9), "kuwait": ("KWT", 29.3, 47.5),
    "laos": ("LAO", 19.9, 102.5), "lebanon": ("LBN", 33.9, 35.9),
    "liberia": ("LBR", 6.4, -9.4), "libya": ("LBY", 26.3, 17.2),
    "madagascar": ("MDG", -18.8, 46.9), "malawi": ("MWI", -13.3, 34.3),
    "malaysia": ("MYS", 4.2, 101.9), "mali": ("MLI", 17.6, -4.0),
    "mauritania": ("MRT", 21.0, -10.9), "mexico": ("MEX", 23.6, -102.6),
    "mongolia": ("MNG", 46.8, 103.8), "morocco": ("MAR", 31.8, -7.1),
    "mozambique": ("MOZ", -18.7, 35.5), "myanmar": ("MMR", 21.9, 95.9),
    "namibia": ("NAM", -22.6, 17.1), "nepal": ("NPL", 28.4, 84.1),
    "nicaragua": ("NIC", 12.9, -85.2), "niger": ("NER", 17.6, 8.1),
    "nigeria": ("NGA", 9.1, 8.7), "north korea": ("PRK", 40.3, 127.5),
    "oman": ("OMN", 21.5, 55.9), "pakistan": ("PAK", 30.4, 69.3),
    "panama": ("PAN", 8.5, -80.8), "papua new guinea": ("PNG", -6.3, 143.9),
    "paraguay": ("PRY", -23.4, -58.4), "peru": ("PER", -9.2, -75.0),
    "philippines": ("PHL", 12.9, 122.0), "poland": ("POL", 51.9, 19.1),
    "portugal": ("PRT", 39.4, -8.2), "qatar": ("QAT", 25.4, 51.2),
    "romania": ("ROU", 45.9, 24.9), "russia": ("RUS", 61.5, 105.3),
    "rwanda": ("RWA", -2.0, 29.9), "saudi arabia": ("SAU", 23.9, 45.1),
    "senegal": ("SEN", 14.5, -14.5), "sierra leone": ("SLE", 8.5, -11.8),
    "singapore": ("SGP", 1.4, 103.8), "somalia": ("SOM", 5.2, 46.2),
    "south africa": ("ZAF", -30.6, 22.9), "south korea": ("KOR", 35.9, 127.8),
    "south sudan": ("SSD", 6.9, 31.3), "spain": ("ESP", 40.5, -3.7),
    "sri lanka": ("LKA", 7.9, 80.8), "sudan": ("SDN", 12.9, 30.2),
    "suriname": ("SUR", 3.9, -56.0), "sweden": ("SWE", 60.1, 18.6),
    "switzerland": ("CHE", 46.8, 8.2), "syria": ("SYR", 34.8, 38.0),
    "taiwan": ("TWN", 23.7, 121.0), "tanzania": ("TZA", -6.4, 34.9),
    "thailand": ("THA", 15.9, 100.9), "togo": ("TGO", 8.6, 1.2),
    "trinidad and tobago": ("TTO", 10.7, -61.2), "tunisia": ("TUN", 33.9, 9.5),
    "turkey": ("TUR", 38.9, 35.2), "uganda": ("UGA", 1.4, 32.3),
    "ukraine": ("UKR", 48.4, 31.2), "united arab emirates": ("ARE", 23.4, 53.8),
    "united kingdom": ("GBR", 55.4, -3.4), "united states": ("USA", 37.1, -95.7),
    "uruguay": ("URY", -32.5, -55.8), "uzbekistan": ("UZB", 41.4, 64.6),
    "venezuela": ("VEN", 6.4, -66.6), "vietnam": ("VNM", 14.1, 108.3),
    "yemen": ("YEM", 15.6, 48.5), "zambia": ("ZMB", -13.1, 28.6),
    "zimbabwe": ("ZWE", -19.0, 29.2),
    " cabo verde": ("CPV", 16.5, -23.0), "cape verde": ("CPV", 16.5, -23.0),
    "cabo verde": ("CPV", 16.5, -23.0),
}


class WHODONCollector:
    SOURCE = SourceType.WHO_DON
    API_URL = "https://www.who.int/api/news/diseaseoutbreaknews"

    def __init__(self, cache_dir: str = "data/cache"):
        import requests
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "GlobalEpidemicTracker/1.0"})
        self.cache_dir = cache_dir

    def collect(self, max_pages: int = 10) -> list[OutbreakReport]:
        all_items = self._fetch_all(max_pages)
        reports = []
        for item in all_items:
            parsed = self._parse_item(item)
            if parsed:
                reports.append(parsed)
        return reports

    def _fetch_all(self, max_pages: int) -> list[dict]:
        import requests
        all_items = []
        for page in range(max_pages):
            params = {"$orderby": "PublicationDate desc", "$top": 50, "$skip": page * 50}
            try:
                resp = requests.get(self.API_URL, params=params, timeout=30)
                data = resp.json()
                items = data.get("value", [])
                if not items:
                    break
                all_items.extend(items)
                if len(items) < 50:
                    break
            except Exception:
                break
        return all_items

    def _parse_item(self, item: dict) -> OutbreakReport | None:
        title = item.get("Title", "")
        summary = item.get("Summary", "")
        url_name = item.get("UrlName", "")
        pub_date = item.get("PublicationDate", "")

        disease = self._extract_disease(title)
        if not disease:
            return None
        if disease in ("Hurricane", "Guillain", "Mass Bromide Poisoning", "International food safety event"):
            return None

        countries = self._extract_countries(f"{title} {summary}")
        cases, deaths, suspected = self._extract_counts(summary)

        if deaths > 0 and cases == 0:
            cases = deaths
        if deaths > cases and cases > 0:
            deaths = cases

        date_reported = datetime.utcnow().date()
        if pub_date:
            try:
                date_reported = datetime.fromisoformat(pub_date.replace("Z", "+00:00")).date()
            except (ValueError, AttributeError):
                pass

        h2h = bool(re.search(r"person[\s-]*to[\s-]*person|human[\s-]*to[\s-]*human", summary, re.I))

        if not countries:
            countries = [("Multi-country", "MUL", 0.0, 0.0)]

        reports = []
        for name, iso3, lat, lon in countries:
            reports.append(OutbreakReport(
                outbreak_id=url_name or f"{iso3}_{disease}_{date_reported}",
                disease=disease,
                location=name,
                country=iso3,
                country_iso3=iso3,
                latitude=lat,
                longitude=lon,
                cases=cases,
                deaths=deaths,
                cases_suspected=suspected,
                severity=self._calc_severity(cases, deaths, h2h),
                status="active",
                description=summary[:500],
                source=self.SOURCE,
                source_url=f"https://www.who.int/emergencies/disease-outbreak-news/{url_name}" if url_name else "",
                date_reported=date_reported,
                h2h_transmission=h2h,
                travel_associated=bool(re.search(r"cruise\s*ship|travel|imported", summary, re.I)),
                confidence="high" if cases > 0 else "pending",
            ))
        return reports[0] if reports else None

    def _extract_disease(self, title: str) -> str:
        title_lower = title.lower()
        for keyword, canonical in sorted(DISEASE_ALIASES.items(), key=lambda x: -len(x[0])):
            if keyword in title_lower:
                return canonical
        parts = re.split(r"\s*[-–—:]\s*", title)
        candidate = parts[0].strip()
        if len(candidate) < 50 and not any(c.isdigit() for c in candidate):
            return candidate
        return ""

    def _extract_countries(self, text: str) -> list[tuple[str, str, float, float]]:
        # For Multi-country/Global DONs, return single entry
        text_lower = text.lower()
        if any(kw in text_lower for kw in ['multi-country', 'global situation', 'global update', 'regional']):
            return [("Multi-country", "MUL", 0.0, 0.0)]
        found = []
        for keyword, (iso3, lat, lon) in COUNTRY_COORDS.items():
            if keyword in text_lower:
                name = keyword.title()
                found.append((name, iso3, lat, lon))
        return found

    def _extract_counts(self, text: str) -> tuple[int, int, int]:
        cases, deaths, suspected = 0, 0, 0

        # Search first 2 sentences for outbreak-specific numbers
        sentences = re.split(r'(?<=[.!?])\s+', text)
        context = ' '.join(sentences[:2]) if len(sentences) >= 2 else text

        # Pattern: "a total of X cases" (most reliable)
        m = re.search(r"a\s+total\s+of\s+(\d[\d\s,]+)\s+(?:[\w/()]+\s+)*?cases?", context, re.I)
        if m:
            cases = self._word_to_num(m.group(1).strip().replace(",","").replace(" ",""))

        # Pattern: "X confirmed cases"
        if cases == 0:
            m = re.search(r"(\d[\d,]*)\s+(?:confirmed|suspected)\s+(?:\w+\s+)?cases?", text, re.I)
            if m:
                cases = self._word_to_num(m.group(1).replace(",",""))

        # Pattern: word number + cases: "seven cases", "eight cases"
        if cases == 0:
            # Pattern: "one/two/three confirmed case(s)" or "a case of"
            m = re.search(r"(\w+)\s+(?:confirmed\s+|suspected\s+|laboratory[- ]confirmed\s+)?cases?\s*[,(.:]", text, re.I)
            if m:
                n = self._word_to_num(m.group(1))
                if n > 0:
                    cases = n

        # Pattern: "the Nth case" or "X human cases"
        if cases == 0:
            m = re.search(r"(\d+)(?:st|nd|rd|th)\s+(?:confirmed\s+)?(?:human\s+)?case", text, re.I)
            if m:
                cases = int(m.group(1))

        # Deaths: "including X deaths"
        m = re.search(r"including\s+(\w+|\d[\d,]*)\s+deaths?", text, re.I)
        if m:
            deaths = self._word_to_num(m.group(1).strip().replace(",",""))

        # Deaths: "X deaths"
        if deaths == 0:
            m = re.search(r"(\d[\d,]*)\s+deaths?", text, re.I)
            if m:
                deaths = self._word_to_num(m.group(1).replace(",",""))

        # Deaths: word number
        if deaths == 0:
            m = re.search(r"(\w+)\s+deaths?\s*[,(.]", text, re.I)
            if m:
                n = self._word_to_num(m.group(1))
                if n > 0:
                    deaths = n

        # Suspected
        m = re.search(r"(\d[\d,]*)\s+suspected", text, re.I)
        if m:
            suspected = int(m.group(1).replace(",",""))

        # Sanity: deaths cannot exceed cases
        if deaths > cases and cases > 0:
            deaths = cases

        return cases, deaths, suspected

    def _word_to_num(self, w: str) -> int:
        m = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10,
             "eleven":11,"twelve":12,"thirteen":13,"fourteen":14,"fifteen":15,"sixteen":16,"seventeen":17,
             "eighteen":18,"nineteen":19,"twenty":20,"thirty":30,"forty":40,"fifty":50}
        if w.replace(",", "").isdigit():
            return int(w.replace(",", ""))
        return m.get(w.lower(), 0)

    def _calc_severity(self, cases: int, deaths: int, h2h: bool) -> Severity:
        if h2h and cases > 5:
            return Severity.VERY_HIGH
        cfr = deaths / cases if cases > 0 else 0
        if cfr > 0.25 or cases > 1000:
            return Severity.VERY_HIGH
        if cfr > 0.10 or cases > 100:
            return Severity.HIGH
        if cases > 10:
            return Severity.MODERATE
        return Severity.LOW
