<script>
import NavBar from "./components/NavBar.vue";
import "./assets/styles.css";

export default {
  name: "App",
  components: {
    NavBar,
  },
};
</script>

<template>
  <div id="app">
    <NavBar />
    <router-view />
  </div>
</template>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  min-height: 100vh;
  background-color: #f8f9fa;
}

body {
  margin: 0;
  padding: 0;
}
</style>
