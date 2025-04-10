from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import requests
import csv
from io import StringIO
import re
import logging
from urllib.parse import unquote

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

def get_product_links(soup, base_url):
    """Extract product links from the main page"""
    product_links = []
    
    # Find all links that might be product links
    for link in soup.find_all('a', href=True):
        href = link['href']
        if 'product-page' in href:
            full_url = urljoin(base_url, href)
            product_links.append(full_url)
            logger.info(f"Found product link: {full_url}")
    
    return product_links

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

def scrape_product_page(url):
    try:
        logger.info(f"Scraping product page: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Log the response content for debugging
        logger.info(f"Response content length: {len(response.text)}")
        logger.info(f"Response status code: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find product name (h2 with class 'title')
        name = None
        name_elem = soup.find('h2', class_='title')
        if name_elem:
            name = name_elem.text.strip()
            logger.info(f"Found product name: {name}")
        else:
            logger.warning("Could not find product name (h2.title)")
            # Try to find the name in other elements
            name_elem = soup.find('h1')  # Try h1 tag
            if name_elem:
                name = name_elem.text.strip()
                logger.info(f"Found product name in h1: {name}")
        
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
        else:
            logger.warning("Could not find price (h2.price)")
            # Try to find price in other elements
            price_elem = soup.find(text=re.compile(r'\d+[.,]\d+\s*€'))
            if price_elem:
                price_text = price_elem.strip()
                price_match = re.search(r'(\d+[.,]\d+)', price_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', '.'))
                logger.info(f"Found price in text: {price_text}")
        
        # Find weight options (labels with class 'radio')
        weights = []
        weight_elems = soup.find_all('label', class_='radio')
        for elem in weight_elems:
            weight_text = elem.text.strip()
            if weight_text:
                weights.append(weight_text)
                logger.info(f"Found weight option: {weight_text}")
        
        if not weights:
            logger.warning("No weight options found in labels.radio")
            # Try to find weight in other elements
            weight_elem = soup.find('select')
            if weight_elem:
                options = weight_elem.find_all('option')
                for option in options:
                    weight_text = option.text.strip()
                    if weight_text:
                        weights.append(weight_text)
                        logger.info(f"Found weight option in select: {weight_text}")
        
        if not weights:
            weights = ["1 kg"]  # Default weight if none found
            logger.warning("Using default weight: 1 kg")
        
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
                logger.info(f"Added product entry: {name}, {price_text}, {weight}, {price_per_kg}")
        
        if not products:
            logger.warning("No products were created")
            if not name:
                logger.error("Missing product name")
            if not price:
                logger.error("Missing product price")
        
        return products
    
    except Exception as e:
        logger.error(f"Error scraping product page: {e}")
        return []

@app.get("/scrape")
async def scrape_website(url: str = Query(..., description="URL to scrape")):
    try:
        # URL should already be properly encoded by the client
        logger.info(f"Received URL: {url}")
        
        # Scrape the product page directly
        products = scrape_product_page(url)
        
        if not products:
            logger.warning("No products were successfully scraped!")
            raise HTTPException(status_code=404, detail="No product information could be found on the page")
        
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
    except Exception as e:
        logger.error(f"Error scraping website: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)