<script setup lang="ts">
// The workflow loop around the Brain, with the Beads work graph that runs at "Work the issues".
// One beat a second: issues start, close, and unblock their dependents, then the loop moves on to
// review and back to the Brain. Each locale's index.md supplies the copy in its `workLoop`
// frontmatter; geometry sits on an 8px grid and is scaled down to fit narrow columns.
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useData } from 'vitepress'
import AgentIcon from './AgentIcon.vue'
import { agents } from './agents'

const { frontmatter } = useData()
const copy = computed(() => frontmatter.value.workLoop)

const TRACK = 'M64,200 V112 A48,48 0 0 1 112,64 H288 A48,48 0 0 1 336,112 V288 A48,48 0 0 1 288,336 H112 A48,48 0 0 1 64,288 Z'
const stages = [
  { x: 64, y: 200, skill: 'find-unknowns' },
  { x: 200, y: 64, skill: 'to-design' },
  { x: 336, y: 200, skill: 'run-execution' },
  { x: 200, y: 336, skill: 'review-gate' },
]
const agent = (name: string) => agents.find((a) => a.name === name)!
const issues = [
  { k: 1, agent: agent('Claude Code') },
  { k: 2, agent: agent('Codex') },
  { k: 3, agent: agent('Claude Code') },
  { k: 4, agent: agent('OpenCode') },
  { k: 5, agent: agent('Cursor') },
]
// Two layouts of the same graph: left to right beside the loop, and top to bottom on phones.
const GRAPHS = {
  wide: {
    width: 616, height: 176, label: { x: 196, y: 24, anchor: 'middle' },
    at: { 1: [0, 0], 2: [0, 112], 3: [224, 0], 4: [224, 112], 5: [448, 56] } as Record<number, number[]>,
    edges: [
      { e: '1-3', d: 'M168,32 H218', head: 'M216,28.5 L223,32 L216,35.5Z' },
      { e: '2-4', d: 'M168,144 H218', head: 'M216,140.5 L223,144 L216,147.5Z' },
      { e: '3-5', d: 'M392,32 H412 A8,8 0 0 1 420,40 V80 A8,8 0 0 0 428,88 H442' },
      { e: '4-5', d: 'M392,144 H412 A8,8 0 0 0 420,136 V96 A8,8 0 0 1 428,88 H442', head: 'M440,84.5 L447,88 L440,91.5Z' },
    ],
  },
  tall: {
    width: 352, height: 288, label: { x: 92, y: 92, anchor: 'start' },
    at: { 1: [0, 0], 2: [184, 0], 3: [0, 112], 4: [184, 112], 5: [92, 224] } as Record<number, number[]>,
    edges: [
      { e: '1-3', d: 'M84,64 V106', head: 'M80.5,104 L84,111 L87.5,104Z' },
      { e: '2-4', d: 'M268,64 V106', head: 'M264.5,104 L268,111 L271.5,104Z' },
      { e: '3-5', d: 'M84,176 V188 A8,8 0 0 0 92,196 H168 A8,8 0 0 1 176,204 V218' },
      { e: '4-5', d: 'M268,176 V188 A8,8 0 0 1 260,196 H184 A8,8 0 0 0 176,204 V218', head: 'M172.5,216 L176,223 L179.5,216Z' },
    ],
  },
}

type Status = 'blocked' | 'ready' | 'active' | 'done'
interface Beat { stage?: number; reset?: boolean; n?: Record<number, Status>; e?: Record<string, 'flow' | 'done'> }
const START: Record<number, Status> = { 1: 'ready', 2: 'ready', 3: 'blocked', 4: 'blocked', 5: 'blocked' }
const BEATS: Beat[] = [
  { stage: 0, reset: true }, { stage: 1 }, { stage: 2 },
  { n: { 1: 'active' } }, { n: { 2: 'active' } },
  { n: { 1: 'done' }, e: { '1-3': 'flow' } }, { n: { 3: 'ready' }, e: { '1-3': 'done' } },
  { n: { 3: 'active', 2: 'done' }, e: { '2-4': 'flow' } }, { n: { 4: 'ready' }, e: { '2-4': 'done' } },
  { n: { 4: 'active' } },
  { n: { 3: 'done' }, e: { '3-5': 'flow' } }, { e: { '3-5': 'done' } },
  { n: { 4: 'done' }, e: { '4-5': 'flow' } }, { n: { 5: 'ready' }, e: { '4-5': 'done' } },
  { n: { 5: 'active' } }, { n: { 5: 'done' } },
  { stage: 3 }, {},
]
// The frame shown with reduced motion, and before the page hydrates: work under way.
const STILL = 10

