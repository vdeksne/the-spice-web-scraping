from fastapi import FastAPI, HTTPException, Query # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from bs4 import BeautifulSoup # type: ignore
import requests # type: ignore
import csv
from io import StringIO
import re
import logging
from urllib.parse import urljoin, unquote
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import platform
import os
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_category_links(soup):
    """Extract category links with class 'dator'"""
    links = []
    for link in soup.find_all('a', class_='dator'):
        if link.get('href'):
            links.append(link['href'])
            logger.info(f"Found category link: {link['href']}")
    return links

def get_subcategory_links(soup):
    """Extract subcategory links from divs with class 'astota-uzraksts'"""
    links = []
    for div in soup.find_all('div', class_='astota-uzraksts'):
        link = div.find('a')
        if link and link.get('href'):
            links.append(link['href'])
            logger.info(f"Found subcategory link: {link['href']}")
    return links

def get_product_links(soup):
    """Extract product links from img tags with class 'img-responsive'"""
    links = []
    for img in soup.find_all('img', class_='img-responsive'):
        parent_link = img.find_parent('a')
        if parent_link and parent_link.get('href'):
            links.append(parent_link['href'])
            logger.info(f"Found product link: {parent_link['href']}")
    return links

def extract_price_per_kg(price: float, weight_text: str) -> str:
    try:
        # Extract weight value and unit
        weight_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(kg|g)', weight_text.lower())
        if not weight_match:
            return "N/A"
            
        value = float(weight_match.group(1).replace(',', '.'))
        unit = weight_match.group(2)
        
        # Convert to kg if in grams
        weight_kg = value if unit == 'kg' else value / 1000
        
        if weight_kg > 0:
            price_per_kg = price / weight_kg
            return f"{price_per_kg:.2f} €/kg"
        return "N/A"
    except Exception as e:
        logger.error(f"Error extracting price per kg: {e}")
        return "N/A"

