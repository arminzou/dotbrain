<script setup lang="ts">
// The home hero: headline, actions, supported agents, and the repo-to-private-home link panels.
// Each locale's index.md supplies the copy in its `homeHero` frontmatter.
import { computed } from 'vue'
import { useData } from 'vitepress'
import { VPButton } from 'vitepress/theme'
import AgentIcon from './AgentIcon.vue'
import { agents } from './agents'

const { frontmatter } = useData()
const hero = computed(() => frontmatter.value.homeHero)

const links = [
  { name: '.brain', folder: true, home: 'brainspaces/my-app/.brain', chip: 'thinking' },
  { name: '.claude/skills/review', folder: true, home: 'skills/engineering/review', chip: 'skills' },
  { name: '.claude/agents/reviewer.md', folder: false, home: 'subagents/claude/reviewer.md', chip: 'subagents' },
]
</script>

<template>
  <section v-if="hero" class="home-hero">
    <div class="inner">
      <div class="copy">
        <h1 class="title">
          {{ hero.title }}
          <span class="second"><span class="private">{{ hero.private }}</span> <span class="shared">{{ hero.shared }}</span></span>
        </h1>
        <p class="lede">{{ hero.tagline }}</p>
        <div class="actions">
          <VPButton
            v-for="action in hero.actions"
            :key="action.link"
            tag="a"
            size="medium"
            :theme="action.theme"
            :text="action.text"
            :href="action.link"
          />
        </div>
        <p class="label">{{ hero.worksWith }}</p>
        <ul class="agents" role="list">
          <li v-for="agent in agents" :key="agent.name" class="agent">
            <AgentIcon :agent="agent" />{{ agent.name }}
          </li>
        </ul>
      </div>

      <div class="panels">
        <div class="panel">
          <p class="cap">{{ hero.repo }}</p>
          <div class="row"><svg class="ic" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 6.5A2.5 2.5 0 0 1 5.5 4h3.6l2 2h7.4A2.5 2.5 0 0 1 21 8.5v9a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5z" /></svg>my-app/</div>
          <div class="row dim in"><svg class="ic" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 6.5A2.5 2.5 0 0 1 5.5 4h3.6l2 2h7.4A2.5 2.5 0 0 1 21 8.5v9a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5z" /></svg>src/</div>
          <template v-for="link in links" :key="link.name">
            <div class="row link in">
              <svg v-if="link.folder" class="ic" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 6.5A2.5 2.5 0 0 1 5.5 4h3.6l2 2h7.4A2.5 2.5 0 0 1 21 8.5v9a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5z" /></svg>
              <svg v-else class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M14 3H6.5A1.5 1.5 0 0 0 5 4.5v15A1.5 1.5 0 0 0 6.5 21h11a1.5 1.5 0 0 0 1.5-1.5V8z" /><path d="M14 3v5h5" /></svg>
              {{ link.name }}
            </div>
            <div class="target">→ <span class="prefix">~/dotbrain/</span><span class="path">{{ link.home }}</span></div>
          </template>
        </div>
        <div class="panel private-home">
          <p class="cap"><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><rect x="4" y="11" width="16" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></svg>{{ hero.home }}</p>
          <div v-for="link in links" :key="link.home" class="row">
            <svg v-if="link.folder" class="ic" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 6.5A2.5 2.5 0 0 1 5.5 4h3.6l2 2h7.4A2.5 2.5 0 0 1 21 8.5v9a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5z" /></svg>
            <svg v-else class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M14 3H6.5A1.5 1.5 0 0 0 5 4.5v15A1.5 1.5 0 0 0 6.5 21h11a1.5 1.5 0 0 0 1.5-1.5V8z" /><path d="M14 3v5h5" /></svg>
            <span class="path">{{ link.home }}</span><span class="chip">{{ hero.chips[link.chip] }}</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.home-hero {
  position: relative;
  overflow: hidden;
  padding: 48px 24px 64px;
}
/* A teal glow behind the panels, the same light as the social card. */
.home-hero::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(720px 520px at 78% 42%, color-mix(in srgb, var(--vp-c-brand-1) 14%, transparent), transparent 65%);
}
.inner {
  position: relative;
  max-width: 1152px;
  margin: 0 auto;
  display: grid;
  gap: 48px;
}
.title {
  margin: 0;
  font-size: 40px;
  line-height: 1.04;
  font-weight: 750;
  letter-spacing: -0.035em;
  text-wrap: balance;
}
.second {
  display: block;
  margin-top: 12px;
  font-size: 22px;
  line-height: 1.25;
  font-weight: 650;
  letter-spacing: -0.02em;
}
.private {
  color: var(--vp-c-text-2);
}
.shared {
  color: var(--vp-c-brand-1);
}
.lede {
  margin: 20px 0 0;
  max-width: 34ch;
  text-wrap: balance;
  font-size: 18px;
  line-height: 1.5;
  color: var(--vp-c-text-2);
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}
.label {
  margin: 36px 0 0;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--vp-c-text-3);
}
.agents {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}
.agent {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 12px 0 8px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  background: var(--vp-c-bg-soft);
  font-size: 14px;
  font-weight: 500;
}

