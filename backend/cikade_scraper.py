import asyncio
import logging
import re
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def extract_price_per_kg(price: float, weight_text: str) -> str:
    """Calculate price per kg if possible."""
    try:
        # Extract numeric value and unit from weight string
        match = re.search(r'(\d+(?:\.\d+)?)\s*(g|kg)', weight_text.lower())
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

async def format_price(price: float) -> str:
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

async def get_product_links(page: Page) -> List[str]:
    """Extract product links from the category page."""
    logger.info("Extracting product links from category page")
    product_links = await page.evaluate("""() => {
        const links = Array.from(document.querySelectorAll('h3.name a'));
        return links.map(link => link.href);
    }""")
    logger.info(f"Found {len(product_links)} product links")
    return product_links

async def get_weight_options(page: Page) -> List[str]:
    """Extract weight options from the product page."""
    logger.info("Extracting weight options from product page")
    weight_options = await page.evaluate("""() => {
        const select = document.getElementById('svars');
        if (!select) return [];
        
        const options = Array.from(select.options);
        return options
            .filter(option => option.value && option.value !== '')
            .map(option => option.value);
    }""")
    logger.info(f"Found {len(weight_options)} weight options: {weight_options}")
    return weight_options

async def select_weight_option(page: Page, weight: str) -> bool:
    """Select a weight option from the dropdown."""
    logger.info(f"Selecting weight option: {weight}")
    try:
        await page.select_option('#svars', weight)
        logger.info(f"Successfully selected weight option: {weight}")
        return True
    except Exception as e:
        logger.error(f"Error selecting weight option: {e}")
        return False

async def add_to_cart(page: Page) -> bool:
    """Click the 'Add to cart' button."""
    logger.info("Clicking 'Add to cart' button")
    try:
        await page.click('button.single_add_to_cart_button')
        logger.info("Successfully clicked 'Add to cart' button")
        return True
    except Exception as e:
        logger.error(f"Error clicking 'Add to cart' button: {e}")
        return False

async def view_cart(page: Page) -> bool:
    """Click the 'View cart' button."""
    logger.info("Clicking 'View cart' button")
    try:
        await page.click('a.button.wc-forward')
        logger.info("Successfully clicked 'View cart' button")
        return True
    except Exception as e:
        logger.error(f"Error clicking 'View cart' button: {e}")
        return False

async def extract_cart_data(page: Page) -> Optional[Dict]:
    """Extract product data from the cart page."""
    logger.info("Extracting product data from cart page")
    try:
        cart_data = await page.evaluate("""() => {
            const productNameElem = document.querySelector('td.product-name a');
            const priceElem = document.querySelector('span.woocommerce-Price-amount');
            
            if (!productNameElem || !priceElem) return null;
            
            const productName = productNameElem.textContent.trim();
            const priceText = priceElem.textContent.trim();
            
            // Extract numeric price
            const priceMatch = priceText.match(/\\d+[.,]\\d+/);
            const price = priceMatch ? parseFloat(priceMatch[0].replace(',', '.')) : null;
            
            return {
                name: productName,
                price: price
            };
        }""")
        
        if not cart_data or not cart_data.get('name') or cart_data.get('price') is None:
            logger.error("Failed to extract cart data")
            return None
            
        logger.info(f"Extracted cart data: {cart_data}")
        return cart_data
    except Exception as e:
        logger.error(f"Error extracting cart data: {e}")
        return None

async def remove_from_cart(page: Page) -> bool:
    """Remove the product from the cart."""
    logger.info("Removing product from cart")
    try:
        await page.click('td.product-remove a.remove')
        logger.info("Successfully removed product from cart")
        return True
    except Exception as e:
        logger.error(f"Error removing product from cart: {e}")
        return False

async def get_product_name(page: Page) -> Optional[str]:
    """Extract product name from the product page."""
    logger.info("Extracting product name from product page")
    try:
        product_name = await page.evaluate("""() => {
            const titleElem = document.querySelector('h1.product_title');
            return titleElem ? titleElem.textContent.trim() : null;
        }""")
        
        if not product_name:
            logger.error("Failed to extract product name")
            return None
            
        logger.info(f"Extracted product name: {product_name}")
        return product_name
    except Exception as e:
        logger.error(f"Error extracting product name: {e}")
        return None

