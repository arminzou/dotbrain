<script setup lang="ts">
import { useData } from 'vitepress'
import HomeTiles from './HomeTiles.vue'

// The home page's Learn: one tile per topic, with its latest lessons. The sidebar's Learn section
// keeps every lesson in order. Renders nothing when the Brain has no lessons or references.
const { theme } = useData()
</script>

<template>
  <HomeTiles title="Learn" :section="theme.learn ?? { tiles: [], rest: [] }" />
</template>
