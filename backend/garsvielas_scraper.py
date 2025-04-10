import csv
from typing import List, Dict
import logging
import asyncio
from playwright.async_api import async_playwright
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_price_per_kg(price: str, weight: str = None) -> str:
    """Calculate price per kg if possible."""
    if weight is None:
        return "N/A"
    
    try:
        # Extract numeric values from price and weight
        price_value = float(price.replace('€', '').strip())
        weight_value = float(weight.replace('g', '').strip())
        
        # Calculate price per kg (convert grams to kg)
        price_per_kg = (price_value / weight_value) * 1000
        return f"{price_per_kg:.2f}€/kg"
    except (ValueError, ZeroDivisionError):
        return "N/A"

def clean_price(price_text: str) -> str:
    """Clean price text by removing currency symbols and 'No' prefix."""
    return price_text.replace('No', '').replace('€', '').strip()

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
                    # Get product name
                    name = await name_elem.inner_text()
                    name = name.strip()
                    logger.info(f"Found product name: {name}")
                    
                    # Find the parent product item
                    container = await name_elem.evaluate("""node => {
                        // Find the parent container with product name and price
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
                            
                            console.log('Prices container HTML:', pricesContainer.outerHTML);
                            
                            // Try to find the price elements
                            const priceToPay = pricesContainer.querySelector('[data-hook="product-item-price-to-pay"]');
                            const priceFrom = pricesContainer.querySelector('[data-hook="price-range-from"]');
                            
                            console.log('Price to pay element:', priceToPay ? priceToPay.outerHTML : 'not found');
                            console.log('Price from element:', priceFrom ? priceFrom.outerHTML : 'not found');
                            
                            // Return the price text, preferring price-to-pay over price-from
                            if (priceToPay) {
                                return priceToPay.textContent.trim();
                            } else if (priceFrom) {
                                return priceFrom.textContent.trim();
                            }
                            
                            console.log('No price elements found in container');
                            return null;
                        } catch (error) {
                            console.error('Error finding price:', error);
                            return null;
                        }
                    }""", container)
                    
                    if price:
                        price = clean_price(price)
                        logger.info(f"Found price for {name}: {price}")
                        
                        # Create product object
                        product = {
                            'name': name,
                            'price': price,
                            'weight': None,  # We'll handle weight extraction later if needed
                            'price_per_kg': None  # We'll calculate this later if needed
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
                price = product['price'] if product['price'] is not None else 'N/A'
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
            writer = csv.writer(f)
            # Write headers
            writer.writerow(['Product Name', 'Price', 'Weight', 'Price per kg'])
            # Write data
            for product in products:
                writer.writerow([
                    product['name'],
                    product['price'],
                    product['weight'] or 'N/A',
                    product['price_per_kg']
                ])
        logger.info(f"Successfully exported {len(products)} products to {filename}")
    except Exception as e:
        logger.error(f"Error exporting to CSV: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(scrape_garsvielas())
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}") 