<template>
  <div class="view-container">
    <h1>Safrans</h1>
    <div class="scraper-form">
      <input
        v-model="url"
        type="text"
        placeholder="Enter URL to scrape"
        class="url-input"
      />
      <button @click="scrapeProducts" class="scrape-button">
        Scrape Products
      </button>
    </div>

    <div v-if="loading" class="loading">Scraping products...</div>

    <div v-if="error" class="error">
      {{ error }}
    </div>

    <div v-if="products.length > 0" class="results">
      <h2>Scraped Products</h2>
      <table>
        <thead>
          <tr>
            <th>Product Name</th>
            <th>Price (€)</th>
            <th>Weight (g)</th>
            <th>Price per kg (€)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(product, index) in products" :key="index">
            <td>{{ product.name }}</td>
            <td>{{ product.price }}</td>
            <td>{{ product.weight }}</td>
            <td>{{ product.price_per_kg }}</td>
          </tr>
        </tbody>
      </table>
      <button @click="downloadCSV" class="download-button">Download CSV</button>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import "../assets/styles.css";

export default {
  name: "HomeView",
  data() {
    return {
      url: "https://www.safrans.lv/garsvielas_/garsvielas_un_garsaugi",
      products: [],
      loading: false,
      error: null,
    };
  },
  methods: {
    async scrapeProducts() {
      this.loading = true;
      this.error = null;
      this.products = [];

      try {
        const response = await fetch(
          `http://localhost:8003/scrape?url=${encodeURIComponent(this.url)}`
        );
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        // Parse CSV content
        const csvContent = data.csv_content;
        const lines = csvContent.split("\n");
        const headers = lines[0].split(",");

        for (let i = 1; i < lines.length; i++) {
          if (lines[i].trim()) {
            const values = lines[i].split(",");
            const product = {
              name: values[0],
              price: values[1],
              weight: values[2],
              price_per_kg: values[3],
            };
            this.products.push(product);
          }
        }
      } catch (error) {
        console.error("Error:", error);
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    },
    downloadCSV() {
      const headers = [
        "Product Name",
        "Price (€)",
        "Weight (g)",
        "Price per kg (€)",
      ];
      const csvContent = [
        headers.join(","),
        ...this.products.map((item) =>
          [
            `"${item.name || ""}"`,
            `"${item.price || "N/A"}"`,
            `"${item.weight || "N/A"}"`,
            `"${item.price_per_kg || "N/A"}"`,
          ].join(",")
        ),
      ].join("\n");

      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "safrans_products.csv";
      link.click();
    },
  },
};
</script>

<style scoped>
.view-container {
  padding: 2rem;
}

.scraper-form {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.url-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.scrape-button,
.download-button {
  padding: 0.5rem 1rem;
  background-color: #4a90e2;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.scrape-button:hover,
.download-button:hover {
  background-color: #357abd;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.error {
  color: #dc3545;
  padding: 1rem;
  margin: 1rem 0;
  background-color: #f8d7da;
  border-radius: 4px;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 2rem 0;
}

th,
td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

th {
  background-color: #f8f9fa;
  font-weight: bold;
}

tr:hover {
  background-color: #f5f5f5;
}
</style>
