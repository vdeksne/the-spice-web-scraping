<template>
  <div class="container">
    <h1>Cikade Scraper</h1>
    <div class="form-group">
      <label for="url">Enter Cikade URL:</label>
      <input
        type="text"
        id="url"
        v-model="url"
        placeholder="https://cikade.lv/product-category/garsvielas/"
        class="form-control"
      />
    </div>
    <div class="form-group">
      <label for="limit">Product Limit (optional):</label>
      <input
        type="number"
        id="limit"
        v-model="limit"
        placeholder="Leave empty for all products"
        class="form-control"
      />
    </div>
    <button @click="scrapeProducts" :disabled="loading" class="scrape-button">
      {{ loading ? "Scraping..." : "Scrape Products" }}
    </button>

    <!-- Progress bar -->
    <div v-if="loading" class="progress-container">
      <div class="progress">
        <div
          class="progress-bar"
          role="progressbar"
          :style="{ width: progress + '%' }"
          :aria-valuenow="progress"
          aria-valuemin="0"
          aria-valuemax="100"
        >
          {{ progress }}%
        </div>
      </div>
      <div class="progress-text">
        Scraping products... {{ progress }}% complete
      </div>
    </div>

    <div v-if="error" class="alert alert-danger mt-3">
      {{ error }}
    </div>

    <div v-if="products.length > 0" class="mt-4">
      <h2>Results ({{ products.length }} products)</h2>
      <div class="table-responsive">
        <table class="table table-striped">
          <thead>
            <tr>
              <th>Product Name</th>
              <th>Price (€)</th>
              <th>Weight</th>
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
      </div>
      <button @click="downloadCSV" class="btn btn-success mt-3">
        Download CSV
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: "CikadeView",
  data() {
    return {
      url: "https://cikade.lv/product-category/garsvielas/",
      limit: null,
      products: [],
      loading: false,
      error: null,
      progress: 0,
      progressInterval: null,
    };
  },
  methods: {
    async scrapeProducts() {
      this.loading = true;
      this.error = null;
      this.products = [];
      this.progress = 0;

      // Start polling for progress updates
      this.startProgressPolling();

      try {
        let url = `http://localhost:8001/scrape?url=${encodeURIComponent(
          this.url
        )}&format=json`;
        if (this.limit) {
          url += `&limit=${this.limit}`;
        }

        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        // Stop polling for progress updates
        this.stopProgressPolling();

        if (data.error) {
          throw new Error(data.error);
        }

        this.products = data;
      } catch (error) {
        this.error = `Error: ${error.message}`;
        this.stopProgressPolling();
      } finally {
        this.loading = false;
        this.progress = 100; // Ensure progress is 100% when done
      }
    },
    startProgressPolling() {
      // Poll for progress updates every 500ms
      this.progressInterval = setInterval(async () => {
        try {
          const response = await fetch("http://localhost:8001/progress");
          if (response.ok) {
            const data = await response.json();
            this.progress = data.progress;

            // If progress is 100%, stop polling
            if (this.progress === 100) {
              this.stopProgressPolling();
            }
          }
        } catch (error) {
          console.error("Error fetching progress:", error);
        }
      }, 500);
    },
    stopProgressPolling() {
      if (this.progressInterval) {
        clearInterval(this.progressInterval);
        this.progressInterval = null;
      }
    },
    downloadCSV() {
      // Create CSV content
      let csvContent = "Product Name,Price (€),Weight,Price per kg (€)\n";

      this.products.forEach((product) => {
        const name = product.name.replace(/,/g, " ");
        const price = product.price || "N/A";
        const weight = product.weight || "N/A";
        const pricePerKg = product.price_per_kg || "N/A";

        csvContent += `${name},${price},${weight},${pricePerKg}\n`;
      });

      // Create a blob and download link
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", "cikade_products.csv");
      link.style.visibility = "hidden";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    },
  },
  beforeUnmount() {
    // Clean up interval when component is unmounted
    this.stopProgressPolling();
  },
};
</script>

<style scoped>
@import url("https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap");

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  font-family: "Poppins", sans-serif;
}

.form-group {
  margin-bottom: 15px;
}

.form-control {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-success {
  background-color: #28a745;
  color: white;
}

.btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.alert {
  padding: 10px;
  border-radius: 4px;
  margin-top: 15px;
}

.alert-danger {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

.table th,
.table td {
  padding: 8px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.table th {
  background-color: #f2f2f2;
}

.progress-container {
  margin-top: 20px;
  margin-bottom: 20px;
}

.progress {
  height: 25px;
  background-color: #f5f5f5;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background-color: #007bff;
  color: white;
  text-align: center;
  line-height: 25px;
  transition: width 0.3s ease;
}

.progress-text {
  margin-top: 8px;
  text-align: center;
  font-weight: bold;
  color: #007bff;
}
</style>