async def scrape_cikade(url: str = "https://cikade.lv/product-category/garsvielas/", limit: Optional[int] = None) -> List[Dict]:
    """Scrape products from Cikade website."""
    logger.info(f"Starting Cikade scraper for URL: {url}")
    products = []
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Make browser visible
                args=['--disable-http2']  # Add arguments for better compatibility
            )
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},  # Set viewport size
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'  # Set user agent
            )
            page = await context.new_page()
            page.set_default_timeout(60000)  # Set timeout to 60 seconds
            
            # Navigate to the category page
            await page.goto(url)
            logger.info("Navigated to category page")
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)  # Wait for page to fully load
            
            # Get product links
            product_links = await get_product_links(page)
            logger.info(f"Found {len(product_links)} product links")
            
            # Apply limit if specified
            if limit:
                product_links = product_links[:limit]
                logger.info(f"Limited to {limit} products")
            
            # Process each product
            for i, product_url in enumerate(product_links):
                try:
                    logger.info(f"Processing product {i+1}/{len(product_links)}: {product_url}")
                    
                    # Navigate to product page
                    await page.goto(product_url)
                    await page.wait_for_load_state('domcontentloaded')
                    await page.wait_for_timeout(3000)  # Wait for page to fully load
                    
                    # Get product name
                    name = await get_product_name(page)
                    if not name:
                        logger.warning(f"Could not find product name for {product_url}")
                        # Go back to the category page
                        await page.goto(url)
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_timeout(3000)
                        continue
                    
                    # Check if there's a weight dropdown
                    weight_options = await get_weight_options(page)
                    
                    if weight_options:
                        logger.info(f"Found {len(weight_options)} weight options for {name}")
                        
                        # Process each weight option
                        for j, weight in enumerate(weight_options):
                            try:
                                logger.info(f"Processing weight option {j+1}/{len(weight_options)}: {weight} for {name}")
                                
                                # Select weight option
                                if not await select_weight_option(page, weight):
                                    logger.warning(f"Failed to select weight option {weight}, skipping")
                                    continue
                                
                                await page.wait_for_timeout(2000)  # Wait for dropdown to update
                                
                                # Add to cart
                                if not await add_to_cart(page):
                                    logger.warning(f"Failed to add product to cart, skipping")
                                    continue
                                
                                await page.wait_for_timeout(3000)  # Wait for cart to update
                                
                                # View cart
                                if not await view_cart(page):
                                    logger.warning(f"Failed to view cart, skipping")
                                    continue
                                
                                await page.wait_for_load_state('domcontentloaded')
                                await page.wait_for_timeout(3000)  # Wait for cart page to load
                                
                                # Extract cart data
                                cart_data = await extract_cart_data(page)
                                if cart_data:
                                    # Calculate price per kg
                                    price = cart_data.get('price')
                                    if price is not None:
                                        price_per_kg = await extract_price_per_kg(price, weight)
                                        
                                        products.append({
                                            "name": name,
                                            "price": cart_data["price"],
                                            "weight": weight,
                                            "price_per_kg": price_per_kg
                                        })
                                        
                                        logger.info(f"Added product: {name} - {weight} - {cart_data['price']}€ - {price_per_kg}€/kg")
                                
                                # Remove from cart
                                if not await remove_from_cart(page):
                                    logger.warning(f"Failed to remove product from cart")
                                
                                await page.wait_for_timeout(3000)  # Wait for cart to update
                                
                                # Go back to the product page for the next weight option
                                await page.goto(product_url)
                                await page.wait_for_load_state('domcontentloaded')
                                await page.wait_for_timeout(3000)  # Wait for page to fully load
                                
                            except Exception as e:
                                logger.error(f"Error processing weight option {weight}: {e}")
                                # Try to go back to the product page
                                try:
                                    await page.goto(product_url)
                                    await page.wait_for_load_state('domcontentloaded')
                                    await page.wait_for_timeout(3000)
                                except:
                                    pass
                                continue
                        
                        # After processing all weight options, go back to the category page
                        logger.info(f"Finished processing all weight options for {name}, returning to category page")
                        await page.goto(url)
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_timeout(3000)  # Wait for page to fully load
                        
                    else:
                        # No weight options, just get the product price
                        try:
                            logger.info(f"Processing product without weight options: {name}")
                            
                            # Get price directly from the product page
                            price_text = await page.evaluate("""() => {
                                const priceElem = document.querySelector('.price .amount');
                                return priceElem ? priceElem.textContent.trim() : null;
                            }""")
                            
                            if price_text:
                                # Extract numeric price
                                price_match = re.search(r'(\d+[.,]\d+)', price_text)
                                if price_match:
                                    price = float(price_match.group(1).replace(',', '.'))
                                    formatted_price = await format_price(price)
                                    
                                    # Get weight from product description or title
                                    weight_text = await page.evaluate("""() => {
                                        const descElem = document.querySelector('.woocommerce-product-details__short-description');
                                        return descElem ? descElem.textContent.trim() : '';
                                    }""")
                                    
                                    # Try to extract weight from description
                                    weight_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(g|kg)', weight_text.lower())
                                    weight = weight_match.group(0) if weight_match else "N/A"
                                    
                                    # Calculate price per kg
                                    price_per_kg = await extract_price_per_kg(price, weight)
                                    
                                    products.append({
                                        "name": name,
                                        "price": formatted_price,
                                        "weight": weight,
                                        "price_per_kg": price_per_kg
                                    })
                                    
                                    logger.info(f"Added product without weight options: {name} - {weight} - {formatted_price}€ - {price_per_kg}€/kg")
                            
                            # Go back to the category page
                            logger.info(f"Finished processing {name}, returning to category page")
                            await page.goto(url)
                            await page.wait_for_load_state('domcontentloaded')
                            await page.wait_for_timeout(3000)  # Wait for page to fully load
                            
                        except Exception as e:
                            logger.error(f"Error processing product without weight options: {e}")
                            # Try to go back to the category page
                            try:
                                await page.goto(url)
                                await page.wait_for_load_state('domcontentloaded')
                                await page.wait_for_timeout(3000)
                            except:
                                pass
                            continue
                    
                except Exception as e:
                    logger.error(f"Error processing product {product_url}: {e}")
                    # Try to go back to the category page
                    try:
                        await page.goto(url)
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_timeout(3000)
                    except:
                        pass
                    continue
            
            await browser.close()
            
    except Exception as e:
        logger.error(f"Error in Cikade scraper: {e}")
    
    logger.info(f"Finished scraping. Found {len(products)} products")
    return products

if __name__ == "__main__":
    # Test the scraper
    asyncio.run(scrape_cikade(limit=2)) 