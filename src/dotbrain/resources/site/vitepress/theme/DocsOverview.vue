<script setup lang="ts">
import { useData } from 'vitepress'
import HomeTiles from './HomeTiles.vue'

// The home page's docs: one tile per docs/ folder, with its most recently updated pages.
const { theme } = useData()
</script>

<template>
  <HomeTiles title="Docs" :section="theme.docs ?? { tiles: [], rest: [] }" />
</template>
