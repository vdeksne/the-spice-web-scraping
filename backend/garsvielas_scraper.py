import csv
from typing import List, Dict
import logging
import asyncio
from playwright.async_api import async_playwright
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_price_per_kg(price: float, weight_str: str) -> str:
    """Calculate price per kg if possible."""
    if weight_str == 'N/A':
        return 'N/A'
    
    try:
        # Extract numeric value and unit from weight string
        match = re.search(r'(\d+(?:\.\d+)?)\s*(g|kg)', weight_str.lower())
        if not match:
            return 'N/A'
            
        value = float(match.group(1))
        unit = match.group(2)
        
        # Convert to kg if in grams
        weight_kg = value if unit == 'kg' else value / 1000
        
        if weight_kg > 0:
            price_per_kg = price / weight_kg
            # Format with dot and 2 decimal places
            return f"{int(price_per_kg)}.{int((price_per_kg % 1) * 100):02d}"
        return 'N/A'
    except Exception as e:
        logger.error(f"Error calculating price per kg: {e}")
        return 'N/A'

def clean_price(price_text: str) -> float:
    """Clean price text and return raw float value."""
    try:
        # Remove any currency symbols and whitespace
        cleaned = price_text.replace('No', '').replace('€', '').strip()
        # Extract the numeric value using regex
        match = re.search(r'(\d+(?:[.,]\d+)?)', cleaned)
        if match:
            # Replace comma with dot for float conversion
            price_str = match.group(1).replace(',', '.')
            return float(price_str)
        return 0.0
    except ValueError:
        return 0.0

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

