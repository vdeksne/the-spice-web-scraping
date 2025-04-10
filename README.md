# Product Scraper

A web application that scrapes product information from various e-commerce websites.

## Project Structure

- **Frontend**: Angular application
- **Backend**: Python Flask server with web scraping functionality

## Features

- Scrape products from Garsvielas.lv
- Scrape products from Safrans.lv
- Display product information in a table format
- Export data to CSV

## Setup

### Backend

1. Navigate to the backend directory:

   ```
   cd backend
   ```

2. Create and activate a virtual environment:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Run the Flask server:
   ```
   python app.py
   ```

### Frontend

1. Navigate to the frontend directory:

   ```
   cd frontend
   ```

2. Install dependencies:

   ```
   npm install
   ```

3. Run the development server:
   ```
   npm run dev
   ```

## Usage

1. Open your browser and navigate to `http://localhost:5173`
2. Enter the URL of the website you want to scrape
3. Click "Scrape" to start the scraping process
4. View the results in the table
5. Export the data to CSV if needed

## Technologies Used

- **Frontend**: Angular, Vue.js, TypeScript
- **Backend**: Python, Flask, BeautifulSoup, Requests
- **Other**: Playwright for browser automation
