<script setup lang="ts">
// One library, three repos: the repo tabs cycle in CSS and each repo's skills light up in the
// library, while every agent in the repo loads that same set. Hovering or focusing a tab holds it.
// Each locale's index.md supplies the copy in its `skillSpotlight` frontmatter.
import { computed } from 'vue'
import { useData } from 'vitepress'
import AgentIcon from './AgentIcon.vue'
import { agents } from './agents'

const { frontmatter } = useData()
const copy = computed(() => frontmatter.value.skillSpotlight)

// The repos each skill is linked into: b(ackend), f(rontend), i(nfra).
const skills = [
  { name: 'tdd', group: 'shared', repos: 'b f' },
  { name: 'security-review', group: 'shared', repos: 'b i' },
  { name: 'db-migrations', group: 'backend', repos: 'b' },
  { name: 'api-design', group: 'backend', repos: 'b' },
  { name: 'accessibility-audit', group: 'frontend', repos: 'f' },
  { name: 'component-library', group: 'frontend', repos: 'f' },
  { name: 'visual-regression', group: 'frontend', repos: 'f' },
  { name: 'terraform-plan', group: 'infra', repos: 'i' },
  { name: 'k8s-manifests', group: 'infra', repos: 'i' },
  { name: 'incident-runbook', group: 'infra', repos: 'i' },
]
const repos = [
  { key: 'b', name: 'backend' },
  { key: 'f', name: 'frontend' },
  { key: 'i', name: 'infra' },
]
const groups = ['shared', 'backend', 'frontend', 'infra']
</script>

<template>
  <div v-if="copy" class="spot">
    <div class="tabs" role="group" :aria-label="copy.tabsLabel">
      <button v-for="repo in repos" :key="repo.key" type="button" class="tab" :class="repo.key">
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 6.5A2.5 2.5 0 0 1 5.5 4h3.6l2 2h7.4A2.5 2.5 0 0 1 21 8.5v9a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5z" /></svg>
        <span><span class="prefix">~/repos/</span>{{ repo.name }}</span>
      </button>
    </div>
    <div class="win">
      <div class="lab">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><rect x="4" y="11" width="16" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></svg>
        <span>{{ copy.linked }} <span class="mono">~/dotbrain/skills</span></span>
      </div>
      <div class="kit">
        <span v-for="skill in skills" :key="skill.name" class="sk" :class="[skill.group, skill.repos]"><i></i>{{ skill.name }}</span>
      </div>
      <div class="lab sep">{{ copy.loads }}</div>
      <div class="agents">
        <span v-for="agent in agents" :key="agent.name" class="agent">
          <AgentIcon :agent="agent" />{{ agent.name }}
          <svg class="ok" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
        </span>
      </div>
    </div>
    <div class="legend">
      <span v-for="(group, i) in groups" :key="group" :class="group"><i></i>{{ copy.legend[i] }}</span>
    </div>
  </div>
</template>

<style scoped>
.spot {
  --g-shared: var(--vp-c-brand-1);
  --g-backend: #1d4ed8;
  --g-frontend: #6d28d9;
  --g-infra: #c2410c;
  container-type: inline-size;
  min-width: 0;
}
.dark .spot {
  --g-backend: #60a5fa;
  --g-frontend: #a78bfa;
  --g-infra: #fb923c;
}
.shared { --g: var(--g-shared); }
.backend { --g: var(--g-backend); }
.frontend { --g: var(--g-frontend); }
.infra { --g: var(--g-infra); }

