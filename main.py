from helpers.handler import Scrapper
from config.configurations import Config as config

from apscheduler.schedulers.background import BackgroundScheduler
import time

from helpers.state import load_state, save_state
import chromedriver_autoinstaller

scheduler = BackgroundScheduler()

chromedriver_autoinstaller.install(cwd=True) 

def main():
    
    state = load_state()
    resuming = bool(state["main_url"])
    # Ensure CSV file is initialized with headers once

    for url in config["urls"]:
        if resuming:
            # If resuming, skip URLs until we reach the last saved URL
            if url == state["main_url"]:
                resuming = False  # Stop skipping once we find the last URL
            else:
                continue
        try:
            # Initialize Scrapper for the given URL
            scraper = Scrapper(url)
            # scraper.addCsvFileFieldnames(field_names)  # Write headers once

            print("Visiting URL:", url)
            content = scraper.get_page_content()
            # scraper.addCsvFileFieldnames()
                        
            # # Retrieve subcategory URLs and then individual item data
            subcategory_urls = scraper.getSubcategoriesUrls(content)
            scraper.getProductUrls(subcategory_urls)
            
            # Clean up driver resources after each URL
            # Exit loop if successful
        
            scraper.state["visited_urls"] = url
            save_state(scraper.state)
        except Exception as e:
            print(f"Error processing URL {url}: {e}")
            
            # Add the failed URL to state and save
            if url not in state["failed_urls"]:
                state["failed_urls"].append(url)
            save_state(state)
        finally:
            # Delay to avoid overloading the server
            time.sleep(config["sleepTime"])
            

# main()