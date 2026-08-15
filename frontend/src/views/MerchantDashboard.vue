<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { api } from "../api";
import ActivityFeed from "../components/ActivityFeed.vue";
import TrustBreakdown from "../components/TrustBreakdown.vue";
import OrderTimeline from "../components/OrderTimeline.vue";
import RuleBuilder from "../components/RuleBuilder.vue";

const orders = ref([]);
const agents = ref([]);
const selectedAgentId = ref(null);
const selectedOrderId = ref(null);
const overriding = ref(null);
const copied = ref(false);
let timer = null;

function toggleOrder(orderId) {
  selectedOrderId.value = selectedOrderId.value === orderId ? null : orderId;
}

const STAGES = [
  { key: "discover", label: "Discover", matches: [] },
  { key: "identify", label: "Identify", matches: ["identify"] },
  { key: "checkout", label: "Checkout", matches: ["checkout", "blocked"] },
  { key: "authorise", label: "Authorise", matches: ["authorise"] },
  { key: "prove", label: "Prove", matches: ["receipt"] },
];
const recentEvents = ref([]);
const activeIndex = computed(() => {
  if (!recentEvents.value.length) return -1;
  return STAGES.findIndex((s) => s.matches.includes(recentEvents.value[0].step));
});

const cmd = "python agent.py 'buy me a birthday gift under $50'";
function copyCmd() {
  navigator.clipboard?.writeText(cmd);
  copied.value = true;
  setTimeout(() => (copied.value = false), 1500);
}

async function refresh() {
  [orders.value, agents.value, recentEvents.value] = await Promise.all([
    api.orders(), api.agents(), api.activityFeed(1),
  ]);
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
      <span class="eyebrow">Run the demo agent</span>
      <p class="hint">
        The shopping agent is a standalone Claude-powered script (<code class="mono">demo_agent/agent.py</code>)
        that calls this exact API over HTTP — nothing here is simulated.
      </p>
      <div class="cmd-row">
        <code class="mono cmd">{{ cmd }}</code>
        <button @click="copyCmd">{{ copied ? "Copied" : "Copy" }}</button>
      </div>
      <ol class="stages">
        <li v-for="(s, i) in STAGES" :key="s.key" :class="{ active: i === activeIndex, done: i < activeIndex }">
          <span class="stage-dot"></span>{{ s.label }}
        </li>
      </ol>
    </section>

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
      <div v-if="!orders.length" class="empty">No orders yet — run the demo agent (command above).</div>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Order</th><th>Agent</th><th>Item</th><th>Amount</th>
              <th>Trust</th><th>Required</th><th>Commercial</th><th>Status</th><th></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="o in orders" :key="o.order_id">
              <tr class="order-row" @click="toggleOrder(o.order_id)">
                <td class="mono">{{ o.order_id }}</td>
                <td>{{ o.agent_name }}</td>
                <td>{{ o.product_name }}</td>
                <td class="tabular">${{ o.amount_sgd.toFixed(2) }}</td>
                <td class="tabular">{{ Math.round(o.trust_score_at_checkout) }}</td>
                <td class="tabular">{{ Math.round(o.required_trust) }}</td>
                <td class="tabular" :class="{ warn: o.commercial_validity_score < 50 }">{{ Math.round(o.commercial_validity_score) }}</td>
                <td><span class="pill" :class="o.status">{{ o.status.replace("_", " ") }}</span></td>
                <td>
                  <button v-if="o.status === 'blocked'" class="primary" :disabled="overriding === o.order_id" @click.stop="doOverride(o)">
                    {{ overriding === o.order_id ? "Approving…" : "Override" }}
                  </button>
                </td>
              </tr>
              <tr v-if="selectedOrderId === o.order_id" class="timeline-row">
                <td colspan="9">
                  <OrderTimeline :order-id="o.order_id" />
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <p class="hint">Click a row for the per-stage trust score timeline.</p>
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

.order-row { cursor: pointer; }
.order-row:hover { background: var(--surface-2); }
.order-row td.warn { color: var(--warn); font-weight: 700; }
.timeline-row td { padding: 0.9rem 0.7rem 1.1rem; background: var(--surface-2); border-radius: 8px; }

.cmd-row { display: flex; gap: 0.6rem; align-items: center; margin-top: 0.6rem; }
.cmd { background: var(--surface-2); padding: 0.55rem 0.8rem; border-radius: 6px; flex: 1; font-size: 0.85rem; overflow-x: auto; }

.stages { list-style: none; display: flex; gap: 0; margin: 1rem 0 0; padding: 0; }
.stages li {
  flex: 1; display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 0.4rem;
  border-bottom: 2px solid var(--line); color: var(--ink-faint); font-size: 0.85rem; font-weight: 600;
}
.stage-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--line-strong); flex: none; }
.stages li.done { color: var(--ink-muted); border-color: var(--accent); }
.stages li.done .stage-dot { background: var(--accent); }
.stages li.active { color: var(--accent-ink); border-color: var(--accent); }
.stages li.active .stage-dot { background: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
</style>
