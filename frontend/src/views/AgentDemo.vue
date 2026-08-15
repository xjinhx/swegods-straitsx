<script setup>
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
import ProductGrid from "../components/ProductGrid.vue";

const products = ref([]);
const query = ref("");

onMounted(async () => {
  products.value = await api.products();
});

const visible = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return products.value;
  return products.value.filter(
    (p) => p.name.toLowerCase().includes(q) || p.description.toLowerCase().includes(q)
  );
});
</script>

<template>
  <div class="storefront">
    <header class="market-header">
      <div class="wordmark">
        Agent<span class="m">M</span><span class="a">a</span><span class="r">r</span><span class="t">t</span>
      </div>
      <div class="search-bar">
        <input v-model="query" type="search" placeholder="Search the catalogue…" />
      </div>
      <div class="header-meta">{{ products.length }} listings · every purchase made by an AI agent, not a click</div>
    </header>

    <ProductGrid :products="visible" />
  </div>
</template>

<style scoped>
.storefront { display: flex; flex-direction: column; gap: 1.3rem; }

.market-header {
  display: flex; flex-wrap: wrap; align-items: center; gap: 1rem 1.4rem;
  padding: 1.1rem 1.4rem; background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
}
.wordmark {
  font-size: 1.5rem; font-weight: 800; letter-spacing: -0.01em; color: var(--ink);
  white-space: nowrap;
}
.wordmark .m { color: #E1553D; }
.wordmark .a { color: #3E6AE1; }
.wordmark .r { color: #E1B93E; }
.wordmark .t { color: #3DBE6C; }

.search-bar { flex: 1; min-width: 12rem; }
.search-bar input {
  width: 100%; padding: 0.6rem 0.9rem; border-radius: 999px; border: 1px solid var(--line-strong);
  background: var(--surface-2);
}

.header-meta {
  font-size: 0.8rem; color: var(--ink-faint); white-space: nowrap;
}
</style>
