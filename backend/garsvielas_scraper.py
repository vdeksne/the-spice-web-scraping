import csv
from typing import List, Dict
import logging
import asyncio
from playwright.async_api import async_playwright
import re
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

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
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-http2']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        
        page = await context.new_page()
        page.set_default_timeout(60000)  # 60 seconds timeout
        
        try:
            if url is None:
                url = "https://www.garsvielas.lv/gar%C5%A1vielas"
            
            if not url.startswith("https://www.garsvielas.lv/"):
                raise ValueError("Invalid URL. Please provide a URL from garsvielas.lv")
                
            logger.info(f"Loading page: {url}")
            
            await page.goto(url)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(5000)
            
            # Try to close the popup if it exists
            try:
                close_button = await page.wait_for_selector("span[class*='close']", timeout=5000)
                if close_button:
                    await close_button.click()
                    await page.wait_for_timeout(2000)
            except Exception as e:
                logger.info(f"No popup found or error handling popup: {str(e)}")

            # First, get all product links
            product_links = await page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a[data-hook="product-item-container"]'));
                return links.map(link => link.href);
            }""")
            
            logger.info(f"Processing all {len(product_links)} product links")
            
            results = []
            # Visit each product page and get variations
            for index, product_url in enumerate(product_links):
                try:
                    # Calculate and log progress percentage
                    progress_percentage = int((index / len(product_links)) * 100)
                    logger.info(f"Progress: {progress_percentage}% - Processing product {index+1} of {len(product_links)}")
                    logger.info(f"Processing product page: {product_url}")
                    
                    # Navigate to product page
                    await page.goto(product_url)
                    await page.wait_for_load_state('domcontentloaded')
                    await page.wait_for_timeout(2000)
                    
                    # Get product name from the product title
                    name_elem = await page.wait_for_selector('h1[data-hook="product-title"]')
                    if not name_elem:
                        name_elem = await page.wait_for_selector('[data-hook="product-item-name"]')
                    name = await name_elem.inner_text()
                    name = name.strip()
                    logger.info(f"Found product name: {name}")
                    
                    # Find and click the dropdown button
                    try:
                        dropdown_button = await page.wait_for_selector('button[data-hook="dropdown-base"]', timeout=5000)
                        if dropdown_button:
                            # First, get all weight texts to know what we need to process
                            await dropdown_button.click()
                            await page.wait_for_timeout(1000)
                            
                            # Get all weight options text first
                            weight_options = []
                            menu_items = await page.query_selector_all('div[role="menuitem"]')
                            for item in menu_items:
                                weight_span = await item.query_selector('span[class*="ogFb3AX"]')
                                if weight_span:
                                    weight_text = await weight_span.inner_text()
                                    weight_options.append(weight_text)
                            
                            logger.info(f"Found weight options: {weight_options}")
                            
                            # Close the dropdown
                            await dropdown_button.click()
                            await page.wait_for_timeout(1000)
                            
                            # Now process each weight option
                            for weight in weight_options:
                                try:
                                    # Open dropdown
                                    await dropdown_button.click()
                                    await page.wait_for_timeout(1000)
                                    
                                    # Find and click the specific weight option
                                    option_selector = f'div[role="menuitem"][title="{weight}"]'
                                    option = await page.wait_for_selector(option_selector)
                                    if option:
                                        await option.click()
                                        await page.wait_for_timeout(1000)
                                        
                                        # Get the updated price
                                        price_elem = await page.wait_for_selector('[data-hook="formatted-primary-price"]')
                                        price_text = await price_elem.get_attribute('data-wix-price')
                                        logger.info(f"Found price text: {price_text}")
                                        
                                        # Extract numeric price value
                                        raw_price = clean_price(price_text)
                                        formatted_price = format_price(raw_price)
                                        price_per_kg = calculate_price_per_kg(raw_price, weight)
                                        
                                        logger.info(f"Found price {formatted_price} for weight {weight}")
                                        
                                        # Add product variation
                                        results.append({
                                            'name': name,
                                            'price': formatted_price,
                                            'weight': weight,
                                            'price_per_kg': price_per_kg
                                        })
                                    
                                except Exception as e:
                                    logger.error(f"Error processing weight option: {str(e)}")
                                    continue
                                    
                        else:
                            # No dropdown - single weight product
                            # Try to find weight in product name
                            weight_match = re.search(r'\s+(\d+(?:\.\d+)?(?:g|kg))(?:\s+|$)', name)
                            weight = weight_match.group(1) if weight_match else 'N/A'
                            
                            # Get the price from the product-item-price-to-pay element
                            try:
                                price_elem = await page.wait_for_selector('[data-hook="product-item-price-to-pay"]')
                                price_text = await price_elem.get_attribute('data-wix-price')
                                logger.info(f"Found price text for single weight product: {price_text}")
                                
                                raw_price = clean_price(price_text)
                                formatted_price = format_price(raw_price)
                                price_per_kg = calculate_price_per_kg(raw_price, weight)
                                
                                logger.info(f"Found price {formatted_price} for weight {weight}")
                                
                                results.append({
                                    'name': name,
                                    'price': formatted_price,
                                    'weight': weight,
                                    'price_per_kg': price_per_kg
                                })
                            except Exception as e:
                                logger.error(f"Error processing single weight product: {str(e)}")
                                continue
                            
                    except Exception as e:
                        # If dropdown button not found, try to process as single weight product
                        logger.info(f"No dropdown button found, processing as single weight product")
                        
                        # Try to find weight in product name
                        weight_match = re.search(r'\s+(\d+(?:\.\d+)?(?:g|kg))(?:\s+|$)', name)
                        weight = weight_match.group(1) if weight_match else 'N/A'
                        
                        # Get the price from the product-item-price-to-pay element
                        try:
                            price_elem = await page.wait_for_selector('[data-hook="product-item-price-to-pay"]')
                            price_text = await price_elem.get_attribute('data-wix-price')
                            logger.info(f"Found price text for single weight product: {price_text}")
                            
                            raw_price = clean_price(price_text)
                            formatted_price = format_price(raw_price)
                            price_per_kg = calculate_price_per_kg(raw_price, weight)
                            
                            logger.info(f"Found price {formatted_price} for weight {weight}")
                            
                            results.append({
                                'name': name,
                                'price': formatted_price,
                                'weight': weight,
                                'price_per_kg': price_per_kg
                            })
                        except Exception as e:
                            logger.error(f"Error processing single weight product: {str(e)}")
                            continue
                        
                except Exception as e:
                    logger.error(f"Error processing product page: {str(e)}")
                    continue
            
            # Log final progress
            logger.info(f"Progress: 100% - Completed scraping {len(product_links)} products")
            
            # Export to CSV
            export_to_csv(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error scraping page: {str(e)}")
            return []
        finally:
            await page.wait_for_timeout(2000)
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

def scrape_product_page(url, base_url):
    """Scrape individual product page"""
    try:
        logger.info(f"Scraping product page: {url}")
        
        # Make sure URL is absolute
        full_url = urljoin(base_url, url)
        
        # Initialize Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Initialize the driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(full_url)
        driver.implicitly_wait(5)  # Set a general implicit wait
        
        # Wait for the page to load
        wait = WebDriverWait(driver, 10)
        
        # Find product name
        name = None
        try:
            name_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-hook="product-item-name"]')))
            name = name_elem.text.strip()
            logger.info(f"Found product name: {name}")
        except Exception as e:
            logger.error(f"Error finding product name: {e}")
            return []

        products = []
        try:
            # Find and click the dropdown button
            dropdown_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-hook="dropdown-base"]')))
            dropdown_button.click()
            logger.info("Clicked dropdown button")

            # Wait for dropdown options container
            options_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="menu"]')))
            
            # Find all weight options
            weight_options = options_container.find_elements(By.CSS_SELECTOR, 'div[role="menuitem"]')
            logger.info(f"Found {len(weight_options)} weight options")

            for option in weight_options:
                try:
                    # Get the weight text
                    weight_span = option.find_element(By.CSS_SELECTOR, 'span[class*="oGS1fO3"]')
                    weight_text = weight_span.text.strip()
                    logger.info(f"Processing weight option: {weight_text}")

                    # Click the weight option
                    driver.execute_script("arguments[0].click();", option)
                    logger.info(f"Clicked weight option: {weight_text}")

                    # Wait for price element to be updated
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-hook="product-item-price-to-pay"]')))
                    driver.implicitly_wait(1)  # Short wait for price update

                    # Get the updated price
                    price_elem = driver.find_element(By.CSS_SELECTOR, '[data-hook="product-item-price-to-pay"]')
                    price_text = price_elem.text.strip()
                    logger.info(f"Found price text: {price_text}")

                    # Extract numeric price value
                    price_match = re.search(r'(\d+[.,]\d+)', price_text)
                    if price_match:
                        price = float(price_match.group(1).replace(',', '.'))
                        logger.info(f"Found price for {weight_text}: {price}")

                        # Format price and calculate price per kg
                        formatted_price = format_price(price)
                        price_per_kg = calculate_price_per_kg(price, weight_text)

                        products.append({
                            "name": name,
                            "price": formatted_price,
                            "weight": weight_text,
                            "price_per_kg": price_per_kg
                        })

                    # Click the dropdown button again to show options for next iteration
                    if option != weight_options[-1]:  # If not the last option
                        dropdown_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-hook="dropdown-base"]')))
                        dropdown_button.click()
                        logger.info("Reopened dropdown for next option")
                        # Wait for options to be visible again
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="menu"]')))

                except Exception as e:
                    logger.error(f"Error processing weight option: {e}")
                    logger.error(f"Exception details: {str(e)}")
                    continue

            return products

        except Exception as e:
            logger.error(f"Error in weight selection process: {e}")
            logger.error(f"Exception details: {str(e)}")
            return []

    except Exception as e:
        logger.error(f"Error scraping product page: {e}")
        logger.error(f"Exception details: {str(e)}")
        return []
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(scrape_garsvielas())
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}") 