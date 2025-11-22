from src.tools.custom_scraper import CustomScraper

# Test the scraper with a real URL
scraper = CustomScraper()

# Wikipedia is good for testing (public, allows scraping)
test_url = "https://en.wikipedia.org/wiki/Artificial_intelligence"

print("Testing CustomScraper...")
print(f"Fetching: {test_url}\n")

text = scraper.fetch_text(test_url)

if text:
    print("✅ SUCCESS! Scraped content:")
    print("="*60)
    print(text[:500])  # First 500 characters
    print("...")
    print(f"\nTotal length: {len(text)} characters")
else:
    print("❌ Failed to scrape content")