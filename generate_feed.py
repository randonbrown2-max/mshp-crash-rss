from datetime import datetime, timezone

def parse_mshp_date(date_str):
    """
    Converts MSHP date/time string (e.g. '08/02/2026 12:45AM') 
    into a timezone-aware datetime object for RSS pubDate sorting.
    """
    try:
        # Standard MSHP format: MM/DD/YYYY I:MMPM
        dt = datetime.strptime(date_str, "%m/%d/%Y %I:%M%p")
        # Assuming US Central timezone (-05:00/CDT or -06:00/CST)
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        # Fallback if time format varies
        return datetime.now(timezone.utc)

def generate_rss(reports):
    fg = FeedGenerator()
    fg.id("https://www.mshp.dps.mo.gov/HP68/search.jsp")
    fg.title("Texas County & Area Crash Reports (MSHP)")
    fg.author({'name': 'MSHP RSS Generator'})
    fg.link(href="https://www.mshp.dps.mo.gov/HP68/search.jsp", rel='alternate')
    fg.description("Automated RSS feed for Texas County and surrounding Missouri counties.")
    fg.language("en")

    # SORT REPORTS: Newest crashes at the top of the feed
    reports.sort(key=lambda x: parse_mshp_date(x['date']), reverse=True)

    for item in reports:
        fe = fg.add_entry()
        fe.id(item["url"] if item["url"] != "https://www.mshp.dps.mo.gov/HP68/search.jsp" else item["id"])
        fe.title(f"Crash Report #{item['id']} - {item['county']} County")
        fe.link(href=item["url"])
        
        # Parse actual date for RSS pubDate tag
        pub_dt = parse_mshp_date(item['date'])
        fe.pubDate(pub_dt)

        bullet_description = (
            "<ul>"
            f"<li><b>County:</b> {item['county']}</li>"
            f"<li><b>Date/Time:</b> {item['date']}</li>"
            f"<li><b>Location:</b> {item['location']}</li>"
            "</ul>"
        )
        fe.description(bullet_description)

    fg.rss_file("index.html")
    fg.rss_file("feed.xml")
