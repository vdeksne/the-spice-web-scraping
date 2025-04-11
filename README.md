# Web Scraping Tool

A web scraping tool built with Python (FastAPI) and Vue 3 that allows you to scrape product information from websites and download the data in CSV format.

## Features

- Scrape product information from websites
- Extract product names, prices, and price per kg
- Download data in CSV format
- Modern and responsive UI

## Prerequisites

- Python 3.8+
- Node.js 14+
- npm

## Setup and Running

### Backend Setup

1. Navigate to the backend directory:

   ```bash
   cd backend
   ```

2. Create and activate virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the backend server:
   ```bash
   uvicorn main:app --reload
   ```

The backend will be running at http://localhost:8000

### Frontend Setup

1. Navigate to the frontend directory:

   ```bash
   cd frontend
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```

The frontend will be running at http://localhost:5173

## Usage

1. Open your browser and go to http://localhost:5173
2. Enter the website URL you want to scrape (e.g., https://www.garsvielas.lv)
3. Click "Scrape Website" or press Enter
4. The data will be automatically downloaded as a CSV file

## Note

Make sure both the backend and frontend servers are running simultaneously for the application to work properly.

# web-scraping
