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
from cikade_scraper import scrape_cikade

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Enable CORS
CORS(app)

# Global variable to track progress
scraping_progress = 0

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
def scrape_website():
    global scraping_progress
    scraping_progress = 0  # Reset progress at the start
    
    try:
        url = request.args.get('url')
        format_type = request.args.get('format', 'csv')  # Default to CSV format
        limit = request.args.get('limit', type=int)  # Get limit parameter
        if not url:
            return jsonify({'error': 'URL parameter is required'}), 400
            
        # Decode the URL properly
        decoded_url = unquote(url)
        logger.info(f"Starting scrape of website: {decoded_url}")
        
        # Determine URL type and handle accordingly
        if 'garsvielas.lv' in decoded_url:
            logger.info(f"Scraping Garsvielas URL: {decoded_url}")
            # Run the Garsvielas scraper in an event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            products = loop.run_until_complete(scrape_garsvielas(decoded_url))
            loop.close()
            
            if not products:
                return jsonify({'error': 'No product information could be found'}), 404
            
            # Return format based on request
            if format_type == 'json':
                # Return raw JSON data for GarsvielasView
                return jsonify(products)
            else:
                # Create CSV content with proper formatting
                output = StringIO()
                # Write headers manually without quotes
                output.write('Product Name,Price (€),Weight (g),Price per kg (€)\n')
                
                # Write data manually without quotes
                for product in products:
                    name = product['name'].strip() if product['name'] else ''
                    price = product['price'].strip() if product['price'] else 'N/A'
                    weight = product['weight'].strip() if product['weight'] else 'N/A'
                    price_per_kg = product['price_per_kg'].strip() if product['price_per_kg'] else 'N/A'
                    
                    # Remove any existing quotes or backslashes
                    name = name.replace('"', '').replace('\\', '').replace(',', ' ')
                    price = price.replace('"', '').replace('\\', '').replace(',', ' ')
                    weight = weight.replace('"', '').replace('\\', '').replace(',', ' ')
                    price_per_kg = price_per_kg.replace('"', '').replace('\\', '').replace(',', ' ')
                    
                    # Write the line without quotes
                    output.write(f"{name},{price},{weight},{price_per_kg}\n")
                
                return jsonify({"csv_content": output.getvalue()})
            
        elif 'cikade.lv' in decoded_url:
            logger.info(f"Scraping Cikade URL: {decoded_url}")
            # Run the Cikade scraper in an event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            products = loop.run_until_complete(scrape_cikade(decoded_url, limit))
            loop.close()
            
            if not products:
                return jsonify({'error': 'No product information could be found'}), 404
            
            # Return format based on request
            if format_type == 'json':
                # Return raw JSON data for CikadeView
                return jsonify(products)
            else:
                # Create CSV content with proper formatting
                output = StringIO()
                # Write headers manually without quotes
                output.write('Product Name,Price (€),Weight (g),Price per kg (€)\n')
                
                # Write data manually without quotes
                for product in products:
                    name = product['name'].strip() if product['name'] else ''
                    price = product['price'].strip() if product['price'] else 'N/A'
                    weight = product['weight'].strip() if product['weight'] else 'N/A'
                    price_per_kg = product['price_per_kg'].strip() if product['price_per_kg'] else 'N/A'
                    
                    # Remove any existing quotes or backslashes
                    name = name.replace('"', '').replace('\\', '').replace(',', ' ')
                    price = price.replace('"', '').replace('\\', '').replace(',', ' ')
                    weight = weight.replace('"', '').replace('\\', '').replace(',', ' ')
                    price_per_kg = price_per_kg.replace('"', '').replace('\\', '').replace(',', ' ')
                    
                    # Write the line without quotes
                    output.write(f"{name},{price},{weight},{price_per_kg}\n")
                
                return jsonify({"csv_content": output.getvalue()})
            
        elif 'safrans.lv' in decoded_url:
            # Handle Safrans website
            if decoded_url == "https://www.safrans.lv":
                # Main website URL - do full crawl
                products = crawl_website(decoded_url)
            else:
                # This is a category or product page
                if decoded_url.count('/') >= 5:  # This is a product page URL
                    # Single product page
                    products = scrape_product_page(decoded_url, 'https://www.safrans.lv')
                else:
                    # This is a category page - get product links and scrape each one
                    logger.info(f"Scraping category page: {decoded_url}")
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    response = requests.get(decoded_url, headers=headers)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    product_links = get_product_links(soup)
                    if not product_links:
                        logger.warning(f"No product links found on category page: {decoded_url}")
                        return jsonify({'error': 'No product links found on this category page'}), 404
                    
                    products = []
                    for product_url in product_links[:10000]:  # Limit to 10 products
                        product_data = scrape_product_page(product_url, 'https://www.safrans.lv')
                        products.extend(product_data)
                        time.sleep(1)  # Be nice to the server
            
            if not products:
                return jsonify({'error': 'No product information could be found'}), 404
            
            logger.info(f"Successfully scraped {len(products)} products")
            
            # Return format based on request
            if format_type == 'json':
                # Return raw JSON data
                return jsonify(products)
            else:
                # Create CSV content
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(["Product Name", "Price (€)", "Weight (g)", "Price per kg (€)"])
                
                for product in products:
                    writer.writerow([
                        product["name"],
                        product["price"],
                        product["weight"],
                        product["price_per_kg"]
                    ])
                
                return jsonify({"csv_content": output.getvalue()})
        else:
            return jsonify({'error': 'Invalid URL. Please provide a URL from garsvielas.lv, cikade.lv, or safrans.lv'}), 400
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return jsonify({'error': f'Error making request: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Error scraping website: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/progress', methods=['GET'])
def get_progress():
    """Return the current scraping progress as a percentage"""
    return jsonify({"progress": scraping_progress})

@app.route('/update_progress', methods=['GET'])
def update_progress():
    """Update the current scraping progress"""
    global scraping_progress
    progress = request.args.get('progress', type=int)
    if progress is not None:
        scraping_progress = progress
        logger.info(f"Progress updated to {progress}%")
    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(debug=True, port=8003) 