<script setup lang="ts">
import { computed } from 'vue'
import { useData } from 'vitepress'

// ADRs carry `status:` and design docs `lifecycle:` in frontmatter, which a page does not show, so
// a superseded decision or an abandoned design would read like a current one.
const { frontmatter } = useData()
const label = computed(() => {
  const { status, lifecycle } = frontmatter.value
  if (status != null) return `Status: ${status}`
  if (lifecycle != null) return `Lifecycle: ${lifecycle}`
  return ''
})
const type = computed(() => {
  const value = label.value.toLowerCase()
  if (/superseded|abandoned|deprecated|rejected/.test(value)) return 'danger'
  if (/accepted|active|shipped/.test(value)) return 'tip'
  return 'info'
})
</script>

<template>
  <p v-if="label" class="page-status"><Badge :type="type" :text="label" /></p>
</template>
