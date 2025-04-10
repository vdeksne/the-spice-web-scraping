from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
from garsvielas_scraper import scrape_garsvielas
import urllib.parse
import logging
import requests
from bs4 import BeautifulSoup
import re
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Enable CORS for all routes and origins
CORS(app, resources={r"/*": {"origins": "*"}})

def scrape_safrans(url: str):
    """Scrape products from Safrans website."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        logger.info(f"Scraping Safrans URL: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        
        # Find all product links
        product_links = []
        for link in soup.find_all('a', href=True):
            if '/garsvielas_/garsvielas_un_garsaugi/' in link['href'] and link['href'].count('/') >= 5:
                product_links.append(link['href'])
                logger.info(f"Found product link: {link['href']}")
        
        # Scrape each product page
        for product_url in product_links:
            try:
                logger.info(f"Scraping product page: {product_url}")
                product_response = requests.get(product_url, headers=headers)
                product_response.raise_for_status()
                product_soup = BeautifulSoup(product_response.text, 'html.parser')
                
                # Extract product name from h2 with class 'title'
                name_elem = product_soup.find('h2', class_='title')
                if not name_elem:
                    continue
                name = name_elem.text.strip()
                
                # Extract price from h2 with class 'price'
                price_elem = product_soup.find('h2', class_='price')
                if not price_elem:
                    continue
                price_text = price_elem.text.strip()
                
                # Extract numeric price value using regex
                price_match = re.search(r'(\d+[.,]\d+)', price_text)
                if not price_match:
                    continue
                price = float(price_match.group(1).replace(',', '.'))
                
                # Extract weight options from labels with class 'radio'
                weights = []
                weight_elems = product_soup.find_all('label', class_='radio')
                for elem in weight_elems:
                    weight_text = elem.text.strip()
                    if weight_text:
                        weights.append(weight_text)
                
                if not weights:
                    weights = ["1 kg"]  # Default weight if none found
                
                # Create product entries for each weight option
                for weight in weights:
                    # Calculate price per kg
                    price_per_kg = None
                    try:
                        # Extract weight value and unit
                        weight_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(kg|g)', weight.lower())
                        if weight_match:
                            value = float(weight_match.group(1).replace(',', '.'))
                            unit = weight_match.group(2)
                            
                            # Convert to kg if in grams
                            weight_kg = value if unit == 'kg' else value / 1000
                            
                            if weight_kg > 0:
                                price_per_kg = f"{(price / weight_kg):.2f}"
                    except (ValueError, ZeroDivisionError):
                        pass
                    
                    products.append({
                        'name': name,
                        'price': str(price),
                        'weight': weight,
                        'price_per_kg': price_per_kg
                    })
                    logger.info(f"Found product: {name} - {price}€ - {weight}")
                
                # Add a small delay between requests
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing product page: {str(e)}")
                continue
        
        if not products:
            logger.warning("No products found on the page")
            logger.info(f"Page content: {soup.prettify()[:1000]}")  # Log first 1000 chars of HTML for debugging
            
        return products
    except Exception as e:
        logger.error(f"Error scraping Safrans: {str(e)}")
        raise

@app.route('/scrape', methods=['GET'])
async def scrape():
    try:
        # Get URL from query parameters
        url = request.args.get('url')
        if not url:
            return jsonify({'error': 'URL parameter is required'}), 400
            
        # Decode the URL properly
        decoded_url = urllib.parse.unquote(url)
        
        # Validate URL
        if not decoded_url.startswith(('https://www.garsvielas.lv/', 'https://www.safrans.lv/')):
            return jsonify({'error': 'Invalid URL. Please provide a URL from garsvielas.lv or safrans.lv'}), 400
        
        # Run the appropriate scraper
        if 'garsvielas.lv' in decoded_url:
            logger.info(f"Scraping Garsvielas URL: {decoded_url}")
            results = await scrape_garsvielas(decoded_url)
        else:
            logger.info(f"Scraping Safrans URL: {decoded_url}")
            results = scrape_safrans(decoded_url)
        
        if not results:
            return jsonify({'error': 'No products found'}), 404
            
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error scraping: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=True) 