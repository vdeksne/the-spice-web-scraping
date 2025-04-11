# Web Scraping Project

This project is a web scraping application that allows users to scrape product information from various e-commerce websites. The application consists of a frontend built with Vue.js and a backend built with Flask.

## Features

### Safrans Scraper

- Scrapes product information from safrans.lv
- Extracts product names, prices, weights, and price per kg
- Supports CSV export of scraped data
- Handles both category pages and individual product pages

### Garsvielas Scraper

- Scrapes product information from garsvielas.lv
- Extracts product names, prices, weights, and price per kg
- Supports CSV export of scraped data
- Handles products with multiple weight options

### Cikade Scraper

- Scrapes product information from cikade.lv
- Extracts product names, prices, weights, and price per kg
- Supports CSV export of scraped data
- Handles products with multiple weight options
- Automatically processes all available weight options for each product
- Visual scraping process with browser automation

## Project Structure

```
.
├── backend/
│   ├── app.py                 # Flask backend server
│   ├── safrans_scraper.py     # Safrans scraping logic
│   ├── garsvielas_scraper.py  # Garsvielas scraping logic
│   └── cikade_scraper.py      # Cikade scraping logic
├── frontend/
│   ├── src/
│   │   ├── components/        # Vue components
│   │   ├── views/            # Vue views
│   │   ├── router/           # Vue router
│   │   └── App.vue           # Main Vue component
│   └── package.json          # Frontend dependencies
└── README.md                 # Project documentation
```

## Setup

### Backend Setup

1. Navigate to the backend directory:

   ```bash
   cd backend
   ```

2. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Start the Flask server:
   ```bash
   python app.py
   ```

### Frontend Setup

1. Navigate to the frontend directory:

   ```bash
   cd frontend
   ```

2. Install Node.js dependencies:

   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

## Usage

### Safrans Scraper

1. Navigate to the Safrans scraper page
2. Enter a URL from safrans.lv (e.g., https://www.safrans.lv/garsvielas_/garsvielas_un_garsaugi)
3. Click "Scrape Products"
4. View the scraped products in the table
5. Click "Download CSV" to export the data

### Garsvielas Scraper

1. Navigate to the Garsvielas scraper page
2. Enter a URL from garsvielas.lv
3. Click "Scrape Products"
4. View the scraped products in the table
5. Click "Download CSV" to export the data

### Cikade Scraper

1. Navigate to the Cikade scraper page
2. Enter a URL from cikade.lv (default: https://cikade.lv/product-category/garsvielas/)
3. Set the maximum number of products to scrape (optional)
4. Click "Scrape Products"
5. Watch the automated scraping process in the browser
6. View the scraped products in the table
7. Click "Download CSV" to export the data

## Dependencies

### Backend

- Flask
- Flask-CORS
- BeautifulSoup4
- Requests
- Playwright

### Frontend

- Vue.js
- Vue Router
- Axios

## Contributing

1. Fork the repository
2. Create a new branch for your feature
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

# web-scraping
