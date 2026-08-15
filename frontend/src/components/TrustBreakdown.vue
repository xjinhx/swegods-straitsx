<script setup>
import { computed } from "vue";

const props = defineProps({ agent: { type: Object, required: true } });
const emit = defineEmits(["revoke", "reinstate"]);

const ALL_ROWS = [
  { key: "mandate_scope_score", label: "Mandate scope" },
  { key: "identity_score", label: "Identity" },
  { key: "behavior_score", label: "Behaviour" },
  { key: "reputation_score", label: "Reputation" },
];

// reputation_score is null for a brand-new agent with no resolved order history yet —
// omit the row entirely rather than showing a misleading 0.
const rows = computed(() => ALL_ROWS.filter((r) => props.agent[r.key] !== undefined && props.agent[r.key] !== null));

function relTime(iso) {
  const s = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 5) return "just now";
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  return `${Math.floor(m / 60)}h ago`;
}
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
    <p v-if="agent.reputation_orders" class="reputation-note">{{ agent.reputation_orders }} (Wilson score, 95% CI)</p>
    <div class="revocation-row">
      <button v-if="agent.key_active" class="revoke-btn" @click="emit('revoke', agent.agent_id)">
        Revoke credential
      </button>
      <template v-else>
        <span class="revoked-badge">Revoked {{ relTime(agent.key_revoked_at) }}</span>
        <button class="reinstate-btn" @click="emit('reinstate', agent.agent_id)">Reinstate</button>
      </template>
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
.reputation-note { margin: 0; font-size: 0.74rem; color: var(--ink-faint); font-family: var(--mono); }
.revocation-row { display: flex; align-items: center; gap: 0.6rem; }
.revoke-btn { border-color: var(--warn); color: var(--warn); }
.revoke-btn:hover { background: var(--warn-soft); }
.revoked-badge { font-size: 0.78rem; font-weight: 600; color: var(--warn); background: var(--warn-soft); padding: 0.3rem 0.6rem; border-radius: 999px; }
.reinstate-btn { font-size: 0.8rem; }
</style>