.tabs {
  display: flex;
  gap: 4px;
}
/* The active tab joins the window: it shares the window's ground and covers its top border. */
.tab {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  margin-bottom: -1px;
  padding: 0 14px;
  border: 1px solid var(--vp-c-divider);
  border-bottom-color: transparent;
  border-radius: 10px 10px 0 0;
  background: transparent;
  color: var(--vp-c-text-3);
  font: 400 14px var(--vp-font-family-mono);
  cursor: pointer;
  animation: 9s infinite;
}
.tab svg {
  width: 15px;
  height: 15px;
  flex: none;
}
.tab.b { animation-name: tab-b; }
.tab.f { animation-name: tab-f; }
.tab.i { animation-name: tab-i; }
.win {
  padding: 16px 18px 18px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 0 12px 12px 12px;
  background: var(--vp-c-bg-soft);
}
.lab {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  line-height: 1.4;
  color: var(--vp-c-text-2);
}
.lab svg {
  width: 14px;
  height: 14px;
  flex: none;
  color: var(--vp-c-brand-1);
}
.mono {
  font-family: var(--vp-font-family-mono);
  color: var(--vp-c-text-1);
}
.sep {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--vp-c-divider);
}
.kit,
.agents {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}
.sk {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 30px;
  padding: 0 12px;
  border: 1px solid var(--g);
  border-radius: 999px;
  font: 400 13px var(--vp-font-family-mono);
  color: var(--vp-c-text-1);
  animation: 9s infinite;
}
.sk i,
.legend i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--g);
}
.sk.b { animation-name: on-b; }
.sk.f { animation-name: on-f; }
.sk.i { animation-name: on-i; }
.sk.b.f { animation-name: on-bf; }
.sk.b.i { animation-name: on-bi; }
.agent {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 10px 0 8px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  background: var(--vp-c-bg);
  font-size: 14px;
  font-weight: 500;
}
.ok {
  width: 14px;
  height: 14px;
  color: var(--vp-c-brand-1);
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  margin-top: 12px;
  font-size: 13px;
  color: var(--vp-c-text-3);
}
.legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

@keyframes on-b { 0%, 30% { opacity: 1 } 34%, 96% { opacity: .16 } 100% { opacity: 1 } }
@keyframes on-f { 0%, 30% { opacity: .16 } 34%, 63% { opacity: 1 } 67%, 100% { opacity: .16 } }
@keyframes on-i { 0%, 63% { opacity: .16 } 67%, 96% { opacity: 1 } 100% { opacity: .16 } }
@keyframes on-bf { 0%, 63% { opacity: 1 } 67%, 96% { opacity: .16 } 100% { opacity: 1 } }
@keyframes on-bi { 0%, 30% { opacity: 1 } 34%, 63% { opacity: .16 } 67%, 100% { opacity: 1 } }
@keyframes tab-b {
  0%, 30% { background: var(--vp-c-bg-soft); color: var(--vp-c-text-1); border-bottom-color: var(--vp-c-bg-soft) }
  34%, 96% { background: transparent; color: var(--vp-c-text-3); border-bottom-color: transparent }
  100% { background: var(--vp-c-bg-soft); color: var(--vp-c-text-1); border-bottom-color: var(--vp-c-bg-soft) }
}
@keyframes tab-f {
  0%, 30% { background: transparent; color: var(--vp-c-text-3); border-bottom-color: transparent }
  34%, 63% { background: var(--vp-c-bg-soft); color: var(--vp-c-text-1); border-bottom-color: var(--vp-c-bg-soft) }
  67%, 100% { background: transparent; color: var(--vp-c-text-3); border-bottom-color: transparent }
}
@keyframes tab-i {
  0%, 63% { background: transparent; color: var(--vp-c-text-3); border-bottom-color: transparent }
  67%, 96% { background: var(--vp-c-bg-soft); color: var(--vp-c-text-1); border-bottom-color: var(--vp-c-bg-soft) }
  100% { background: transparent; color: var(--vp-c-text-3); border-bottom-color: transparent }
}

/* Hovering or focusing a repo stops the cycle and holds that repo's set. */
.spot:has(.tab:is(:hover, :focus-visible)) :is(.tab, .sk) {
  animation: none;
}
.spot:has(.tab:is(:hover, :focus-visible)) .sk {
  opacity: 0.16;
}
.spot:has(.tab:is(:hover, :focus-visible)) .tab {
  background: transparent;
  color: var(--vp-c-text-3);
  border-bottom-color: transparent;
}
.spot:has(.tab:is(:hover, :focus-visible)) .tab:is(:hover, :focus-visible) {
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  border-bottom-color: var(--vp-c-bg-soft);
}
.spot:has(.tab.b:is(:hover, :focus-visible)) .sk.b,
.spot:has(.tab.f:is(:hover, :focus-visible)) .sk.f,
.spot:has(.tab.i:is(:hover, :focus-visible)) .sk.i {
  opacity: 1;
}

@media (prefers-reduced-motion: reduce) {
  .tab,
  .sk {
    animation: none;
  }
}

/* Narrow columns drop the ~/repos/ prefix so the three tabs stay on one row. */
@container (max-width: 480px) {
  .prefix {
    display: none;
  }
  .tab {
    padding: 0 12px;
    font-size: 13px;
  }
  .win {
    padding: 14px;
  }
  .sk {
    height: 28px;
    padding: 0 10px;
    font-size: 12px;
  }
}
</style>
