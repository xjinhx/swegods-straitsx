<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import { api } from "../api";

const props = defineProps({
  limit: { type: Number, default: 30 },
  pollMs: { type: Number, default: 2000 },
});

const events = ref([]); // newest-first, same order the feed renders in
const error = ref(null);
const hasMore = ref(false); // more history older than what's loaded
const loadingOlder = ref(false);
let timer = null;

async function initialLoad() {
  try {
    const res = await api.activityFeed({ limit: props.limit });
    events.value = res.events;
    hasMore.value = res.has_more;
    error.value = null;
  } catch (e) {
    error.value = e.message;
  }
}

// Delta poll: fetch only what's newer than the top-of-feed event and prepend it,
// instead of re-fetching (and re-rendering) the same top-N window every tick — also
// what makes this immune to duplicating or dropping rows across polls, unlike
// re-fetching "the last N" would be under concurrent writes.
async function pollNew() {
  if (!events.value.length) return initialLoad();
  try {
    const res = await api.activityFeed({ limit: props.limit, sinceId: events.value[0].id });
    if (res.events.length) events.value = [...res.events, ...events.value];
    error.value = null;
  } catch (e) {
    error.value = e.message;
  }
}

// "Load older": paged back from the oldest currently-loaded event, triggered by
// scrolling the feed's capped-height region toward its bottom.
async function loadOlder() {
  if (loadingOlder.value || !hasMore.value || !events.value.length) return;
  loadingOlder.value = true;
  try {
    const oldestId = events.value[events.value.length - 1].id;
    const res = await api.activityFeed({ limit: props.limit, beforeId: oldestId });
    events.value = [...events.value, ...res.events];
    hasMore.value = res.has_more;
  } catch (e) {
    error.value = e.message;
  } finally {
    loadingOlder.value = false;
  }
}

function onScroll(e) {
  const el = e.target;
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 80) loadOlder();
}

onMounted(() => {
  initialLoad();
  timer = setInterval(pollNew, props.pollMs);
});
onUnmounted(() => clearInterval(timer));

const stepLabel = {
  identify: "Identify",
  checkout: "Checkout",
  blocked: "Blocked",
  authorise: "Authorise",
  receipt: "Receipt",
  override: "Override",
  rule_created: "Rule added",
  rule_deleted: "Rule removed",
};

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
  <div>
    <p v-if="error" class="empty">Couldn't reach the backend: {{ error }}</p>
    <p v-else-if="!events.length" class="empty">No activity yet — run the demo agent to generate some.</p>
    <div v-else class="feed-scroll" @scroll="onScroll">
      <ul class="feed">
        <li v-for="ev in events" :key="ev.id" :class="['feed-row', ev.step]">
          <span class="feed-step" :class="ev.step">{{ stepLabel[ev.step] || ev.step }}</span>
          <span class="feed-msg">{{ ev.message }}</span>
          <span class="feed-time">{{ relTime(ev.timestamp) }}</span>
        </li>
      </ul>
      <p v-if="loadingOlder" class="feed-end">Loading older activity…</p>
      <p v-else-if="!hasMore" class="feed-end">— start of activity —</p>
    </div>
  </div>
</template>

<style scoped>
.feed-scroll { max-height: 420px; overflow-y: auto; }
.feed { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
.feed-row {
  display: grid; grid-template-columns: 6.5rem 1fr auto; gap: 0.8rem; align-items: baseline;
  padding: 0.55rem 0; border-bottom: 1px solid var(--line); font-size: 0.87rem;
}
.feed-row:last-child { border-bottom: none; }
.feed-step {
  font-family: var(--mono); font-size: 0.68rem; font-weight: 700; letter-spacing: 0.04em;
  text-transform: uppercase; padding: 0.15rem 0.45rem; border-radius: 4px; width: fit-content;
  color: var(--ink-muted); background: var(--surface-2);
}
.feed-step.checkout, .feed-step.receipt { color: var(--accent-ink); background: var(--accent-soft); }
.feed-step.authorise { color: var(--good); background: var(--good-soft); }
.feed-step.blocked { color: var(--warn); background: var(--warn-soft); }
.feed-step.override { color: var(--accent-ink); background: var(--accent-soft); }
.feed-msg { color: var(--ink); }
.feed-time { color: var(--ink-faint); font-family: var(--mono); font-size: 0.78rem; white-space: nowrap; }
.feed-end { text-align: center; color: var(--ink-faint); font-size: 0.78rem; padding: 0.7rem 0 0.2rem; margin: 0; }
</style>
