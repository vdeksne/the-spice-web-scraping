from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import requests
import csv
from io import StringIO
import re
import logging
from urllib.parse import urljoin, unquote
import time

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

@app.get("/scrape")
async def scrape_website(url: str = Query(..., description="URL to scrape")):
    try:
        logger.info(f"Starting scrape of website: {url}")
        
        # Determine URL type and handle accordingly
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
        else:
            raise HTTPException(status_code=400, detail="Invalid URL. Please provide either the main Safrans website URL or a product/category URL")
        
        if not products:
            raise HTTPException(status_code=404, detail="No product information could be found")
        
        logger.info(f"Successfully scraped {len(products)} products")
        
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Product Name", "Price", "Weight", "Price per kg"])
        
        for product in products:
            writer.writerow([
                product["name"],
                product["price"],
                product["weight"],
                product["price_per_kg"]
            ])
        
        return {"csv_content": output.getvalue()}
    
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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)