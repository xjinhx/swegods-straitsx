<script setup>
import { computed, ref, watch } from "vue";
import { api } from "../api";

const props = defineProps({
  orders: { type: Array, required: true },
  agents: { type: Array, required: true },
});

const SERIES_COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)"];
const PLOT = { left: 70, right: 700, top: 30, bottom: 250 };
const STAGE_X = { identify: 100, checkout: 340, authorise: 560 };

function scoreY(score) {
  return PLOT.bottom - (score / 100) * (PLOT.bottom - PLOT.top);
}

// Pick up to 3 representative recent orders: one clean completion, one blocked for a
// tampered/stale price, one blocked for insufficient trust — the three outcomes the
// live_trust_score blend is actually built to distinguish.
const candidates = computed(() => {
  const byRecency = [...props.orders].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  const picks = [
    { status: "completed", denial_reason: null, label: "Completed" },
    { status: "blocked", denial_reason: "commercial_validity_failure", label: "Blocked — tampered price" },
    { status: "blocked", denial_reason: "insufficient_trust", label: "Blocked — insufficient trust" },
  ];
  const result = [];
  for (const p of picks) {
    const match = byRecency.find((o) => o.status === p.status && (p.denial_reason === null || o.denial_reason === p.denial_reason));
    if (match) result.push({ order: match, outcomeLabel: p.label });
  }
  return result;
});

const seriesData = ref([]); // [{ order, outcomeLabel, color, points: [{stage,label,score,x,y}] }]
const loading = ref(false);
const hoveredKey = ref(null);

function pointKey(series, p) {
  return `${series.order.order_id}:${p.stage}`;
}

async function loadSeries() {
  if (!candidates.value.length) { seriesData.value = []; return; }
  loading.value = true;
  try {
    const built = await Promise.all(candidates.value.map(async ({ order, outcomeLabel }, i) => {
      const agent = props.agents.find((a) => a.agent_id === order.agent_id);
      const points = [];
      if (agent) {
        points.push({ stage: "identify", label: "Identify", score: agent.trust_score, x: STAGE_X.identify, y: scoreY(agent.trust_score), detail: `${agent.name} identified` });
      }
      const audit = await api.orderAudit(order.order_id);
      const checkoutEvent = audit.events.find((e) => ["checkout", "blocked"].includes(e.step));
      if (checkoutEvent?.detail?.live_trust_score != null) {
        points.push({
          stage: "checkout", label: "Checkout", score: checkoutEvent.detail.live_trust_score,
          x: STAGE_X.checkout, y: scoreY(checkoutEvent.detail.live_trust_score),
          detail: checkoutEvent.step === "blocked" ? (order.reason || "blocked") : "approved",
        });
      }
      const authoriseEvent = audit.events.find((e) => e.step === "authorise");
      if (authoriseEvent?.detail?.live_trust_score != null) {
        points.push({
          stage: "authorise", label: "Authorise", score: authoriseEvent.detail.live_trust_score,
          x: STAGE_X.authorise, y: scoreY(authoriseEvent.detail.live_trust_score),
          detail: "completed",
        });
      }
      return {
        order, outcomeLabel, color: SERIES_COLORS[i % SERIES_COLORS.length],
        points, agentName: agent?.name || order.agent_name,
      };
    }));
    seriesData.value = built.filter((s) => s.points.length >= 2);
  } finally {
    loading.value = false;
  }
}

// Key on the actual selected order IDs, not the `candidates` array reference itself --
// MerchantDashboard polls every 2.5s and hands down a fresh orders/agents array each
// time even when nothing changed, which made `candidates` recompute to a new (but
// equivalent) array on every tick and re-triggered loadSeries constantly. That flipped
// `loading` on and off every poll, collapsing the chart down to the one-line "Loading
// trajectories..." text and back, which shunted the panels below it up and down --
// looked like the chart was flickering into the Live Activity panel underneath it.
const candidateKey = computed(() => candidates.value.map((c) => c.order.order_id).join(","));
watch(candidateKey, loadSeries, { immediate: true });

function linePoints(series) {
  return series.points.map((p) => `${p.x},${p.y}`).join(" ");
}
// Denial reasons (e.g. commercial-validity / identity-gate messages) can run to a full
// sentence — the tooltip box is a fixed-size SVG rect, not a wrapping HTML element, so
// an untruncated string overflows past its edges and renders unstyled on the page
// behind it instead of white-on-dark. Keep it short; the full reason is already
// visible in the orders table and activity feed.
function truncate(text, max = 30) {
  if (!text || text.length <= max) return text;
  return text.slice(0, max - 1).trimEnd() + "…";
}
function endLabelY(series) {
  const last = series.points[series.points.length - 1];
  return last.y < 40 ? last.y - 14 : last.y + 22;
}
</script>

