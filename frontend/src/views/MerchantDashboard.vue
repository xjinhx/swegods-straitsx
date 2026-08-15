<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import { api } from "../api";
import ActivityFeed from "../components/ActivityFeed.vue";
import TrustBreakdown from "../components/TrustBreakdown.vue";
import RuleBuilder from "../components/RuleBuilder.vue";

const orders = ref([]);
const agents = ref([]);
const selectedAgentId = ref(null);
const overriding = ref(null);
let timer = null;

async function refresh() {
  [orders.value, agents.value] = await Promise.all([api.orders(), api.agents()]);
  if (!selectedAgentId.value && agents.value.length) selectedAgentId.value = agents.value[0].agent_id;
}

onMounted(() => {
  refresh();
  timer = setInterval(refresh, 2500);
});
onUnmounted(() => clearInterval(timer));

const selectedAgent = () => agents.value.find((a) => a.agent_id === selectedAgentId.value);

async function doOverride(order) {
  overriding.value = order.order_id;
  try {
    await api.override(order.order_id, "approved from merchant dashboard");
    await refresh();
  } finally {
    overriding.value = null;
  }
}
</script>

<template>
  <div class="grid">
    <section class="panel span-2">
      <span class="eyebrow">Live activity — merchant view</span>
      <ActivityFeed :limit="25" />
    </section>

    <section class="panel">
      <span class="eyebrow">Trust score breakdown</span>
      <div v-if="!agents.length" class="empty">No agents yet.</div>
      <template v-else>
        <select v-model="selectedAgentId" class="agent-select">
          <option v-for="a in agents" :key="a.agent_id" :value="a.agent_id">
            {{ a.name }} — {{ Math.round(a.trust_score) }}
          </option>
        </select>
        <TrustBreakdown v-if="selectedAgent()" :agent="selectedAgent()" />
      </template>
    </section>

    <section class="panel span-2">
      <span class="eyebrow">Orders</span>
      <div v-if="!orders.length" class="empty">No orders yet — run the demo agent from the Agent view.</div>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Order</th><th>Agent</th><th>Item</th><th>Amount</th>
              <th>Trust</th><th>Required</th><th>Status</th><th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="o in orders" :key="o.order_id">
              <td class="mono">{{ o.order_id }}</td>
              <td>{{ o.agent_name }}</td>
              <td>{{ o.product_name }}</td>
              <td class="tabular">${{ o.amount_sgd.toFixed(2) }}</td>
              <td class="tabular">{{ Math.round(o.trust_score_at_checkout) }}</td>
              <td class="tabular">{{ Math.round(o.required_trust) }}</td>
              <td><span class="pill" :class="o.status">{{ o.status.replace("_", " ") }}</span></td>
              <td>
                <button v-if="o.status === 'blocked'" class="primary" :disabled="overriding === o.order_id" @click="doOverride(o)">
                  {{ overriding === o.order_id ? "Approving…" : "Override" }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="orders.some((o) => o.status === 'blocked')" class="hint">
        Blocked orders stay blocked until an agent tries <code class="mono">/authorise</code> again — overriding
        here doesn't charge the card itself, it just clears the gate.
      </p>
    </section>

    <section class="panel span-2">
      <span class="eyebrow">Rule builder — /checkout reads these live</span>
      <RuleBuilder />
    </section>
  </div>
</template>

<style scoped>
.grid { display: grid; gap: 1.1rem; grid-template-columns: 1fr 1fr; align-items: start; }
.span-2 { grid-column: 1 / -1; }
@media (max-width: 900px) {
  .grid { grid-template-columns: 1fr; }
}
.agent-select { width: 100%; margin-bottom: 1rem; }
.hint { color: var(--ink-faint); font-size: 0.82rem; margin-top: 0.7rem; }
</style>
