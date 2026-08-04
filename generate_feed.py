import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone

SEARCH_URL = "https://www.mshp.dps.mo.gov/HP68/SearchAction?searchTroop=G"

# Texas County + surrounding counties
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

    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 4:
                text_content = [c.get_text(strip=True) for c in cols]
                
                if "Crash" in text_content[0] or "County" in text_content[0]:
                    continue

                county = text_content[2].strip().upper() if len(text_content) > 2 else ""

                if any(target in county for target in TARGET_COUNTIES):
                    link = row.find("a")
                    report_url = "https://www.mshp.dps.mo.gov/HP68/" + link["href"] if link and "href" in link.attrs else SEARCH_URL

                    reports.append({
                        "id": text_content[0],
                        "date": text_content[1] if len(text_content) > 1 else "N/A",
                        "county": text_content[2] if len(text_content) > 2 else "N/A",
                        "location": text_content[3] if len(text_content) > 3 else "N/A",
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

    # Writes RSS XML directly to index.html and feed.xml
    fg.rss_file("index.html")
    fg.rss_file("feed.xml")

if __name__ == "__main__":
    reports = fetch_crash_reports()
    generate_rss(reports)
    print(f"Generated RSS feed with {len(reports)} items.")
