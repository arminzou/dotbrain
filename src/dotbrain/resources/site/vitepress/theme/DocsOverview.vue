<script setup lang="ts">
import { useData, withBase } from 'vitepress';

// Lists the Brain's docs/ pages for its home page, <DocsOverview />: one tile per docs/ folder, with
// its page count and most recently updated pages. It renders nothing when docs/ has no pages.
const { theme } = useData()
const tiles = theme.value.docs ?? []
</script>

<template>
  <div v-if="tiles.length" class="docs-overview">
    <h2>Docs</h2>
    <div class="docs-tiles">
      <section v-for="tile in tiles" :key="tile.folder" class="docs-tile">
        <h3>{{ tile.name }} <span class="docs-count">{{ tile.count }} {{ tile.count === 1 ? 'page' : 'pages' }}</span></h3>
        <code class="docs-folder">{{ tile.folder }}</code>
        <ul>
          <li v-for="page in tile.pages" :key="page.link">
            <a :href="withBase(page.link + '.html')">{{ page.text }}</a>
            <span v-if="page.updated" class="docs-date">{{ page.updated }}</span>
          </li>
        </ul>
        <p v-if="tile.more" class="docs-more">and {{ tile.more }} more</p>
      </section>
    </div>
  </div>
</template>