const status = reactive<Record<number, Status>>({ ...START })
const flow = reactive<Record<string, string>>({})
const stage = ref(0)
// Loop steps taken so far. The progress arc and dot count forward from it, so moving from review
// back to the Brain keeps going round: a closed path wraps distances past 100%.
const steps = ref(0)
const frontier = computed(() => Object.values(status).filter((s) => s === 'ready' || s === 'active').length)

function apply(b: Beat) {
  if (b.reset) {
    Object.assign(status, START)
    for (const k of Object.keys(flow)) delete flow[k]
  }
  Object.assign(status, b.n ?? {})
  Object.assign(flow, b.e ?? {})
  if (b.stage !== undefined && b.stage !== stage.value) {
    steps.value += (b.stage - stage.value + 4) % 4
    stage.value = b.stage
  }
}
for (let i = 0; i <= STILL; i++) apply(BEATS[i])

const root = ref<HTMLElement>()
const zoom = ref(1)
const stacked = ref(false)
const tall = ref(false)
const graph = computed(() => (tall.value ? GRAPHS.tall : GRAPHS.wide))
let timer: ReturnType<typeof setInterval> | undefined
let observer: ResizeObserver | undefined
onMounted(() => {
  observer = new ResizeObserver(([entry]) => {
    // Beside each other from 1088px, stacked from 664px, and stacked with the tall graph below.
    const width = entry.contentRect.width
    stacked.value = width < 1088
    tall.value = width < 664
    zoom.value = Math.min(1, width / (tall.value ? 400 : stacked.value ? 664 : 1088))
  })
  observer.observe(root.value!)
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return
  let i = STILL + 1
  timer = setInterval(() => apply(BEATS[i++ % BEATS.length]), 1000)
})
onUnmounted(() => {
  clearInterval(timer)
  observer?.disconnect()
})
</script>

<template>
  <div v-if="copy" ref="root" class="work-loop">
    <div class="diagram" :class="{ stacked, tall }" :style="{ zoom }" aria-hidden="true">
      <div class="ring">
        <svg viewBox="0 0 400 400">
          <path class="track" :d="TRACK" />
          <path class="progress" pathLength="100" :d="TRACK" :style="{ strokeDashoffset: 25 - steps * 25 }" />
        </svg>
        <svg v-for="at in [12.5, 37.5, 62.5, 87.5]" :key="at" class="chevron" :style="{ offsetDistance: at + '%' }" viewBox="0 0 10 10">
          <path d="M3,1.5 L7,5 L3,8.5" />
        </svg>
        <span class="comet" :style="{ offsetDistance: steps * 25 + '%' }"></span>
        <div class="core" :class="{ lit: stage === 0 || stage === 3 }"><b>.brain</b><span>{{ copy.core }}</span></div>
        <div v-for="(s, i) in stages" :key="s.skill" class="stage" :class="{ on: stage === i }" :style="{ left: s.x + 'px', top: s.y + 'px' }">
          <span class="num">0{{ i + 1 }}</span>
          <span class="name">{{ copy.stages[i] }}</span>
          <span class="skill">{{ s.skill }}</span>
        </div>
      </div>
      <div class="link" :class="{ on: stage === 2 }"></div>
      <div class="panel">
        <div class="head">
          <span>Beads</span><span class="epic">app-c7d2 · {{ copy.epic }}</span>
          <span class="frontier">{{ copy.frontier }} <b>{{ frontier }}</b></span>
        </div>
        <div class="graph" :style="{ width: graph.width + 'px', height: graph.height + 'px' }">
          <svg :viewBox="`0 0 ${graph.width} ${graph.height}`">
            <g v-for="edge in graph.edges" :key="edge.e" class="edge" :class="flow[edge.e]">
              <path class="line" :d="edge.d" />
              <path class="beam" pathLength="100" :d="edge.d" />
              <path v-if="edge.head" class="head" :d="edge.head" />
            </g>
            <text class="label" :x="graph.label.x" :y="graph.label.y" :text-anchor="graph.label.anchor">{{ copy.blocks }}</text>
          </svg>
          <div v-for="(issue, i) in issues" :key="issue.k" class="issue" :class="status[issue.k]" :style="{ left: graph.at[issue.k][0] + 'px', top: graph.at[issue.k][1] + 'px' }">
            <div class="meta">
              <svg class="glyph" viewBox="0 0 14 14"><use :href="`#work-loop-${status[issue.k]}`" /></svg>
              <span class="id">app-c7d2.{{ issue.k }}</span>
              <span class="avatar"><AgentIcon :agent="issue.agent" /></span>
            </div>
            <div class="title">{{ copy.issues[i] }}</div>
          </div>
        </div>
        <div class="legend">
          <span v-for="(s, i) in ['ready', 'active', 'blocked', 'done']" :key="s">
            <svg class="glyph" viewBox="0 0 14 14"><use :href="`#work-loop-${s}`" /></svg>{{ copy.legend[i] }}
          </span>
        </div>
      </div>
    </div>
    <svg width="0" height="0" class="defs">
      <symbol id="work-loop-blocked" viewBox="0 0 14 14"><circle class="g-blocked" cx="7" cy="7" r="5.5" /></symbol>
      <symbol id="work-loop-ready" viewBox="0 0 14 14"><circle class="g-ring" cx="7" cy="7" r="5.5" /></symbol>
      <symbol id="work-loop-active" viewBox="0 0 14 14"><circle class="g-ring" cx="7" cy="7" r="5.5" /><path class="g-fill" d="M7,3 A4,4 0 0 1 7,11 Z" /></symbol>
      <symbol id="work-loop-done" viewBox="0 0 14 14"><circle class="g-fill" cx="7" cy="7" r="6.5" /><path class="g-check" d="M4.3,7.2 L6.2,9 L9.8,5.2" /></symbol>
    </svg>
  </div>
