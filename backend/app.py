from flask import Flask, request, jsonify # type: ignore
from flask_cors import CORS # type: ignore
from bs4 import BeautifulSoup # type: ignore
import requests # type: ignore
import csv
from io import StringIO
import re
import logging
from urllib.parse import urljoin, unquote
import time
import asyncio
from garsvielas_scraper import scrape_garsvielas

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Enable CORS
CORS(app)

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
        
        # Convert to grams for consistent calculation
        weight_grams = value * 1000 if unit == 'kg' else value
        
        if weight_grams > 0:
            # Calculate price per kg (1000g)
            price_per_kg = (price / weight_grams) * 1000
            return f"{price_per_kg:.2f}€"
        return "N/A"
    except Exception as e:
        logger.error(f"Error extracting price per kg: {e}")
        return "N/A"
    
def calculate_total_price(base_price: float, weight_text: str) -> str:
    """Calculate total price for given weight."""
    try:
        # Extract weight value and unit
        weight_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(kg|g)', weight_text.lower())
        if not weight_match:
            return "N/A"
            
        value = float(weight_match.group(1).replace(',', '.'))
        unit = weight_match.group(2)
        
        # Convert to grams for consistent calculation
        weight_grams = value * 1000 if unit == 'kg' else value
        
        # Calculate total price (price per gram * weight in grams)
        total_price = base_price * weight_grams
        return f"{total_price:.2f}€"
    except Exception as e:
        logger.error(f"Error calculating total price: {e}")
        return "N/A"

def format_price(price: float) -> str:
    """Format price with dot between euros and cents."""
    if isinstance(price, str):
        return price
    if price == 0.0:
        return 'N/A'
    try:
        # Split into euros and cents
        euros = int(price)
        cents = int(round((price - euros) * 100))
        # Format with dot
        return f"{euros}.{cents:02d}"
    except:
        return 'N/A'

def extract_price_from_weight(weight_text: str) -> float:
    """Extract price from weight text that contains price in parentheses."""
    try:
        # Extract price from text like "100 g (1.70€)"
        price_match = re.search(r'\((\d+[.,]\d+)€\)', weight_text)
        if price_match:
            price_str = price_match.group(1).replace(',', '.')
            return float(price_str)
        return None
    except Exception as e:
        logger.error(f"Error extracting price from weight: {e}")
        return None

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
                # Extract price from weight text if available
                weight_price = extract_price_from_weight(weight)
                
                # Use weight price if available and different from main price
                if weight_price is not None and abs(weight_price - price) > 0.01:  # Allow for small floating point differences
                    logger.info(f"Using price from weight section: {weight_price} instead of {price}")
                    price = weight_price
                    price_text = f"{price:.2f}€"
                
                formatted_price = format_price(price)
                price_per_kg = extract_price_per_kg(price, weight)
                products.append({
                    "name": name,
                    "price": formatted_price,
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

@app.route('/scrape', methods=['GET'])
async def scrape_website():
    """Endpoint to scrape website data"""
    try:
        url = request.args.get('url')
        limit = request.args.get('limit', type=int)  # Get limit parameter as integer
        
        if not url:
            return jsonify({'error': 'URL parameter is required'}), 400
            
        # Decode URL if it's encoded
        url = unquote(url)
        logger.info(f"Received scrape request for URL: {url}")
        logger.info(f"Product limit set to: {limit if limit else 'unlimited'}")
        
        # Check which website we're scraping
        if 'safrans' in url.lower():
            # Handle Safrans website
            base_url = "https://www.safrans.lv"
            products = crawl_website(base_url)
            return jsonify(products)
        elif 'garsvielas' in url.lower():
            # Handle Garsvielas website
            products = await scrape_garsvielas(url, limit)
            return jsonify(products)
        else:
            return jsonify({'error': 'Unsupported website'}), 400
            
    except Exception as e:
        logger.error(f"Error in scrape endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8003) 