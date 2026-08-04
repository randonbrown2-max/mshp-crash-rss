import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone

# Target endpoints for South-Central Missouri (Troop G & Troop I)
SEARCH_URLS = [
    "https://www.mshp.dps.mo.gov/HP68/SearchAction?searchTroop=G",
    "https://www.mshp.dps.mo.gov/HP68/SearchAction?searchTroop=I"
]

# Texas County + surrounding area
TARGET_COUNTIES = {
    "TEXAS", "PHELPS", "DENT", "SHANNON", 
    "HOWELL", "DOUGLAS", "WRIGHT", "LACLEDE", "PULASKI"
}

def parse_mshp_date(date_str):
    """Parses MSHP date/time strings for proper RSS sorting."""
    try:
        dt = datetime.strptime(date_str, "%m/%d/%Y %I:%M%p")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)

def fetch_crash_reports():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    reports = []
    seen_ids = set()

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
                    date_str = f"{text_content[6]} {text_content[7]}" if len(text_content) > 7 else text_content[6]
                    county = text_content[8].upper()
                    location = text_content[9]

                    if any(target in county for target in TARGET_COUNTIES):
                        dedup_key = f"{report_id}-{county}"
                        if dedup_key in seen_ids:
                            continue
                        seen_ids.add(dedup_key)

                        link = row.find("a")
                        report_url = "https://www.mshp.dps.mo.gov/HP68/" + link["href"] if link and "href" in link.attrs else url

                        reports.append({
                            "id": report_id,
                            "date": date_str,
                            "county": county,
                            "location": location,
                            "url": report_url
                        })
                
    return reports

def generate_rss(reports):
    fg = FeedGenerator()
    fg.id("https://www.mshp.dps.mo.gov/HP68/search.jsp")
    fg.title("Texas County & Area Crash Reports (MSHP)")
    fg.author({'name': 'MSHP RSS Generator'})
    fg.link(href="https://www.mshp.dps.mo.gov/HP68/search.jsp", rel='alternate')
    fg.description("Automated RSS feed for Texas County and surrounding Missouri counties.")
    fg.language("en")

    # Sort newest crashes first
    reports.sort(key=lambda x: parse_mshp_date(x['date']), reverse=True)

    for item in reports:
        fe = fg.add_entry()
        fe.id(item["url"] if item["url"] != "https://www.mshp.dps.mo.gov/HP68/search.jsp" else item["id"])
        fe.title(f"Crash Report #{item['id']} - {item['county']} County")
        fe.link(href=item["url"])
        fe.pubDate(parse_mshp_date(item['date']))
        
        bullet_description = (
            "<ul>"
            f"<li><b>County:</b> {item['county']}</li>"
            f"<li><b>Date/Time:</b> {item['date']}</li>"
            f"<li><b>Location:</b> {item['location']}</li>"
            "</ul>"
        )
        fe.description(bullet_description)

    # Force write XML files
    fg.rss_file("index.html")
    fg.rss_file("feed.xml")

if __name__ == "__main__":
    reports = fetch_crash_reports()
    generate_rss(reports)
    print(f"Generated RSS feed with {len(reports)} items.")
