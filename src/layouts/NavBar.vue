<template>
  <nav class="navbar navbar-expand navbar-dark bg-dark">
    <router-link class="navbar-brand" :to="{ name: 'Home' }">
      <svg
        width="1em"
        height="1em"
        viewBox="0 0 16 16"
        class="bi bi-lightning"
        fill="currentColor"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          fill-rule="evenodd"
          d="M11.251.068a.5.5 0 0 1 .227.58L9.677 6.5H13a.5.5 0 0 1 .364.843l-8 8.5a.5.5 0 0 1-.842-.49L6.323 9.5H3a.5.5 0 0 1-.364-.843l8-8.5a.5.5 0 0 1 .615-.09zM4.157 8.5H7a.5.5 0 0 1 .478.647L6.11 13.59l5.732-6.09H9a.5.5 0 0 1-.478-.647L9.89 2.41 4.157 8.5z"
        />
      </svg>
      e4futuregrid</router-link
    >
    <div class="collapse navbar-collapse" id="navbarSupportedContent">
      <ul class="navbar-nav mr-auto">
        <li class="nav-item">
          <router-link class="nav-link" :to="{ name: 'Home' }">Home</router-link>
        </li>
        <li class="nav-item">
          <router-link class="nav-link" :to="{ name: 'SimulateNetworkAPI' }">Simulate</router-link>
        </li>
        <li class="nav-item">
          <router-link class="nav-link" :to="{ name: 'Resources' }">Resources</router-link>
        </li>
      </ul>
    </div>
  </nav>
  <div style="margin: 1.5rem;">
    <router-view></router-view>
  </div>
</template>

<script>
export default {
  name: "NavBar"
};
</script>
