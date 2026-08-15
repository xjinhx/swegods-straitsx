<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { api } from "../api";
import ActivityFeed from "../components/ActivityFeed.vue";
import TrustBreakdown from "../components/TrustBreakdown.vue";
import OrderTimeline from "../components/OrderTimeline.vue";
import TrustTrajectoryChart from "../components/TrustTrajectoryChart.vue";
import RuleBuilder from "../components/RuleBuilder.vue";

const orders = ref([]);
const agents = ref([]);
const selectedAgentId = ref(null);
const selectedOrderId = ref(null);
const overriding = ref(null);
let timer = null;

function toggleOrder(orderId) {
  selectedOrderId.value = selectedOrderId.value === orderId ? null : orderId;
}

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

async function doRevoke(agentId) {
  await api.revokeAgent(agentId);
  await refresh();
}

async function doReinstate(agentId) {
  await api.reinstateAgent(agentId);
  await refresh();
}

// "Today" means the viewer's local calendar day, not a UTC slice — a judge looking at
// this at 1am SGT should see 1am-to-now, not get yesterday's UTC date back.
function isToday(isoString) {
  const d = new Date(isoString);
  const now = new Date();
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
}
const dateFilter = ref("today"); // "today" | "all"
const todayOrders = computed(() => orders.value.filter((o) => isToday(o.created_at)));
const scopedOrders = computed(() => (dateFilter.value === "today" ? todayOrders.value : orders.value));

const passedCount = computed(() => scopedOrders.value.filter((o) => ["approved", "completed", "approved_override"].includes(o.status)).length);
const blockedCount = computed(() => scopedOrders.value.filter((o) => o.status === "blocked").length);
const settledCount = computed(() => scopedOrders.value.filter((o) => o.status === "completed").length);
const passRate = computed(() => (scopedOrders.value.length ? Math.round((passedCount.value / scopedOrders.value.length) * 100) : 0));

const DENIAL_REASON_LABELS = {
  identity_verification_failure: "Unverified identity",
  commercial_validity_failure: "Tampered / stale price",
  insufficient_trust: "Insufficient trust",
  straitsx_error: "StraitsX settlement error",
};
const DENIAL_REASON_COLORS = {
  identity_verification_failure: "var(--reason-3)",
  commercial_validity_failure: "var(--reason-1)",
  insufficient_trust: "var(--reason-2)",
  straitsx_error: "var(--ink-faint)",
};
const blockedBreakdown = computed(() => {
  const counts = {};
  for (const o of scopedOrders.value) {
    if (!o.denial_reason) continue;
    counts[o.denial_reason] = (counts[o.denial_reason] || 0) + 1;
  }
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const max = entries.length ? entries[0][1] : 1;
  return entries.map(([reason, count]) => ({
    reason,
    count,
    label: DENIAL_REASON_LABELS[reason] || reason,
    color: DENIAL_REASON_COLORS[reason] || "var(--ink-faint)",
    pct: Math.round((count / max) * 100),
  }));
});
</script>

