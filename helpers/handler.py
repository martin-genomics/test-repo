import os
import time
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import TimeoutException
from selenium_stealth import stealth
from urllib.parse import urlparse
import json
import csv
from config.configurations import Config as config


class Scrapper:
    
    def __init__(self, url: str):
        self.csv_filename = "output.csv"
        self.fieldNames = ["name", "price", "description", "prices", "dimensions", 
                           "mechanicalProperties", "chemistryInformation", "weight_lineal_foot", "detail_url"]
        self.url = url
        self.driver = None
        self.driver2 = None
        self.driver3 = None
        # self.initialize_csv()  # Ensure CSV exists and headers are set up
        self.state = {
            "isLeft": False,''
            "main_url": url,
            "resume_page_url": "",
            "resume_product": "",
            "failed_urls": [],
            "visited_urls": []
        }

    def config(self):
        chrome_options = Options()
        capabilities = DesiredCapabilities.CHROME.copy()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        # chrome_options.add_argument('--disable-gpu')
        # chrome_options.add_argument('--disable-dev-shm-usage')
        # chrome_options.add_argument("start-maximized")
        return chrome_options

    # def initialize_csv(self):
    #         """Initialize CSV file if it doesn't already exist, and write headers."""
    #         if not os.path.isfile(self.csv_filename):
    #             with open(self.csv_filename, mode="w", newline="") as csv_file:
    #                 writer = csv.DictWriter(csv_file, fieldnames=self.fieldNames)
    #                 writer.writeheader()
                    
    def buildUrl(self, url: str, path: str):
        parsed_url = urlparse(url)
        return f"{parsed_url.scheme}://{parsed_url.hostname}{path}"

    def getSubcategoriesUrls(self, bs4_content):
        url_elements = bs4_content.find_all("a", class_="btn-primary view-all-link")
        return [self.buildUrl("https://www.onlinemetals.com/", el.get("href")) for el in url_elements if el.get("href")]

    def load_existing_products(self):
        """Load existing product URLs from CSV to avoid duplicates."""
        existing_products = set()
        try:
            with open(self.csv_filename, mode="r", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                # Use the product name or URL as a unique identifier
                for row in reader:
                    existing_products.add(row["detail_url"])  # or row["product_url"] if available
        except FileNotFoundError:
            # CSV file doesn't exist yet, so no duplicates to check
            pass
        return existing_products
    
    def getProductUrls(self, subcategories: list):
        for url in subcategories:
            print("Visiting subcategory: ", url)
            page_content = self.get_page_content(url, driver_number=2)
            self.state["resume_page_url"] = url
            with open("lastpage.txt", "+a") as f:
                f.write(url)
            product_urls = page_content.select(f"div.{config['classes']['singleItem']} a")
            nextPage = page_content.select_one('a[rel="next"][aria-label="Pagination right"]')
            self.getProductsDataAndSave(product_urls=product_urls)
            self.state["visited_urls"].append(url)
            if nextPage:
                url = nextPage.get("href")
                if url:
                    full_url = self.buildUrl("https://www.onlinemetals.com/", url)
                    print("Navigating to the next page.")
                    self.getProductUrls([full_url])
                    
        
    def getNextPageContent(self, url:str):
        '''
        Gets next page content and returns the source.
        '''
        page = self.get_page_content(url, driver_number=1)
        return page
        
    def getProductsDataAndSave(self, product_urls:list):
        '''
        Receives urls of products of a single page.\n
        Loops through them.\n
        Visits each product's page and collects the details.\n
        Collected Details:\n
            1. Name\n
            2. Description\n
            3. Prices\n
            4. Dimensions\n
            5. Mechanical Properties\n
            6. Chemistry Information\n
            7. Weight Lineal Foot\n
            8. Price\n
            
        Then, saves the information in a csv file.
        '''
        existing_products = self.load_existing_products()
        
        n = 1
        for element in product_urls:
            path = element.get("href")
            print("Working on ", len(product_urls))
            
            if path and self.buildUrl("https://www.onlinemetals.com/", path) not in existing_products: 
                product_url = self.buildUrl("https://www.onlinemetals.com/", path)
                print(f"Visiting product {n} of {len(product_urls)} url: {product_url}" )
                product_page = self.get_page_content(product_url, driver_number=3)
                product = {
                    "name": product_page.find("div", class_=config["classes"]["productClasses"]["title"]).text if product_page.find("div", class_=config["classes"]["productClasses"]["title"]) else None,
                    "description": product_page.select_one("div.overview-text").text if product_page.select_one("div.overview-text") else None,
                    "prices": self.getPrices(product_page),
                    "dimensions": self.getTableData(product_page, "table.dimension-table-row tbody tr", "dimensions"),
                    "mechanicalProperties": self.getTableData(product_page, "table.mechanical__table tbody tr", "mechanicalProperties"),
                    "chemistryInformation": self.getTableData(product_page, "table.chemistry__table tbody tr", "chemistryInformation"),
                    "weight_lineal_foot": product_page.select_one("td.pound-weight").text if product_page.select_one("td.pound-weight") else None,
                    "price": product_page.select_one("div.get-product-price").text if product_page.select_one("div.get-product-price") else None,
                    "detail_url": product_url
                }
                
                print("Data collected!")
                # Check if the product name or URL is in existing_products
                if product["detail_url"] not in existing_products:
                    print("Saving into csv")
                    self.addToCsv(product)
                    print("Data has been saved in csv")
                    # Add the new product to the set to avoid duplicates in the same session
                    existing_products.add(product["detail_url"])
                else:
                    print(f"Skipping duplicate product: {product['detail_url']}")
                    print("Duplicate has been ignored")
                n = n + 1
            else:
                print(f"Skipping duplicate product {n}: {self.buildUrl("https://www.onlinemetals.com/", path)}")
                print("Duplicate has been ignored")
                n = n + 1
                
            
                
                    
    def getTableData(self, product_page, selector: str, getFor: str):
        ''''
        Gets table based data from the product detail page.
        All the data represented by table
        '''
        specifications = []
        for row in product_page.select(selector):
            cells = row.find_all('td')
            if len(cells) == 2:
                name, specification = cells[0].get_text(strip=True), cells[1].get_text(strip=True)
                spec_obj = {}
                if getFor == "dimensions":
                    spec_obj = {"name": name, "specification": specification}
                elif getFor == "mechanicalProperties":
                    spec_obj = {"property": name, "value": specification}
                elif getFor == "chemistryInformation":
                    spec_obj = {"element": name, "percentage": specification}
                specifications.append(spec_obj)
        return specifications

    def getPrices(self, product_page):
        return [
            {
                "size": box.select_one('.size').get_text(strip=True) if box.select_one('.size') else None,
                "price": box.select_one('.price').get_text(strip=True) if box.select_one('.price') else None,
                "weight": box.select_one('.weight').get_text(strip=True) if box.select_one('.weight') else None,
            }
            
            for box in product_page.select('div.length-box')
        ]

    def get_page_content(self, url=None, driver_number:int =1):
        current_url = url or self.url
        stealth_config = {
            "languages": ["en-US", "en"],
            "vendor": "Google Inc.",
            "platform": "Win32",
            "webgl_vendor": "Intel Inc.",
            "renderer": "Intel Iris OpenGL Engine",
            "fix_hairline": True
        }

        # Lazily initialize each driver as needed
        if driver_number == 1 and self.driver is None:
            self.driver = uc.Chrome(options=self.config())
            stealth(self.driver, **stealth_config)
        elif driver_number == 2 and self.driver2 is None:
            self.driver2 = uc.Chrome(options=self.config())
            stealth(self.driver2, **stealth_config)
        elif driver_number == 3 and self.driver3 is None:
            self.driver3 = uc.Chrome(options=self.config())
            stealth(self.driver3, **stealth_config)

        # Select the driver based on the driver_number parameter
        driver = self.driver if driver_number == 1 else self.driver2 if driver_number == 2 else self.driver3
        driver.get(current_url)
         # Wait for specific element to load
        try:
            # Wait for the specific <a> element with the class "btn-primary view-all-link" to appear4
            
            WebDriverWait(driver, 2).until((lambda d: d.execute_script("return document.readyState") == 'complete'))
            driver.execute_script("window.stop();")
            # Stop loading as soon as the element appears

            # Retrieve the page content after stopping further loading
            page_content = BeautifulSoup(driver.page_source, 'html.parser')
        except TimeoutException:
            print("Timeout: Element not found within the specified time.")
            page_content = None
        finally:
            # Close the driver after retrieving content or on timeout
            driver.quit()
            if driver_number == 1:
                self.driver = None
            elif driver_number == 2:
                self.driver2 = None
            elif driver_number == 3:
                self.driver3 = None
            print("Driver closed")

        return page_content
    


    def addCsvFileFieldnames(self):
        with open(self.csv_filename, mode="w", newline="") as cvs_file:
            writer = csv.DictWriter(cvs_file, fieldnames=self.fieldNames)
            writer.writeheader()

    def addToCsv(self, product: dict):
        with open(self.csv_filename, mode="a", newline="") as cvs_file:
            writer = csv.DictWriter(cvs_file, fieldnames=self.fieldNames)
            writer.writerow(product)

