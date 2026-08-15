<script setup>
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
import ActivityFeed from "../components/ActivityFeed.vue";

const products = ref([]);
const latestStep = ref(null);
const copied = ref(false);

const STAGES = [
  { key: "discover", label: "Discover", matches: [] },
  { key: "identify", label: "Identify", matches: ["identify"] },
  { key: "checkout", label: "Checkout", matches: ["checkout", "blocked"] },
  { key: "authorise", label: "Authorise", matches: ["authorise"] },
  { key: "prove", label: "Prove", matches: ["receipt"] },
];

onMounted(async () => {
  products.value = await api.products();
  poll();
  setInterval(poll, 2000);
});

async function poll() {
  const events = await api.activityFeed(1);
  latestStep.value = events[0]?.step ?? null;
}

const activeIndex = computed(() => {
  if (!latestStep.value) return -1;
  return STAGES.findIndex((s) => s.matches.includes(latestStep.value));
});

const cmd = 'python agent.py "buy me a birthday gift under $50"';

function copyCmd() {
  navigator.clipboard?.writeText(cmd);
  copied.value = true;
  setTimeout(() => (copied.value = false), 1500);
}
</script>

<template>
  <div class="grid">
    <section class="panel run-panel">
      <span class="eyebrow">Run the demo agent</span>
      <p class="hint">
        The shopping agent is a standalone Claude-powered script (<code class="mono">demo_agent/agent.py</code>)
        that calls this exact API over HTTP — nothing here is simulated. Run it in a terminal
        and watch the flow below update live.
      </p>
      <div class="cmd-row">
        <code class="mono cmd">{{ cmd }}</code>
        <button @click="copyCmd">{{ copied ? "Copied" : "Copy" }}</button>
      </div>
    </section>

    <section class="panel">
      <span class="eyebrow">Flow — discover → identify → checkout → authorise → prove</span>
      <ol class="stages">
        <li v-for="(s, i) in STAGES" :key="s.key" :class="{ active: i === activeIndex, done: i < activeIndex }">
          <span class="stage-dot"></span>{{ s.label }}
        </li>
      </ol>
    </section>

    <section class="panel">
      <span class="eyebrow">Live trace</span>
      <ActivityFeed :limit="20" />
    </section>

    <section class="panel">
      <span class="eyebrow">Catalogue ({{ products.length }} items, 5–30 SGD)</span>
      <div class="table-wrap">
        <table>
          <thead><tr><th>SKU</th><th>Name</th><th>Category</th><th>Price</th></tr></thead>
          <tbody>
            <tr v-for="p in products" :key="p.sku">
              <td class="mono">{{ p.sku }}</td>
              <td>{{ p.name }}</td>
              <td>{{ p.category }}</td>
              <td class="tabular">${{ p.price_sgd.toFixed(2) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.grid { display: grid; gap: 1.1rem; grid-template-columns: 1fr; }
.hint { color: var(--ink-muted); font-size: 0.9rem; max-width: 42rem; margin: 0.5rem 0 0.9rem; }
.cmd-row { display: flex; gap: 0.6rem; align-items: center; }
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