<template>
  <div class="chart-wrap">
    <p v-if="loading" class="empty">Loading trajectories…</p>
    <p v-else-if="!seriesData.length" class="empty">Not enough distinct outcomes yet — need at least one completed and one blocked order.</p>
    <template v-else>
      <svg class="chart-svg" viewBox="0 0 720 300" role="img"
           aria-label="Trust score by pipeline stage for representative recent orders">
        <g class="chart-grid">
          <line x1="70" y1="30" x2="700" y2="30"></line>
          <line x1="70" y1="85" x2="700" y2="85"></line>
          <line x1="70" y1="140" x2="700" y2="140"></line>
          <line x1="70" y1="195" x2="700" y2="195"></line>
          <line x1="70" y1="250" x2="700" y2="250"></line>
        </g>
        <text class="chart-axis-label" x="62" y="34" text-anchor="end">100</text>
        <text class="chart-axis-label" x="62" y="89" text-anchor="end">75</text>
        <text class="chart-axis-label" x="62" y="144" text-anchor="end">50</text>
        <text class="chart-axis-label" x="62" y="199" text-anchor="end">25</text>
        <text class="chart-axis-label" x="62" y="254" text-anchor="end">0</text>

        <text class="chart-stage-label" x="100" y="278" text-anchor="middle">Identify</text>
        <text class="chart-stage-label" x="340" y="278" text-anchor="middle">Checkout</text>
        <text class="chart-stage-label" x="560" y="278" text-anchor="middle">Authorise</text>

        <template v-for="series in seriesData" :key="series.order.order_id">
          <polyline class="chart-line" :points="linePoints(series)" :style="{ stroke: series.color }"></polyline>
          <g v-for="p in series.points" :key="p.stage" class="chart-point" tabindex="0"
             role="img" :aria-label="`${series.agentName}, ${p.label}, score ${p.score.toFixed(1)}, ${p.detail}`"
             @mouseenter="hoveredKey = pointKey(series, p)" @mouseleave="hoveredKey = null"
             @focus="hoveredKey = pointKey(series, p)" @blur="hoveredKey = null">
            <circle class="chart-dot" :cx="p.x" :cy="p.y" r="5" :style="{ fill: series.color }"></circle>
            <circle class="chart-hit" :cx="p.x" :cy="p.y" r="15"></circle>
          </g>
          <text class="chart-end-name" :x="series.points[series.points.length-1].x + 14" :y="endLabelY(series) - 8">{{ series.agentName }}</text>
          <text class="chart-end-score tabular" :x="series.points[series.points.length-1].x + 14" :y="endLabelY(series) + 8" :style="{ fill: series.color }">
            {{ series.points[series.points.length-1].score.toFixed(1) }}
          </text>
        </template>

        <!-- Tooltip layer, rendered after every line/dot/end-label above so the active
             tooltip always paints on top — including when hovering a series' last
             point, right where its end-label also sits. -->
        <template v-for="series in seriesData" :key="series.order.order_id + '-tt'">
          <g v-for="p in series.points" :key="p.stage" class="chart-tt"
             :class="{ visible: hoveredKey === pointKey(series, p) }"
             :transform="`translate(${p.x},${p.y})`">
            <rect x="-130" :y="p.y < 90 ? 14 : -50" width="260" height="36" rx="6" style="fill:var(--ink)"></rect>
            <text x="0" :y="p.y < 90 ? 31 : -33" text-anchor="middle" class="tt-title">{{ truncate(`${p.label} · ${series.agentName}`, 28) }}</text>
            <text x="0" :y="p.y < 90 ? 46 : -18" text-anchor="middle" class="tt-value">{{ p.score.toFixed(1) }} — {{ truncate(p.detail, 20) }}</text>
          </g>
        </template>
      </svg>

      <div class="chart-legend">
        <div v-for="series in seriesData" :key="series.order.order_id" class="legend-item">
          <span class="legend-key" :style="{ background: series.color }"></span>
          <span class="legend-agent">{{ series.agentName }}</span>
          <span class="legend-outcome" :class="series.order.status === 'completed' ? 'completed' : 'blocked'">{{ series.outcomeLabel }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.chart-wrap { position: relative; }
.empty { color: var(--ink-faint); font-size: 0.85rem; }
.chart-svg { width: 100%; height: auto; display: block; overflow: visible; }
.chart-grid line { stroke: var(--line); stroke-width: 1; }
.chart-axis-label { font-family: var(--mono); font-size: 10px; fill: var(--ink-faint); }
.chart-stage-label { font-family: var(--sans); font-size: 12px; font-weight: 600; fill: var(--ink-muted); }
.chart-line { fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.chart-dot { stroke: var(--surface); stroke-width: 2; transition: r 0.1s; }
.chart-hit { fill: transparent; cursor: pointer; }
.chart-tt { opacity: 0; transition: opacity 0.12s; pointer-events: none; }
.chart-tt.visible { opacity: 1; }
.chart-point:hover .chart-dot, .chart-point:focus-visible .chart-dot { r: 7; }
.chart-point:focus-visible { outline: none; }
.tt-title { fill: var(--paper); font-family: var(--sans); font-size: 11px; font-weight: 600; }
.tt-value { fill: var(--paper); font-family: var(--mono); font-size: 12px; font-weight: 700; }
.chart-end-name { font-family: var(--sans); font-size: 12px; font-weight: 700; fill: var(--ink); }
.chart-end-score { font-family: var(--mono); font-size: 12px; font-weight: 600; }
.chart-legend { display: flex; flex-wrap: wrap; gap: 1.1rem; margin-top: 1.1rem; padding-top: 0.9rem; border-top: 1px solid var(--line); }
.legend-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; }
.legend-key { width: 16px; height: 2px; border-radius: 1px; flex: none; }
.legend-agent { font-weight: 600; color: var(--ink); }
.legend-outcome {
  font-family: var(--mono); font-size: 0.66rem; font-weight: 600;
  letter-spacing: 0.03em; text-transform: uppercase;
  padding: 0.15rem 0.45rem; border-radius: 4px;
}
.legend-outcome.completed { background: var(--good-soft); color: var(--good); }
.legend-outcome.blocked { background: var(--warn-soft); color: var(--warn); }
</style>
