import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone

SEARCH_URL = "https://www.mshp.dps.mo.gov/HP68/SearchAction?searchTroop=G"

# Texas County + surrounding area
TARGET_COUNTIES = {
    "TEXAS", "PHELPS", "DENT", "SHANNON", 
    "HOWELL", "DOUGLAS", "WRIGHT", "LACLEDE", "PULASKI"
}

def fetch_crash_reports():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    response = requests.get(SEARCH_URL, headers=headers, timeout=15)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")
    reports = []

    # Target the MSHP results table
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            
            # MSHP table typically has 10-12 columns per row
            if len(cols) >= 9:
                text_content = [c.get_text(strip=True) for c in cols]
                
                # Header row filter
                if "Report" in text_content[0] or "Crash County" in text_content:
                    continue

                # Column mapping for MSHP SearchAction:
                # 0: Report ID, 6: Date, 7: Time, 8: County, 9: Location
                report_id = text_content[0]
                date_str = f"{text_content[6]} {text_content[7]}" if len(text_content) > 7 else text_content[6]
                county = text_content[8].upper() if len(text_content) > 8 else ""
                location = text_content[9] if len(text_content) > 9 else "N/A"

                # Filter by targeted counties
                if any(target in county for target in TARGET_COUNTIES):
                    link = row.find("a")
                    report_url = "https://www.mshp.dps.mo.gov/HP68/" + link["href"] if link and "href" in link.attrs else SEARCH_URL

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
    fg.id(SEARCH_URL)
    fg.title("Texas County & Area Crash Reports (MSHP)")
    fg.author({'name': 'MSHP RSS Generator'})
    fg.link(href=SEARCH_URL, rel='alternate')
    fg.description("Automated RSS feed for Texas County and surrounding Missouri counties.")
    fg.language("en")

    for item in reports:
        fe = fg.add_entry()
        fe.id(item["url"] if item["url"] != SEARCH_URL else item["id"])
        fe.title(f"Crash Report #{item['id']} - {item['county']} County")
        fe.link(href=item["url"])
        fe.description(
            f"<b>County:</b> {item['county']}<br>"
            f"<b>Date/Time:</b> {item['date']}<br>"
            f"<b>Location:</b> {item['location']}"
        )
        fe.pubDate(datetime.now(timezone.utc))

    # Output files
    fg.rss_file("index.html")
    fg.rss_file("feed.xml")

if __name__ == "__main__":
    reports = fetch_crash_reports()
    generate_rss(reports)
    print(f"Generated RSS feed with {len(reports)} items.")
