<script setup>
import { ref } from "vue";
import AgentDemo from "./views/AgentDemo.vue";
import MerchantDashboard from "./views/MerchantDashboard.vue";

const tab = ref("demo");
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand"><span class="dot"></span> AgentMart</div>
      <nav class="tabs">
        <button :class="{ active: tab === 'demo' }" @click="tab = 'demo'">Agent view</button>
        <button :class="{ active: tab === 'merchant' }" @click="tab = 'merchant'">Merchant dashboard</button>
      </nav>
    </header>
    <main class="content">
      <AgentDemo v-if="tab === 'demo'" />
      <MerchantDashboard v-else />
    </main>
  </div>
</template>
