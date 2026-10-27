<script setup lang="ts">
import { withBase } from 'vitepress'
import type { Agent } from './agents'

defineProps<{ agent: Agent }>()
</script>

<template>
  <template v-if="agent.themed">
    <img class="agent-icon only-light" :src="withBase(`/assets/agents/${agent.icon}-light.svg`)" alt="" width="20" height="20" />
    <img class="agent-icon only-dark" :src="withBase(`/assets/agents/${agent.icon}-dark.svg`)" alt="" width="20" height="20" />
  </template>
  <img v-else class="agent-icon" :src="withBase(`/assets/agents/${agent.icon}.svg`)" alt="" width="20" height="20" />
</template>

<style scoped>
.agent-icon {
  width: 20px;
  height: 20px;
  flex: none;
}
.only-dark,
.dark .only-light {
  display: none;
}
.dark .only-dark {
  display: block;
}
</style>
