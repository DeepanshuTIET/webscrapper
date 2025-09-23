"""
Just some examples of how to use the web scraper
Feel free to modify these for your own needs
"""

from retriving_html import WebScraperToStorage

def example_tcs_scraping():
    """Let's grab some TCS financial data"""
    print("=== Example 1: TCS Financial Data ===")
    url = "https://www.screener.in/company/TCS/consolidated/"
    scraper = WebScraperToStorage(url, "TCS")
    scraper.run_complete_pipeline()

def example_reliance_scraping():
    """Now let's try Reliance - always interesting to compare"""
    print("\n=== Example 2: Reliance Financial Data ===")
    url = "https://www.screener.in/company/RELIANCE/consolidated/"
    scraper = WebScraperToStorage(url, "RELIANCE")
    scraper.run_complete_pipeline()

def example_custom_scraping():
    """This shows how to scrape any website with tables"""
    print("\n=== Example 3: Custom Website ===")
    # Just change this URL to whatever site you want to scrape
    url = "https://example.com/tables"  # Put your actual URL here
    scraper = WebScraperToStorage(url, "CUSTOM_SITE")
    
    # Sometimes you want more control over the process:
    if scraper.fetch_html():
        if scraper.extract_tables():
            print(f"Found {len(scraper.tables)} tables")
            
            # Maybe you only want certain formats
            scraper.save_to_csv()      # Everyone loves CSVs
            scraper.save_to_sqlite()   # For when I need to query stuff
            # scraper.save_to_duckdb() # Skip this if you don't need it
            
            # Take a peek at what we got
            for i, table_info in enumerate(scraper.tables):
                df = table_info['dataframe']
                print(f"Table {i} preview:")
                print(df.head())
                print()

if __name__ == "__main__":
    # Let's start with TCS
    example_tcs_scraping()
    
    # Uncomment these if you want to try the others:
    # example_reliance_scraping()
    # example_custom_scraping()
