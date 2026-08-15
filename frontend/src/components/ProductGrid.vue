<script setup>
import { computed, ref } from "vue";

const props = defineProps({ products: { type: Array, required: true } });

const CATEGORY_META = {
  home: { emoji: "🏠", from: "#FFD9A0", to: "#FF9F68" },
  gifts: { emoji: "🎁", from: "#FFC2D1", to: "#FF6B9D" },
  electronics: { emoji: "🎧", from: "#A0C4FF", to: "#4C6FFF" },
  stationery: { emoji: "📓", from: "#B9FBC0", to: "#3DBE6C" },
  toys: { emoji: "🧸", from: "#FFF3A0", to: "#FFC93C" },
};
const FALLBACK = { emoji: "🛍️", from: "#E0E0E0", to: "#B0B0B0" };

function meta(category) {
  return CATEGORY_META[category] || FALLBACK;
}

// Drop an image named after a product's SKU (e.g. assets/products/sku-1001.png)
// for a per-product photo, or after a category (e.g. assets/products/home.png)
// as a shared fallback — see assets/products/README.md.
const productImages = Object.fromEntries(
  Object.entries(import.meta.glob("../assets/products/*.{png,jpg,jpeg,webp,svg}", { eager: true, import: "default" }))
    .map(([path, url]) => [path.match(/([^/]+)\.[^.]+$/)[1].toLowerCase(), url])
);

function image(p) {
  return productImages[p.sku.toLowerCase()] || productImages[p.category] || productImages.fallback || null;
}

const activeCategory = ref("all");
const categories = computed(() => ["all", ...new Set(props.products.map((p) => p.category))]);
const filtered = computed(() =>
  activeCategory.value === "all"
    ? props.products
    : props.products.filter((p) => p.category === activeCategory.value)
);
</script>

<template>
  <div>
    <div class="filters">
      <button
        v-for="c in categories"
        :key="c"
        class="chip"
        :class="{ active: c === activeCategory }"
        @click="activeCategory = c"
      >{{ c === "all" ? "All" : c }}</button>
    </div>

    <div class="grid">
      <article v-for="p in filtered" :key="p.sku" class="card">
        <div
          class="thumb"
          :style="image(p) ? {} : { background: `linear-gradient(135deg, ${meta(p.category).from}, ${meta(p.category).to})` }"
        >
          <img v-if="image(p)" class="thumb-img" :src="image(p)" :alt="p.name" />
          <span v-else class="thumb-emoji">{{ meta(p.category).emoji }}</span>
        </div>
        <div class="body">
          <span class="category">{{ p.category }}</span>
          <h3 class="name">{{ p.name }}</h3>
          <p class="desc">{{ p.description }}</p>
          <div class="footer">
            <span class="price">${{ p.price_sgd.toFixed(2) }}</span>
            <span class="sku mono">{{ p.sku }}</span>
          </div>
        </div>
      </article>
    </div>

    <p v-if="!filtered.length" class="empty">No products in this category.</p>
  </div>
</template>

<style scoped>
.filters { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.7rem 0 1.1rem; }
.chip {
  border: 1px solid var(--line-strong); background: var(--surface); color: var(--ink-muted);
  border-radius: 999px; padding: 0.35rem 0.85rem; font-size: 0.82rem; font-weight: 600;
  text-transform: capitalize;
}
.chip.active { background: var(--accent); border-color: var(--accent); color: #fff; }

.grid {
  display: grid; gap: 1rem;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
}

.card {
  display: flex; flex-direction: column;
  background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
  overflow: hidden; transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 24px -12px rgba(0, 0, 0, 0.25);
  border-color: var(--line-strong);
}

.thumb {
  aspect-ratio: 1.4 / 1; display: flex; align-items: center; justify-content: center; overflow: hidden;
}
.thumb-emoji { font-size: 2.6rem; filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.15)); }
.thumb-img { width: 100%; height: 100%; object-fit: cover; }

.body { padding: 0.8rem 0.9rem 0.95rem; display: flex; flex-direction: column; gap: 0.3rem; flex: 1; }

.category {
  font-family: var(--mono); font-size: 0.65rem; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--ink-faint);
}
.name { margin: 0; font-size: 0.95rem; font-weight: 700; line-height: 1.3; }
.desc {
  margin: 0; font-size: 0.82rem; color: var(--ink-muted); line-height: 1.4;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  flex: 1;
}

.footer {
  display: flex; align-items: baseline; justify-content: space-between;
  margin-top: 0.4rem; padding-top: 0.55rem; border-top: 1px solid var(--line);
}
.price { font-size: 1.05rem; font-weight: 800; color: var(--accent-ink); }
.sku { font-size: 0.68rem; color: var(--ink-faint); }
</style>
