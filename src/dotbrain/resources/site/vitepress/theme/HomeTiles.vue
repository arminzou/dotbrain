<script setup lang="ts">
import { withBase } from 'vitepress'

// The home page's tile grid, shared by <DocsOverview /> and <LearnOverview /> so both look the same:
// each tile has a name, a summary, a few pages with their last commit dates, and "and N more".
// dotbrain sends the most recently active tiles, at most six, and the rest as one line of links.
// Renders nothing when the section is empty.
defineProps<{ title: string; section: { tiles: any[]; rest: any[] } }>()
</script>

<template>
  <div v-if="section.tiles.length" class="home-overview">
    <h2>{{ title }}</h2>
    <div class="home-tiles">
      <section v-for="tile in section.tiles" :key="tile.name" class="home-tile">
        <h3>{{ tile.name }} <span class="home-tile-summary">{{ tile.summary }}</span></h3>
        <code v-if="tile.folder" class="home-tile-folder">{{ tile.folder }}</code>
        <ul>
          <li v-for="page in tile.pages" :key="page.link">
            <a :href="withBase(page.link + '.html')">{{ page.text }}</a>
            <span v-if="page.updated" class="home-tile-date">{{ page.updated }}</span>
          </li>
        </ul>
        <p v-if="tile.more" class="home-tile-more">and {{ tile.more }} more</p>
      </section>
    </div>
    <p v-if="section.rest.length" class="home-rest">
      More:
      <template v-for="(item, index) in section.rest" :key="item.name">
        <a :href="withBase(item.link + '.html')">{{ item.name }}</a>
        <span class="home-tile-summary"> · {{ item.summary }}</span><template v-if="index < section.rest.length - 1">, </template>
      </template>
    </p>
  </div>
</template>
