<script setup>
import { ref, watch } from "vue";
import { api } from "../api";

const props = defineProps({ orderId: { type: String, required: true } });

const events = ref([]);
const loading = ref(false);
const error = ref(null);

const SCORE_ROWS = [
  { key: "identity_score", label: "Identity" },
  { key: "mandate_scope_score", label: "Mandate scope" },
  { key: "behavior_score", label: "Behaviour" },
  { key: "commercial_validity_score", label: "Commercial validity" },
  { key: "payment_authority_score", label: "Payment authority" },
];

const stepLabel = {
  checkout: "Checkout",
  blocked: "Blocked",
  authorise: "Authorise",
  receipt: "Receipt",
  override: "Override",
};

function scoreRowsFor(detail) {
  return SCORE_ROWS.filter((r) => detail[r.key] !== undefined && detail[r.key] !== null);
}

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const data = await api.orderAudit(props.orderId);
    events.value = data.events;
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

watch(() => props.orderId, load, { immediate: true });
</script>

<template>
  <div class="timeline">
    <p v-if="loading" class="empty">Loading…</p>
    <p v-else-if="error" class="empty">Couldn't load audit trail: {{ error }}</p>
    <p v-else-if="!events.length" class="empty">No events for this order yet.</p>
    <ol v-else class="stage-list">
      <li v-for="ev in events" :key="ev.id" class="stage" :class="ev.step">
        <div class="stage-head">
          <span class="stage-step" :class="ev.step">{{ stepLabel[ev.step] || ev.step }}</span>
          <span class="stage-live tabular" v-if="ev.detail.live_trust_score !== undefined && ev.detail.live_trust_score !== null">
            {{ Math.round(ev.detail.live_trust_score) }}
          </span>
        </div>
        <p class="stage-msg">{{ ev.message }}</p>
        <div class="bars" v-if="scoreRowsFor(ev.detail).length">
          <div v-for="row in scoreRowsFor(ev.detail)" :key="row.key" class="bar-row">
            <span class="bar-label">{{ row.label }}</span>
            <div class="bar-track">
              <div class="bar-fill" :class="{ warn: ev.detail[row.key] < 50 }" :style="{ width: ev.detail[row.key] + '%' }"></div>
            </div>
            <span class="bar-value tabular">{{ Math.round(ev.detail[row.key]) }}</span>
          </div>
        </div>
        <p v-if="ev.detail.denial_reason" class="denial">denial_reason: {{ ev.detail.denial_reason }}</p>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.timeline { display: flex; flex-direction: column; }
.empty { color: var(--ink-faint); font-size: 0.85rem; }
.stage-list {
  list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.7rem;
}
.stage {
  border-left: 2px solid var(--line-strong); padding: 0.1rem 0 0.1rem 0.8rem; position: relative;
}
.stage::before {
  content: ""; position: absolute; left: -5px; top: 0.35rem; width: 8px; height: 8px;
  border-radius: 50%; background: var(--line-strong);
}
.stage.checkout::before, .stage.receipt::before { background: var(--accent); }
.stage.authorise::before { background: var(--good); }
.stage.blocked::before { background: var(--warn); }
.stage-head { display: flex; justify-content: space-between; align-items: baseline; }
.stage-step {
  font-family: var(--mono); font-size: 0.68rem; font-weight: 700; letter-spacing: 0.04em;
  text-transform: uppercase; padding: 0.15rem 0.45rem; border-radius: 4px; width: fit-content;
  color: var(--ink-muted); background: var(--surface-2);
}
.stage-step.checkout, .stage-step.receipt { color: var(--accent-ink); background: var(--accent-soft); }
.stage-step.authorise { color: var(--good); background: var(--good-soft); }
.stage-step.blocked { color: var(--warn); background: var(--warn-soft); }
.stage-live { font-weight: 700; font-size: 0.95rem; color: var(--accent-ink); }
.stage-msg { margin: 0.3rem 0 0.4rem; font-size: 0.83rem; color: var(--ink); }
.bars { display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 0.2rem; }
.bar-row { display: grid; grid-template-columns: 8rem 1fr 2rem; align-items: center; gap: 0.5rem; }
.bar-label { font-size: 0.74rem; color: var(--ink-muted); }
.bar-track { height: 5px; background: var(--surface-2); border-radius: 999px; overflow: hidden; }
.bar-fill { height: 100%; background: var(--accent); border-radius: 999px; }
.bar-fill.warn { background: var(--warn); }
.bar-value { font-size: 0.74rem; text-align: right; color: var(--ink-muted); }
.denial { margin: 0.2rem 0 0; font-size: 0.76rem; color: var(--warn); font-family: var(--mono); }
</style>
