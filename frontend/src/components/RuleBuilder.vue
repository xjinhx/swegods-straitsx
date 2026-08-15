<script setup>
import { onMounted, reactive, ref } from "vue";
import { api } from "../api";

const rules = ref([]);
const error = ref(null);
const submitting = ref(false);

const form = reactive({
  rule_type: "category_cap",
  category: "",
  max_price_sgd: 50,
  price_threshold_sgd: 20,
  min_trust: 70,
});

async function load() {
  rules.value = await api.rules();
}
onMounted(load);

async function submit() {
  submitting.value = true;
  error.value = null;
  try {
    const minTrust = form.min_trust === "" || form.min_trust === null ? null : Number(form.min_trust);
    const payload = { rule_type: form.rule_type, min_trust: minTrust };
    if (form.rule_type === "blocked_category") {
      payload.category = form.category;
      payload.min_trust = null;
    } else if (form.rule_type === "category_cap") {
      payload.category = form.category;
      payload.max_price_sgd = Number(form.max_price_sgd);
    } else if (form.rule_type === "price_threshold") {
      payload.price_threshold_sgd = Number(form.price_threshold_sgd);
    }
    await api.createRule(payload);
    form.category = "";
    await load();
  } catch (e) {
    error.value = e.message;
  } finally {
    submitting.value = false;
  }
}

async function remove(id) {
  await api.deleteRule(id);
  await load();
}

function describe(r) {
  if (r.rule_type === "blocked_category") return `Block category "${r.category}"`;
  if (r.rule_type === "category_cap")
    return `"${r.category}" capped at $${r.max_price_sgd.toFixed(2)} for trust < ${r.min_trust}`;
  return `Purchases ≥ $${r.price_threshold_sgd.toFixed(2)} require trust ≥ ${r.min_trust}`;
}
</script>

<template>
  <div class="rule-builder">
    <ul v-if="rules.length" class="rule-list">
      <li v-for="r in rules" :key="r.id" class="rule-row">
        <span class="rule-type">{{ r.rule_type.replace("_", " ") }}</span>
        <span class="rule-desc">{{ describe(r) }}</span>
        <button class="ghost" @click="remove(r.id)" aria-label="Remove rule">✕</button>
      </li>
    </ul>
    <p v-else class="empty">No rules yet — /checkout is using the default price-tier thresholds.</p>

    <form class="rule-form" @submit.prevent="submit">
      <select v-model="form.rule_type">
        <option value="category_cap">Category spend cap</option>
        <option value="price_threshold">Price-tier trust threshold</option>
        <option value="blocked_category">Blocked category</option>
      </select>

      <input
        v-if="form.rule_type === 'category_cap' || form.rule_type === 'blocked_category'"
        v-model="form.category" placeholder="category, e.g. electronics" required
      />
      <input
        v-if="form.rule_type === 'category_cap'"
        v-model.number="form.max_price_sgd" type="number" step="0.5" placeholder="max price SGD"
      />
      <input
        v-if="form.rule_type === 'price_threshold'"
        v-model.number="form.price_threshold_sgd" type="number" step="0.5" placeholder="price threshold SGD"
      />
      <input
        v-if="form.rule_type !== 'blocked_category'"
        v-model.number="form.min_trust" type="number" min="0" max="100" placeholder="min trust score"
      />
      <button class="primary" type="submit" :disabled="submitting">Add rule</button>
    </form>
    <p v-if="error" class="empty" style="color: var(--bad)">{{ error }}</p>
  </div>
</template>

<style scoped>
.rule-builder { display: flex; flex-direction: column; gap: 1rem; }
.rule-list { list-style: none; margin: 0; padding: 0; }
.rule-row {
  display: flex; align-items: center; gap: 0.7rem; padding: 0.5rem 0;
  border-bottom: 1px solid var(--line); font-size: 0.88rem;
}
.rule-row:last-child { border-bottom: none; }
.rule-type {
  font-family: var(--mono); font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.04em;
  color: var(--accent-ink); background: var(--accent-soft); padding: 0.15rem 0.45rem; border-radius: 4px;
  white-space: nowrap;
}
.rule-desc { flex: 1; }
.rule-form { display: flex; flex-wrap: wrap; gap: 0.5rem; padding-top: 0.6rem; border-top: 1px dashed var(--line); }
.rule-form input, .rule-form select { flex: 1; min-width: 8rem; }
</style>
