<template>
  <div class="view-container">
    <h1>Garsvielas</h1>
    <div class="scraper-form">
      <input
        v-model="url"
        type="text"
        placeholder="Enter URL to scrape"
        class="url-input"
      />
      <input
        v-model.number="maxProducts"
        type="number"
        min="1"
        placeholder="Max products"
        class="max-products-input"
      />
      <button @click="scrapeProducts" :disabled="loading" class="scrape-button">
        {{ loading ? "Scraping..." : "Scrape Products" }}
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
            <td>{{ product.pricePerKg }}</td>
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
  name: "GarsvielasView",
  data() {
    return {
      url: "https://www.garsvielas.lv/gar%C5%A1vielas",
      maxProducts: 10,
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
        const response = await axios.get("http://localhost:8001/scrape", {
          params: {
            url: this.url,
            limit: this.maxProducts,
            format: "json",
          },
        });

        this.products = response.data.map((item) => ({
          name: item.name,
          price: item.price,
          weight: item.weight,
          pricePerKg: item.price_per_kg,
        }));
      } catch (error) {
        console.error("Error:", error);
        this.error =
          error.response?.data?.message ||
          error.message ||
          "Failed to scrape products";
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
            `"${item.name}"`,
            `"${item.price}"`,
            `"${item.weight}"`,
            `"${item.pricePerKg || "N/A"}"`,
          ].join(",")
        ),
      ].join("\n");

      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "garsvielas_products.csv";
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

.max-products-input {
  width: 120px;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-right: 1rem;
  display: none;
}

.scrape-button,
.download-button {
  padding: 0.75rem 1.5rem;
  background-color: #ffabd5;
  color: rgb(0, 0, 0);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  font-weight: 500;
  font-size: 1rem;
}

.scrape-button:hover,
.download-button:hover {
  background-color: #ffabd5;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.scrape-button:active,
.download-button:active {
  transform: translateY(0);
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
