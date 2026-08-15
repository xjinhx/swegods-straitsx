<script setup>
import { ref } from "vue";
import AgentDemo from "./views/AgentDemo.vue";
import MerchantDashboard from "./views/MerchantDashboard.vue";

const tab = ref("demo");
const showHelp = ref(false);
const copied = ref(false);
const cmd = "python agent.py 'buy me a birthday gift under $50'";

function copyCmd() {
  navigator.clipboard?.writeText(cmd);
  copied.value = true;
  setTimeout(() => (copied.value = false), 1500);
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand"><span class="dot"></span> AgentMart</div>
      <nav class="tabs">
        <button :class="{ active: tab === 'demo' }" @click="tab = 'demo'">Agent view</button>
        <button :class="{ active: tab === 'merchant' }" @click="tab = 'merchant'">Merchant dashboard</button>
        <div v-if="tab === 'demo'" class="help-wrap">
          <button class="help-fab" :class="{ active: showHelp }" @click="showHelp = !showHelp" aria-label="How to run the demo agent">?</button>
          <div v-if="showHelp" class="help-popover">
            <span class="eyebrow">Run the demo agent</span>
            <p class="hint">
              The shopping agent is a standalone Claude-powered script (<code class="mono">demo_agent/agent.py</code>)
              that calls this exact API over HTTP — nothing here is simulated.
            </p>
            <div class="cmd-row">
              <code class="mono cmd">{{ cmd }}</code>
              <button @click="copyCmd">{{ copied ? "Copied" : "Copy" }}</button>
            </div>
          </div>
        </div>
      </nav>
    </header>
    <main class="content">
      <AgentDemo v-if="tab === 'demo'" />
      <MerchantDashboard v-else />
    </main>
  </div>
</template>
