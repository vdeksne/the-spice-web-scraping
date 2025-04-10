<script setup>
import { ref } from "vue";
import axios from "axios";

const url = ref("");
const isLoading = ref(false);
const error = ref("");
const result = ref(null);
const isSingleProduct = ref(false);

const validateUrl = (url) => {
  return url.startsWith("https://www.safrans.lv");
};

const scrapeWebsite = async () => {
  if (!url.value) {
    error.value = "Please enter a URL";
    return;
  }

  if (!validateUrl(url.value)) {
    error.value = "Please enter a valid Safrans website URL";
    return;
  }

  try {
    isLoading.value = true;
    error.value = "";
    result.value = null;

    console.log(`Sending request to backend: ${url.value}`);

    // Send the URL as is, without encoding (axios will handle the encoding)
    const response = await axios.get(`http://localhost:8000/scrape`, {
      params: {
        url: url.value,
      },
    });

    console.log("Response received:", response.data);

    if (response.data && response.data.csv_content) {
      result.value = response.data.csv_content;
      // Create and download CSV file
      const blob = new Blob([response.data.csv_content], { type: "text/csv" });
      const link = document.createElement("a");
      link.href = window.URL.createObjectURL(blob);
      link.download = "scraped_data.csv";
      link.click();
      window.URL.revokeObjectURL(link.href);
    } else {
      error.value = "No data received from the server";
    }
  } catch (err) {
    console.error("Error:", err);
    if (err.response) {
      console.error("Response error:", err.response.data);
      error.value =
        err.response.data.detail ||
        "An error occurred while scraping the website";
    } else if (err.request) {
      console.error("Request error:", err.request);
      error.value =
        "Could not connect to the server. Please make sure the backend is running.";
    } else {
      error.value = "An error occurred while making the request";
    }
  } finally {
    isLoading.value = false;
  }
};

const updateUrlType = (value) => {
  isSingleProduct.value = value.includes("garsvielas_un_garsaugi");
};
</script>

<template>
  <div class="container">
    <h1>Safrans Web Scraping Tool</h1>
    <div class="description">
      <p v-if="!isSingleProduct">
        Enter the main Safrans website URL to scrape up to 10 products
      </p>
      <p v-else>Enter a specific product page URL to scrape that product</p>
    </div>
    <div class="input-container">
      <input
        v-model="url"
        type="text"
        @input="updateUrlType($event.target.value)"
        :placeholder="
          isSingleProduct
            ? 'Enter product URL (e.g., https://www.safrans.lv/garsvielas_/garsvielas_un_garsaugi/anisa_seklas)'
            : 'Enter website URL (e.g., https://www.safrans.lv)'
        "
        @keyup.enter="scrapeWebsite"
      />
      <button @click="scrapeWebsite" :disabled="isLoading">
        {{
          isLoading
            ? "Scraping..."
            : isSingleProduct
            ? "Scrape Product"
            : "Scrape Website"
        }}
      </button>
    </div>
    <div v-if="error" class="error">
      {{ error }}
    </div>
    <div v-if="isLoading" class="loading">
      <p>Scraping in progress... This may take a few moments.</p>
      <p v-if="!isSingleProduct" class="note">
        Note: The crawler will collect up to 10 products from the website.
      </p>
    </div>
    <div v-if="result" class="result">
      <h3>Preview of scraped data:</h3>
      <pre>{{ result }}</pre>
    </div>
  </div>
</template>

<style scoped>
.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  text-align: center;
}

h1 {
  color: white;
  margin-bottom: 1rem;
}

.description {
  color: #666;
  margin-bottom: 2rem;
}

.input-container {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

input {
  flex: 1;
  padding: 0.5rem;
  font-size: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

button {
  padding: 0.5rem 1rem;
  font-size: 1rem;
  background-color: white;
  color: black;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

button:hover {
  background-color: #43f1dd;
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.error {
  color: #dc3545;
  margin-top: 1rem;
  padding: 0.5rem;
  background-color: #f8d7da;
  border-radius: 4px;
}

.loading {
  margin-top: 1rem;
  color: #0d6efd;
  font-style: italic;
}

.note {
  font-size: 0.9em;
  color: #666;
  margin-top: 0.5rem;
}

.result {
  margin-top: 2rem;
  text-align: left;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.result pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: monospace;
  margin: 0;
  padding: 1rem;
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 4px;
  color: black;
}

h3 {
  color: black;
}
</style>
