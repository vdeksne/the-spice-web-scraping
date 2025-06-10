<template>
  <img src="../assets/paxio_transparent.png" alt="logo" class="logo" />
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
  height: 10rem;
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
  background-color: #db83af;
  color: #090a10;
}

.router-link-active {
  color: #090a10;
  font-weight: bold;
  background-color: #ffabd5;
}

@media (max-width: 500px) {
  .navbar-start {
    display: flex;
    gap: 1.5rem;
    flex-direction: column;
  }
}
</style>
