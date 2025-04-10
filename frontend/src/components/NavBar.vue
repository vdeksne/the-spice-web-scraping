<template>
  <nav class="navbar">
    <div class="navbar-brand"></div>

    <div class="navbar-menu">
      <div class="navbar-start">
        <router-link to="/" class="navbar-item"> Safrāns </router-link>

        <router-link to="/garsvielas" class="navbar-item">
          Garsvielas
        </router-link>

        <router-link to="/cikade" class="navbar-item"> Cikade </router-link>
      </div>
    </div>
  </nav>
</template>

<script>
export default {
  name: "NavBar",
};
</script>

<style scoped>
.navbar {
  background-color: #ffffff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  justify-content: center;
}

.navbar-brand {
  display: flex;
  align-items: center;
}

.logo {
  height: 40px;
  width: auto;
}

.navbar-menu {
  display: flex;
  align-items: center;
}

.navbar-start {
  display: flex;
  gap: 1.5rem;
}

.navbar-item {
  color: #2c3e50;
  text-decoration: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: all 0.3s;
  font-weight: 500;
  font-size: 1.1rem;
}

.navbar-item:hover {
  background-color: #f5f5f5;
  color: #4a90e2;
}

.router-link-active {
  color: #4a90e2;
  font-weight: bold;
  background-color: rgba(74, 144, 226, 0.1);
}
</style>