def scrape_product_page(url, base_url):
    """Scrape individual product page"""
    try:
        logger.info(f"Scraping product page: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Make sure URL is absolute
        full_url = urljoin(base_url, url)
        response = requests.get(full_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find product name (h2 with class 'title')
        name = None
        name_elem = soup.find('h2', class_='title')
        if name_elem:
            name = name_elem.text.strip()
            logger.info(f"Found product name: {name}")
        
        # Find price (h2 with class 'price')
        price = None
        price_text = None
        price_elem = soup.find('h2', class_='price')
        if price_elem:
            price_text = price_elem.text.strip()
            # Extract numeric price value
            price_match = re.search(r'(\d+[.,]\d+)', price_text)
            if price_match:
                price = float(price_match.group(1).replace(',', '.'))
            logger.info(f"Found price: {price_text}")
        
        # Find weight options (labels with class 'radio')
        weights = []
        weight_elems = soup.find_all('label', class_='radio')
        for elem in weight_elems:
            weight_text = elem.text.strip()
            if weight_text:
                weights.append(weight_text)
                logger.info(f"Found weight option: {weight_text}")
        
        if not weights:
            weights = ["1 kg"]  # Default weight if none found
        
        # Create product entries for each weight option
        products = []
        for weight in weights:
            if name and price:
                price_per_kg = extract_price_per_kg(price, weight)
                products.append({
                    "name": name,
                    "price": price_text,
                    "weight": weight,
                    "price_per_kg": price_per_kg
                })
        
        return products
    
    except Exception as e:
        logger.error(f"Error scraping product page: {e}")
        return []

def crawl_website(base_url):
    """Crawl the website following the specified navigation pattern"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Get main page
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        all_products = []
        product_count = 0
        
        # Get category links (a.dator)
        category_links = get_category_links(soup)
        
        for category_url in category_links:
            if product_count >= 10000:  # Limit to 10 results
                break
                
            category_full_url = urljoin(base_url, category_url)
            response = requests.get(category_full_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get subcategory links (div.astota-uzraksts)
            subcategory_links = get_subcategory_links(soup)
            
            for subcategory_url in subcategory_links:
                if product_count >= 10000:  # Limit to 10 results
                    break
                    
                subcategory_full_url = urljoin(base_url, subcategory_url)
                response = requests.get(subcategory_full_url, headers=headers)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Get product links (img.img-responsive)
                product_links = get_product_links(soup)
                
                for product_url in product_links:
                    if product_count >= 10000:  # Limit to 10 results
                        break
                        
                    products = scrape_product_page(product_url, base_url)
                    all_products.extend(products)
                    product_count += len(products)
                    
                    # Add a small delay between requests
                    time.sleep(1)
        
        return all_products[:10000]  # Ensure we return max 10 results
        
    except Exception as e:
        logger.error(f"Error crawling website: {e}")
        return []

def get_chrome_driver():
    try:
        logger.info("Setting up Chrome WebDriver...")
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # For Mac ARM64
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            logger.info("Detected Mac ARM64 system")
            chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            # Use the system ChromeDriver
            driver_path = "/opt/homebrew/bin/chromedriver"  # Updated path for Homebrew installation
            if not os.path.exists(driver_path):
                logger.error(f"ChromeDriver not found at {driver_path}")
                raise Exception(f"ChromeDriver not found at {driver_path}")
        else:
            driver_path = "chromedriver"
        
        logger.info(f"Using ChromeDriver at: {driver_path}")
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("Chrome WebDriver setup successful")
        return driver
    except Exception as e:
        logger.error(f"Error setting up Chrome WebDriver: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def scrape_garsvielas_page(url: str, limit: int = 10):
    logger.info(f"Scraping garsvielas.lv page: {url}")
    driver = None
    try:
        driver = get_chrome_driver()
        logger.info("Loading page...")
        driver.get(url)
        
        # Wait for the page to load
        logger.info("Waiting for page to load...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Get the page source after JavaScript execution
        logger.info("Getting page source...")
        page_source = driver.page_source
        logger.info("Page HTML structure:")
        logger.info(page_source[:1000])  # Log first 1000 chars for debugging
        
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Try different selectors for product items
        selectors = [
            "div.product-item-info",
            "div.product-item",
            "div.product",
            "div.item",
            "li.product-item",
            "div.product-item-wrapper",
            "div[data-testid='product-item']",
            "div[data-testid='product']",
            "div[class*='product']",  # Any div with 'product' in class name
            "div[class*='item']"      # Any div with 'item' in class name
        ]
        
        products = []
        for selector in selectors:
            logger.info(f"Trying selector: {selector}")
            items = soup.select(selector)
            logger.info(f"Found {len(items)} items with selector {selector}")
            
            if items:
                for item in items[:limit]:
                    try:
                        # Try different selectors for product name
                        name = None
                        name_selectors = [
                            "h3.product-name",
                            "div.product-name",
                            "span.product-name",
                            "h2.product-title",
                            "div.product-title",
                            "[data-testid='product-name']",
                            "[data-testid='product-title']",
                            "h3", "h2", "h4",  # Try any heading
                            "span[class*='name']",  # Any span with 'name' in class
                            "div[class*='name']"    # Any div with 'name' in class
                        ]
                        for name_selector in name_selectors:
                            name_elem = item.select_one(name_selector)
                            if name_elem:
                                name = name_elem.text.strip()
                                break
                        
                        if not name:
                            continue
                            
                        # Try different selectors for price
                        price = None
                        price_selectors = [
                            "span.price",
                            "div.price",
                            "span.product-price",
                            "div.product-price",
                            "[data-testid='product-price']",
                            "span[class*='price']",  # Any span with 'price' in class
                            "div[class*='price']"    # Any div with 'price' in class
                        ]
                        for price_selector in price_selectors:
                            price_elem = item.select_one(price_selector)
                            if price_elem:
                                price = price_elem.text.strip()
                                break
                        
                        if not price:
                            continue
                            
                        # Try different selectors for weight
                        weight = None
                        weight_selectors = [
                            "span.weight",
                            "div.weight",
                            "span.product-weight",
                            "div.product-weight",
                            "[data-testid='product-weight']",
                            "span[class*='weight']",  # Any span with 'weight' in class
                            "div[class*='weight']"    # Any div with 'weight' in class
                        ]
                        for weight_selector in weight_selectors:
                            weight_elem = item.select_one(weight_selector)
                            if weight_elem:
                                weight = weight_elem.text.strip()
                                break
                        
                        if not weight:
                            continue
                            
                        products.append({
                            "name": name,
                            "price": price,
                            "weight": weight
                        })
                        logger.info(f"Found product: {name} - {price} - {weight}")
                        
                    except Exception as e:
                        logger.error(f"Error processing product item: {str(e)}")
                        logger.error(traceback.format_exc())
                        continue
                
                if products:
                    break
        
        if not products:
            # Log all div elements with classes for debugging
            logger.info("All div elements with classes:")
            for div in soup.find_all('div', class_=True):
                logger.info(f"Div class: {div['class']}")
            
            logger.warning(f"No products found on page: {url}")
            raise HTTPException(status_code=404, detail="No products found")
            
        return products
        
    except Exception as e:
        logger.error(f"Error scraping garsvielas.lv page: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.error(f"Error closing Chrome WebDriver: {str(e)}")

@app.get("/scrape")
async def scrape_website(url: str = Query(..., description="URL to scrape"), format: str = Query("json", description="Response format (json or csv)")):
    try:
        logger.info(f"Starting scrape of website: {url}")
        
        # Determine URL type and handle accordingly
        if "safrans.lv" in url:
            if url == "https://www.safrans.lv":
                # Main website URL - do full crawl
                products = crawl_website(url)
            elif "garsvielas_un_garsaugi" in url:
                if url.count('/') >= 5:  # This is a product page URL
                    # Single product page
                    products = scrape_product_page(url, 'https://www.safrans.lv')
                else:
                    # This is a category page - get product links and scrape each one
                    logger.info(f"Scraping category page: {url}")
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    response = requests.get(url, headers=headers)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    product_links = get_product_links(soup)
                    if not product_links:
                        logger.warning(f"No product links found on category page: {url}")
                        raise HTTPException(status_code=404, detail="No product links found on this category page")
                    
                    products = []
                    for product_url in product_links[:10000]:  # Limit to 10 products
                        product_data = scrape_product_page(product_url, 'https://www.safrans.lv')
                        products.extend(product_data)
                        time.sleep(1)  # Be nice to the server
        elif "garsvielas.lv" in url:
            # Handle garsvielas.lv URLs
            products = scrape_garsvielas_page(url)
        else:
            raise HTTPException(status_code=400, detail="Invalid URL. Please provide a URL from safrans.lv or garsvielas.lv")
        
        if not products:
            raise HTTPException(status_code=404, detail="No product information could be found")
        
        logger.info(f"Successfully scraped {len(products)} products")
        
        if format.lower() == "csv":
            # Create CSV content
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["Product Name", "Price", "Weight", "Price per kg"])
            
            for product in products:
                writer.writerow([
                    product["name"],
                    product["price"],
                    product["weight"],
                    product.get("price_per_kg", "N/A")
                ])
            
            return {"csv_content": output.getvalue()}
        else:
            # Return JSON format
            return products
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        raise HTTPException(status_code=500, detail=f"Error making request: {str(e)}")
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error scraping website: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn # type: ignore
    uvicorn.run(app, host="0.0.0.0", port=8000)