</template>

<style scoped>
.work-loop {
  --ease: cubic-bezier(0.2, 0.8, 0.2, 1);
  --glow: color-mix(in srgb, var(--vp-c-brand-1) 16%, transparent);
  --line: var(--vp-c-divider);
  --line-strong: color-mix(in srgb, var(--vp-c-text-3) 45%, transparent);
  margin-top: 40px;
}
.defs {
  position: absolute;
}
.diagram {
  display: grid;
  grid-template-columns: 400px 24px 664px;
  align-items: center;
  width: 1088px;
}
.diagram.stacked {
  grid-template-columns: 664px;
  justify-items: center;
  row-gap: 8px;
  width: 664px;
}
.stacked .link {
  display: none;
}
.diagram.tall {
  grid-template-columns: 400px;
  width: 400px;
}
.tall .panel {
  width: 400px;
}
.tall .head {
  flex-wrap: wrap;
}
.tall .legend {
  flex-wrap: wrap;
  gap: 8px 16px;
}

/* The loop: a rounded-square track on the 8px grid, with direction marks at the corners. */
.ring {
  position: relative;
  width: 400px;
  height: 400px;
}
.ring > svg {
  position: absolute;
  inset: 0;
  overflow: visible;
}
.track {
  fill: none;
  stroke: var(--line-strong);
  stroke-width: 1;
}
.progress {
  fill: none;
  stroke: var(--vp-c-brand-1);
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-dasharray: 25 75;
  transition: stroke-dashoffset 0.9s var(--ease);
}
.chevron,
.comet {
  position: absolute;
  left: 0;
  top: 0;
  offset-path: path('M64,200 V112 A48,48 0 0 1 112,64 H288 A48,48 0 0 1 336,112 V288 A48,48 0 0 1 288,336 H112 A48,48 0 0 1 64,288 Z');
}
.chevron {
  width: 10px;
  height: 10px;
  offset-rotate: auto;
}
.chevron path {
  fill: none;
  stroke: var(--vp-c-text-3);
  stroke-width: 1.4;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.comet {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--vp-c-brand-1);
  box-shadow: 0 0 0 4px var(--glow), 0 0 16px var(--vp-c-brand-1);
  offset-rotate: 0deg;
  transition: offset-distance 0.9s var(--ease);
}
.stage,
.core {
  position: absolute;
  transform: translate(-50%, -50%);
  text-align: center;
  border: 1px solid var(--line);
}
.stage {
  width: 136px;
  padding: 8px 10px;
  border-radius: 10px;
  background: var(--vp-c-bg-soft);
  transition: border-color 0.5s var(--ease);
}
.stage.on {
  border-color: var(--vp-c-brand-1);
}
.num,
.skill {
  display: block;
  font: 400 11px var(--vp-font-family-mono);
  color: var(--vp-c-text-3);
}
.num {
  font-weight: 500;
  transition: color 0.5s var(--ease);
}
.stage.on .num {
  color: var(--vp-c-brand-1);
}
.name {
  display: block;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--vp-c-text-1);
}
.skill {
  margin-top: 2px;
}
.core {
  left: 200px;
  top: 200px;
  width: 112px;
  padding: 12px 8px;
  border-radius: 14px;
  background: var(--vp-c-bg);
  transition: border-color 0.7s var(--ease), box-shadow 0.7s var(--ease);
}
.core b {
  display: block;
  font: 500 16px var(--vp-font-family-mono);
  color: var(--vp-c-brand-1);
}
.core span {
  font-size: 12px;
  color: var(--vp-c-text-3);
}
.core.lit {
  border-color: var(--vp-c-brand-1);
  box-shadow: 0 0 0 1px var(--vp-c-brand-1);
}
.link {
  position: relative;
  height: 1px;
  background: var(--line-strong);
  transition: background 0.5s var(--ease);
}
.link::after {
  content: '';
  position: absolute;
  right: -1px;
  top: -3px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: inherit;
}
.link.on {
  background: var(--vp-c-brand-1);
}