.panels {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
}
.panel {
  min-width: 0;
  padding: 16px 0 14px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 16px;
  background: var(--vp-c-bg-soft);
  overflow: hidden;
}
/* The private home: a teal edge that fades out, and a faint teal ground. */
.private-home {
  border: 1.5px solid transparent;
  background:
    linear-gradient(color-mix(in srgb, var(--vp-c-brand-1) 5%, var(--vp-c-bg)), color-mix(in srgb, var(--vp-c-brand-1) 5%, var(--vp-c-bg))) padding-box,
    linear-gradient(160deg, var(--vp-c-brand-1), transparent 55%) border-box;
  box-shadow: 0 0 70px color-mix(in srgb, var(--vp-c-brand-1) 14%, transparent);
}
.cap {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 8px;
  padding: 0 16px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--vp-c-text-3);
}
.private-home .cap {
  color: var(--vp-c-brand-1);
}
.row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 28px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
}
.ic {
  width: 16px;
  height: 16px;
  flex: none;
  color: var(--vp-c-text-3);
}
.cap .ic {
  width: 14px;
  height: 14px;
  color: inherit;
}
.in {
  padding-left: 34px;
}
.dim {
  color: var(--vp-c-text-3);
}
.link,
.link .ic {
  color: var(--vp-c-brand-1);
}
.target {
  margin-top: -4px;
  padding: 0 16px 4px 60px;
  font: 400 12px/20px var(--vp-font-family-mono);
  color: var(--vp-c-text-3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* Phones show the link target relative to ~/dotbrain, which the private panel names. */
.target .prefix {
  display: none;
}
.path {
  font-family: var(--vp-font-family-mono);
  font-weight: 400;
  color: var(--vp-c-text-1);
}
.row .path {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 12px;
}
.chip {
  margin-left: auto;
  padding: 1px 7px;
  border: 1px solid color-mix(in srgb, var(--vp-c-brand-1) 30%, transparent);
  border-radius: 999px;
  background: var(--vp-c-brand-soft);
  color: var(--vp-c-brand-1);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

@media (min-width: 640px) {
  .home-hero {
    padding: 64px 48px 80px;
  }
  .title {
    font-size: 52px;
  }
  .second {
    font-size: 26px;
  }
  .lede {
    font-size: 20px;
  }
  .cap,
  .row {
    padding: 0 22px;
  }
  .row {
    font-size: 16px;
  }
  .row .path {
    font-size: 14px;
  }
  .in {
    padding-left: 44px;
  }
  .target {
    padding: 0 22px 4px 70px;
    font-size: 14px;
    line-height: 22px;
  }
  .target .prefix {
    display: inline;
  }
  .chip {
    font-size: 11px;
    padding: 2px 8px;
  }
}

@media (min-width: 960px) {
  .home-hero {
    padding: 88px 64px 96px;
  }
  .inner {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr);
    gap: 56px;
    align-items: center;
  }
  .title {
    font-size: 60px;
  }
  .second {
    font-size: 28px;
  }
}
</style>