<template>
  <div class="grid">
    <section class="panel span-2" v-if="orders.length">
      <div class="outcomes-head">
        <span class="eyebrow">{{ dateFilter === "today" ? "Today's outcomes" : "All-time outcomes" }}</span>
        <div class="tabs outcomes-toggle">
          <button :class="{ active: dateFilter === 'today' }" @click="dateFilter = 'today'">Today</button>
          <button :class="{ active: dateFilter === 'all' }" @click="dateFilter = 'all'">All time</button>
        </div>
      </div>
      <p v-if="dateFilter === 'today' && !todayOrders.length" class="empty">No orders yet today.</p>
      <div v-else class="kpi-row">
        <div class="kpi-tile">
          <div class="kpi-value tabular">{{ passedCount }}</div>
          <div class="kpi-label"><span class="kpi-dot good"></span>Purchases passed</div>
        </div>
        <div class="kpi-tile">
          <div class="kpi-value tabular">{{ blockedCount }}</div>
          <div class="kpi-label"><span class="kpi-dot warn"></span>Purchases blocked</div>
        </div>
        <div class="kpi-tile">
          <div class="kpi-value tabular">{{ passRate }}%</div>
          <div class="kpi-label">Pass rate</div>
        </div>
        <div class="kpi-tile">
          <div class="kpi-value tabular">{{ settledCount }}</div>
          <div class="kpi-label"><span class="kpi-dot accent"></span>Settled via StraitsX</div>
        </div>
      </div>

      <div v-if="blockedBreakdown.length" class="breakdown-block">
        <span class="eyebrow" style="display:block; margin-bottom:0.9rem;">Why purchases were blocked</span>
        <div class="bar-chart">
          <div v-for="b in blockedBreakdown" :key="b.reason" class="bar-row">
            <span class="bar-cat-label">{{ b.label }}</span>
            <div class="bar-track"><div class="bar-fill-h" :style="{ width: b.pct + '%', background: b.color }"></div></div>
            <span class="bar-value tabular">{{ b.count }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="panel span-2" v-if="orders.length && agents.length">
      <div>
        <span class="eyebrow">Trust score across the pipeline</span>
        <p class="hint" style="margin-top:0.35rem;">
          The score isn't frozen at <code class="mono">/identify</code> — it's recomputed at every stage,
          and a high-trust agent can still fail the <code class="mono">/checkout</code> gate.
        </p>
      </div>
      <TrustTrajectoryChart :orders="orders" :agents="agents" />
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
        <TrustBreakdown v-if="selectedAgent()" :agent="selectedAgent()" @revoke="doRevoke" @reinstate="doReinstate" />
      </template>
    </section>

    <section class="panel span-2">
      <span class="eyebrow">Orders</span>
      <div v-if="!orders.length" class="empty">No orders yet — run the demo agent (see the "?" on Agent view).</div>
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

.kpi-row { display: flex; gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; margin-top: 0.9rem; }
.kpi-tile { flex: 1; background: var(--surface); padding: 1rem 1.1rem; min-width: 0; }
.kpi-value { font-family: var(--mono); font-size: 1.7rem; font-weight: 600; line-height: 1; color: var(--ink); }
.kpi-label { display: flex; align-items: center; gap: 0.4rem; font-size: 0.76rem; color: var(--ink-muted); margin-top: 0.4rem; }
.kpi-dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
.kpi-dot.good { background: var(--good); }
.kpi-dot.warn { background: var(--warn); }
.kpi-dot.accent { background: var(--accent); }
@media (max-width: 700px) { .kpi-row { flex-wrap: wrap; } .kpi-tile { flex: 1 1 45%; } }

.outcomes-head { display: flex; align-items: center; justify-content: space-between; }
.outcomes-toggle { margin-left: 0; gap: 0.2rem; }
.outcomes-toggle button { padding: 0.3rem 0.7rem; font-size: 0.78rem; }
.breakdown-block { margin-top: 1.4rem; padding-top: 1.2rem; border-top: 1px solid var(--line); }
.bar-chart { display: flex; flex-direction: column; gap: 0.7rem; }
.bar-row { display: grid; grid-template-columns: 11rem 1fr 2.4rem; align-items: center; gap: 0.8rem; }
.bar-cat-label { font-size: 0.82rem; color: var(--ink); }
.bar-track { height: 20px; background: var(--surface-2); border-radius: 4px; overflow: hidden; }
.bar-fill-h { height: 100%; border-radius: 0 4px 4px 0; }
.bar-value { font-family: var(--mono); font-size: 0.85rem; font-weight: 600; text-align: right; }

.order-row { cursor: pointer; }
.order-row:hover { background: var(--surface-2); }
.order-row td.warn { color: var(--warn); font-weight: 700; }
.timeline-row td { padding: 0.9rem 0.7rem 1.1rem; background: var(--surface-2); border-radius: 8px; }
</style>
