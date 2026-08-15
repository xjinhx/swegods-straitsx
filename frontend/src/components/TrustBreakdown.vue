<script setup>
defineProps({ agent: { type: Object, required: true } });

const rows = [
  { key: "mandate_scope_score", label: "Mandate scope" },
  { key: "identity_score", label: "Identity" },
  { key: "behavior_score", label: "Behaviour" },
];
</script>

<template>
  <div class="breakdown">
    <div class="head">
      <div>
        <div class="name">{{ agent.name }}</div>
        <div class="id mono">{{ agent.agent_id }}</div>
      </div>
      <div class="overall">
        <div class="overall-score tabular">{{ Math.round(agent.trust_score) }}</div>
        <div class="overall-label">trust score</div>
      </div>
    </div>
    <div class="bars">
      <div v-for="row in rows" :key="row.key" class="bar-row">
        <span class="bar-label">{{ row.label }}</span>
        <div class="bar-track">
          <div class="bar-fill" :style="{ width: agent[row.key] + '%' }"></div>
        </div>
        <span class="bar-value tabular">{{ Math.round(agent[row.key]) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.breakdown { display: flex; flex-direction: column; gap: 0.9rem; }
.head { display: flex; justify-content: space-between; align-items: flex-start; }
.name { font-weight: 700; }
.id { color: var(--ink-faint); font-size: 0.78rem; }
.overall { text-align: right; }
.overall-score { font-size: 1.6rem; font-weight: 700; color: var(--accent-ink); line-height: 1; }
.overall-label { font-size: 0.7rem; color: var(--ink-faint); text-transform: uppercase; letter-spacing: 0.05em; }
.bars { display: flex; flex-direction: column; gap: 0.5rem; }
.bar-row { display: grid; grid-template-columns: 6.5rem 1fr 2rem; align-items: center; gap: 0.6rem; }
.bar-label { font-size: 0.8rem; color: var(--ink-muted); }
.bar-track { height: 6px; background: var(--surface-2); border-radius: 999px; overflow: hidden; }
.bar-fill { height: 100%; background: var(--accent); border-radius: 999px; }
.bar-value { font-size: 0.8rem; text-align: right; color: var(--ink-muted); }
</style>