/* The work graph: issues as quiet cards, where the status glyph, ID and agent carry the meaning. */
.panel {
  width: 664px;
  padding: 20px 24px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--vp-c-bg-alt);
}
.head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 20px;
  font-size: 13px;
  color: var(--vp-c-text-2);
}
.epic {
  font: 500 12px var(--vp-font-family-mono);
  color: var(--vp-c-text-3);
}
.frontier {
  margin-left: auto;
  font-size: 12px;
  color: var(--vp-c-text-3);
}
.frontier b {
  color: var(--vp-c-brand-1);
  font-weight: 600;
}
.graph {
  position: relative;
}
.graph > svg {
  position: absolute;
  inset: 0;
  overflow: visible;
}
.line {
  fill: none;
  stroke: var(--line-strong);
  stroke-width: 1;
}
/* A beam travels the edge when an issue closes and unblocks the next, then the edge stays lit. */
.beam {
  fill: none;
  stroke: var(--vp-c-brand-1);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-dasharray: 18 82;
  stroke-dashoffset: 18;
  opacity: 0;
}
.edge.flow .beam {
  opacity: 1;
  filter: drop-shadow(0 0 4px var(--vp-c-brand-1));
  animation: beam 1s var(--ease) forwards;
}
.edge.done .beam {
  opacity: 0.55;
  stroke-width: 1;
  stroke-dasharray: none;
}
@keyframes beam {
  to {
    stroke-dashoffset: -100;
  }
}
.edge .head {
  fill: var(--line-strong);
  transition: fill 0.5s var(--ease);
}
.edge.flow .head,
.edge.done .head {
  fill: var(--vp-c-brand-1);
}
.label {
  font: 400 10px var(--vp-font-family-mono);
  fill: var(--vp-c-text-3);
}
.issue {
  position: absolute;
  width: 168px;
  height: 64px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--vp-c-bg-soft);
  transition: opacity 0.5s var(--ease), border-color 0.5s var(--ease);
}
.issue.blocked {
  opacity: 0.55;
}
.issue.active {
  border-color: var(--line-strong);
}
.issue.active::before {
  content: '';
  position: absolute;
  left: -1px;
  top: 12px;
  bottom: 12px;
  width: 2px;
  border-radius: 2px;
  background: var(--vp-c-brand-1);
}
.meta {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 18px;
}
.id {
  font: 400 11px var(--vp-font-family-mono);
  color: var(--vp-c-text-3);
}
.title {
  margin-top: 6px;
  font-size: 14px;
  font-weight: 500;
  line-height: 1.4;
  white-space: nowrap;
  color: var(--vp-c-text-1);
  transition: color 0.5s var(--ease);
}
.issue.done .title {
  color: var(--vp-c-text-3);
}
.avatar {
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  margin-left: auto;
  border: 1px solid var(--line);
  border-radius: 50%;
  background: var(--vp-c-bg);
  opacity: 0;
  transform: scale(0.6);
  transition: opacity 0.4s var(--ease), transform 0.4s var(--ease);
}
.avatar :deep(img) {
  width: 12px;
  height: 12px;
}
.issue.active .avatar,
.issue.done .avatar {
  opacity: 1;
  transform: none;
}
.glyph {
  width: 14px;
  height: 14px;
  flex: none;
}
.issue.active .glyph {
  animation: spin 2.4s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.g-blocked {
  fill: none;
  stroke: var(--vp-c-text-3);
  stroke-width: 1.5;
  stroke-dasharray: 2 2.2;
}
.g-ring {
  fill: none;
  stroke: var(--vp-c-brand-1);
  stroke-width: 1.5;
}
.g-fill {
  fill: var(--vp-c-brand-1);
}
.g-check {
  fill: none;
  stroke: var(--vp-c-bg);
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.legend {
  display: flex;
  gap: 20px;
  margin-top: 20px;
  font-size: 12px;
  color: var(--vp-c-text-3);
}
.legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

@media (prefers-reduced-motion: reduce) {
  .work-loop * {
    animation: none !important;
    transition: none !important;
  }
}
</style>
