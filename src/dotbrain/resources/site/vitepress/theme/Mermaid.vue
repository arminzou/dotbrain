<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import { useData } from 'vitepress'

// Draws one ```mermaid block. Mermaid needs the browser, so it loads and renders after mount, and
// renders again when the reader switches between light and dark themes. Layout, curves, and font
// come from Mermaid's config; colours come from `.mermaid-diagram` in custom.css.
const props = defineProps<{ code: string }>()
const { isDark } = useData()
const id = `mermaid-${useId()}`
const code = decodeURIComponent(props.code)
const container = ref<HTMLElement>()
const svg = ref('')
const error = ref('')
const minWidth = ref('')

// A sequence diagram is laid out to fill the content column: the gap between participants is
// whatever the column leaves after the participant boxes, so text keeps its size and messages get
// room instead of the whole drawing being scaled up. With many participants, the boxes narrow
// (down to 90px) before the diagram falls back to scrolling.
const participants = (code.match(/^\s*(participant|actor)\s/gm) ?? []).length
const sideMargin = 8
const minimumGap = 48
let renderedFor = 0

function sequenceLayout() {
  const available = container.value?.clientWidth ?? 0
  if (participants < 2 || !available) return { width: 120, actorMargin: minimumGap }
  const room = available - 2 * sideMargin
  const width = Math.max(90, Math.min(120, Math.floor((room - (participants - 1) * minimumGap) / participants)))
  const actorMargin = Math.max(minimumGap, Math.floor((room - participants * width) / (participants - 1)))
  return { width, actorMargin }
}

async function render() {
  const { default: mermaid } = await import('mermaid')
  const fontFamily = getComputedStyle(document.documentElement).getPropertyValue('--vp-font-family-base')
  renderedFor = container.value?.clientWidth ?? 0
  mermaid.initialize({
    startOnLoad: false,
    theme: isDark.value ? 'neo-dark' : 'neo',
    look: 'neo',
    // Sequence diagrams take their participant, message, and note sizes from this top-level
    // size (default 16), overriding the per-kind sequence settings; 13 matches the flowcharts.
    fontSize: 13,
    themeVariables: { fontFamily, fontSize: '13px' },
    flowchart: { nodeSpacing: 24, rankSpacing: 28, padding: 8, minNodeWidth: 0, wrappingWidth: 400 },
    sequence: {
      wrap: true,
      ...sequenceLayout(),
      diagramMarginX: sideMargin,
      messageMargin: 36,
      noteMargin: 8,
      boxMargin: 8
    }
  })
  // A syntax error would otherwise leave an empty space and a console message only; show the
  // error and the source on the page so a broken diagram is noticed, since the build still passes.
  try {
    svg.value = (await mermaid.render(id, code)).svg
    error.value = ''
  } catch (reason) {
    svg.value = ''
    error.value = reason instanceof Error ? reason.message : String(reason)
    return
  }
  // A wide diagram shrinks to fit only down to 85% of its size; past that it scrolls sideways,
  // so labels stay readable on narrow screens.
  const width = Number(svg.value.match(/viewBox="[\d.-]+ [\d.-]+ ([\d.]+)/)?.[1])
  minWidth.value = width ? `${Math.round(width * 0.85)}px` : ''
}

let observer: ResizeObserver | undefined
onMounted(() => {
  render()
  if (participants < 2) return
  // Re-lay out a sequence diagram when the column width changes noticeably.
  observer = new ResizeObserver(([entry]) => {
    if (Math.abs(entry.contentRect.width - renderedFor) >= 24) render()
  })
  observer.observe(container.value!)
})
onBeforeUnmount(() => observer?.disconnect())
watch(isDark, render)
</script>

<template>
  <div ref="container" class="mermaid-diagram">
    <div v-if="error" class="mermaid-error" role="alert">
      <strong>Mermaid could not draw this diagram.</strong>
      <pre>{{ error }}</pre>
      <pre>{{ code }}</pre>
    </div>
    <div v-else :style="{ minWidth }" v-html="svg" />
  </div>
</template>
