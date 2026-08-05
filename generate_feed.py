import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin
import re

# Base URL used to resolve relative links safely
BASE_MSHP_URL = "https://www.mshp.dps.mo.gov/HP68/"

# Target Counties (South-Central Missouri)
TARGET_COUNTIES = [
    "TEXAS", "PHELPS", "DENT", "SHANNON", 
    "HOWELL", "DOUGLAS", "WRIGHT", "LACLEDE", "PULASKI"
]

# Generate endpoints per county using MSHP's sCounty query parameter
SEARCH_URLS = [
    f"https://www.mshp.dps.mo.gov/HP68/SearchAction?sCounty={county}"
    for county in TARGET_COUNTIES
]

def parse_mshp_date(date_str):
    """Parses MSHP date strings to UTC datetime."""
    try:
        clean_str = re.sub(r'\s+', ' ', date_str).strip()
        dt = datetime.strptime(clean_str, "%m/%d/%Y %I:%M%p")
        # Central Time Offset (-5 Daylight / -6 Standard)
        return dt.replace(tzinfo=timezone(timedelta(hours=-5)))
    except Exception:
        return datetime.now(timezone.utc)

def fetch_crash_reports():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    reports = []
    seen_ids = set()
    
    # MSHP retains online crash reports for roughly 29 days
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
                    
                    # Skip table header rows
                    if "Report" in text_content[0] or "Crash County" in text_content:
                        continue

                    report_id = text_content[0]
                    date_val = text_content[6]
                    time_val = text_content[7] if len(text_content) > 7 else ""
                    date_str = f"{date_val} {time_val}".strip()
                    parsed_dt = parse_mshp_date(date_str)

                    # 29-Day Cutoff Filter
                    if parsed_dt < cutoff_date:
                        continue

                    county = text_content[8].upper()
                    location = text_content[9]

                    # Deduplicate by Report ID + County (handles multi-person crash rows)
                    dedup_key = f"{report_id}-{county}"
                    if dedup_key in seen_ids:
                        continue
                    seen_ids.add(dedup_key)

                    # Extract relative or full report links
                    link = row.find("a")
                    if link and "href" in link.attrs:
                        report_url = urljoin(BASE_MSHP_URL, link["href"])
                    else:
                        report_url = url

                    reports.append({
                        "id": report_id,
                        "date_str": date_str,
                        "parsed_date": parsed_dt,
                        "county": county,
                        "location": location,
                        "url": report_url
                    })
                
    return reports

def generate_rss(reports):
    fg = FeedGenerator()
    fg.id("https://www.mshp.dps.mo.gov/HP68/search.jsp")
    fg.title("Texas County & South-Central MO Crash Reports")
    fg.author({'name': 'MSHP RSS Generator'})
    fg.link(href="https://www.mshp.dps.mo.gov/HP68/search.jsp", rel='alternate')
    fg.description("Automated RSS feed for Texas County and surrounding Missouri counties.")
    fg.language("en")

    # Sort reports newest first
    reports.sort(key=lambda x: x['parsed_date'], reverse=True)

    for item in reports:
        fe = fg.add_entry()
        fe.id(item["url"])
        fe.title(f"Crash Report #{item['id']} - {item['county']} County")
        fe.link(href=item["url"])
        fe.pubDate(item['parsed_date'])
        
        formatted_description = (
            f"County: {item['county']}\n\n"
            f"Date/Time: {item['date_str']}\n\n"
            f"Location: {item['location']}"
        )
        fe.description(formatted_description)

    fg.rss_file("index.html")
    fg.rss_file("feed.xml")

if __name__ == "__main__":
    reports = fetch_crash_reports()
    generate_rss(reports)
    print(f"Generated clean RSS feed with {len(reports)} items.")
