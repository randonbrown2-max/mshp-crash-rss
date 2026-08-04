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
        
        # FIX: Ensure this line stays on a single line!
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
