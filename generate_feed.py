import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin
import re

BASE_MSHP_URL = "https://www.mshp.dps.mo.gov/HP68/"

SEARCH_URLS = [
    "https://www.mshp.dps.mo.gov/HP68/SearchAction?searchTroop=G",
    "https://www.mshp.dps.mo.gov/HP68/SearchAction?searchTroop=I"
]

TARGET_COUNTIES = {
    "TEXAS", "PHELPS", "DENT", "SHANNON", 
    "HOWELL", "DOUGLAS", "WRIGHT", "LACLEDE", "PULASKI"
}

def parse_mshp_date(date_str):
    """Parses MSHP date strings to UTC datetime."""
    try:
        clean_str = re.sub(r'\s+', ' ', date_str).strip()
        dt = datetime.strptime(clean_str, "%m/%d/%Y %I:%M%p")
        # Central Time Offset (-5 daylight / -6 standard)
        return dt.replace(tzinfo=timezone(timedelta(hours=-5)))
    except Exception:
        return datetime.now(timezone.utc)

def fetch_crash_reports():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    reports = []
    seen_ids = set()
    
    # 29-Day Cutoff Date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=29)

    for url in SEARCH_URLS:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
        except Exception as e:
            print(f"Warning: Could not fetch {url} - {e}")
            continue
        
        soup = BeautifulSoup(response.text, "html.parser")
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                
                if len(cols) >= 10:
                    text_content = [c.get_text(strip=True) for c in cols]
                    
                    if "Report" in text_content[0] or "Crash County" in text_content:
                        continue

                    report_id = text_content[0]
                    date_val = text_content[6]
                    time_val = text_content[7] if len(text_content) > 7 else ""
                    date_str = f"{date_val} {time_val}".strip()
                    parsed_dt = parse_mshp_date(date_str)

                    # Skip items older than 29 days
                    if parsed_dt < cutoff_date:
                        continue

                    county = text_content[8].upper()
                    location = text_content[9]

                    if any(target in county for target in TARGET_COUNTIES):
                        dedup_key = f"{report_id}-{county}"
                        if dedup_key in seen_ids:
                            continue
                        seen_ids.add(dedup_key)

                        link = row.find("a")
                        report_url = urljoin(BASE_MSHP_URL, link["href"]) if link and "href" in link.attrs else url

                        reports.append({
                            "id": report_id,
                            "date_str": date_str,
                            "parsed_date": parsed_dt,
                            "county": county,
                            "location": location,
                            "url": report_url
                        })
                
    return reports