async def scrape_garsvielas(url=None):
    async with async_playwright() as p:
        # Launch browser with more lenient settings
        browser = await p.chromium.launch(
            headless=False,  # Set to False to see what's happening
            args=['--disable-http2']
        )
        
        # Create context with more lenient timeout
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        
        page = await context.new_page()
        page.set_default_timeout(60000)  # 60 seconds timeout
        
        try:
            # Use the provided URL or default to the main page
            if url is None:
                url = "https://www.garsvielas.lv/gar%C5%A1vielas"
            
            # Validate URL
            if not url.startswith("https://www.garsvielas.lv/"):
                raise ValueError("Invalid URL. Please provide a URL from garsvielas.lv")
                
            logger.info(f"Loading page: {url}")
            
            # Go to the page and wait for it to load
            await page.goto(url)
            await page.wait_for_load_state('domcontentloaded', timeout=60000)
            
            # Wait for the page to stabilize
            await page.wait_for_timeout(10000)  # Increased wait time
            
            # Try to close the popup if it exists
            try:
                logger.info("Looking for popup close button...")
                close_button = await page.wait_for_selector("span[class*='close']", timeout=5000)
                if close_button:
                    logger.info("Found close button")
                    await close_button.click()
                    logger.info("Clicked close button")
                    await page.wait_for_timeout(5000)  # Wait after closing popup
            except Exception as e:
                logger.info(f"Error handling popup: {str(e)}")
            
            # Wait for any price element to be visible
            logger.info("Waiting for prices to load...")
            try:
                await page.wait_for_selector('span[data-hook="price-range-from"], span[data-hook="product-item-price-to-pay"]', timeout=30000)
                logger.info("Prices loaded successfully")
            except Exception as e:
                logger.error(f"Error waiting for prices: {str(e)}")
            
            # Try to find product names
            logger.info("Looking for product names...")
            product_names = await page.query_selector_all("h3[data-hook='product-item-name']")
            
            if not product_names:
                logger.error("Could not find any products")
                return []
            
            logger.info(f"Found {len(product_names)} products")
            
            results = []
            for name_elem in product_names:
                try:
                    # Get product name and extract weight if present
                    name = await name_elem.inner_text()
                    name = name.strip()
                    
                    # Extract weight from name if present
                    weight_pattern = r'\s+(\d+(?:\.\d+)?(?:g|kg))(?:\s+|$)'
                    weight_match = re.search(weight_pattern, name)
                    weight = weight_match.group(1) if weight_match else None
                    
                    # Remove weight from name if found
                    if weight_match:
                        name = name[:weight_match.start()].strip()
                    
                    logger.info(f"Found product name: {name}, weight: {weight}")
                    
                    # Find the parent product item
                    container = await name_elem.evaluate("""node => {
                        const container = node.closest('[data-hook="product-item-name-and-price-layout"]');
                        if (!container) {
                            console.log('Could not find product container');
                            return null;
                        }
                        return container.outerHTML;
                    }""")
                    
                    if not container:
                        logging.warning(f"Could not find container for product: {name}")
                        continue
                        
                    logging.info(f"Found container for product: {name}")
                    logging.info(f"Container HTML: {container}")
                    
                    # Extract price from the container
                    price = await page.evaluate("""container => {
                        try {
                            // Parse the HTML string into a DOM element
                            const parser = new DOMParser();
                            const doc = parser.parseFromString(container, 'text/html');
                            
                            // Find the prices container
                            const pricesContainer = doc.querySelector('[data-hook="prices-container"]');
                            if (!pricesContainer) {
                                console.log('Could not find prices container');
                                console.log('Container HTML:', container);
                                return null;
                            }
                            
                            // Try to find the price elements
                            const priceToPay = pricesContainer.querySelector('[data-hook="product-item-price-to-pay"]');
                            const priceFrom = pricesContainer.querySelector('[data-hook="price-range-from"]');
                            
                            // Return the price text, preferring price-to-pay over price-from
                            if (priceToPay) {
                                return priceToPay.textContent.trim();
                            } else if (priceFrom) {
                                return priceFrom.textContent.trim();
                            }
                            
                            return null;
                        } catch (error) {
                            console.error('Error finding price:', error);
                            return null;
                        }
                    }""", container)
                    
                    if price:
                        raw_price = clean_price(price)
                        formatted_price = format_price(raw_price)
                        logger.info(f"Found price for {name}: {formatted_price}")
                        
                        # Calculate price per kg
                        price_per_kg = calculate_price_per_kg(raw_price, weight if weight else 'N/A')
                        logger.info(f"Calculated price per kg: {price_per_kg}")
                        
                        # Create product object
                        product = {
                            'name': name,
                            'price': formatted_price,
                            'weight': weight if weight else 'N/A',
                            'price_per_kg': price_per_kg
                        }
                        results.append(product)
                    else:
                        logger.warning(f"No price found for {name}")
                except Exception as e:
                    logger.error(f"Error scraping product: {str(e)}")
            
            # Print results in a table format
            print("\nScraped Products:")
            print("-" * 90)
            print(f"{'Product Name':<50} {'Price (€)':<10} {'Weight':<10} {'Price/kg':<10}")
            print("-" * 90)
            
            for product in results:
                name = product['name']
                price = product['price']
                weight = product['weight'] if product['weight'] is not None else 'N/A'
                price_per_kg = product['price_per_kg'] if product['price_per_kg'] is not None else 'N/A'
                
                print(f"{name[:50]:<50} {price:<10} {weight:<10} {price_per_kg:<10}")
            
            if not results:
                print("No products were found.")
                
            # Export to CSV
            export_to_csv(results)
            
            # Return the results
            return results
        except Exception as e:
            logger.error(f"Error scraping page: {str(e)}")
            return []
        finally:
            # Add a delay before closing to see the results
            await page.wait_for_timeout(5000)
            await context.close()
            await browser.close()

def export_to_csv(products: List[Dict[str, str]], filename: str = "garsvielas_products.csv"):
    """Export products to CSV file."""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            # Write headers manually
            f.write('Product Name,Price,Weight,Price per kg\n')
            
            # Write data manually to have full control over formatting
            for product in products:
                name = product['name'].strip().replace('"', '').replace(',', ' ')
                price = product['price']  # Already formatted
                weight = product['weight'].strip().replace('"', '') if product['weight'] else 'N/A'
                price_per_kg = product['price_per_kg'].strip().replace('"', '') if product['price_per_kg'] else 'N/A'
                
                # Format the line manually
                line = f"{name},{price},{weight},{price_per_kg}\n"
                f.write(line)
                
        logger.info(f"Successfully exported {len(products)} products to {filename}")
    except Exception as e:
        logger.error(f"Error exporting to CSV: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(scrape_garsvielas())
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}") 