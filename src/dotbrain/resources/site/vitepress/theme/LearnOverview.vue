<script setup lang="ts">
import { useData, withBase } from 'vitepress'

// Lists the Learn topics with their lessons and references, for a Brain's home page:
// <LearnOverview />. It renders nothing when the Brain has no learning workspace.
const { theme } = useData()
const topics = theme.value.learn ?? []
</script>

<template>
  <div v-if="topics.length" class="learn-overview">
    <h2>Learn</h2>
    <div class="learn-topics">
      <section v-for="topic in topics" :key="topic.name">
        <h3>{{ topic.name }}</h3>
        <ol>
          <li v-for="lesson in topic.lessons" :key="lesson.link">
            <a :href="withBase(lesson.link + '.html')">{{ lesson.text }}</a>
            <span v-if="lesson.description">{{ lesson.description }}</span>
          </li>
        </ol>
        <p v-if="topic.references.length" class="learn-references">
          References:
          <template v-for="(reference, index) in topic.references" :key="reference.link">
            <a :href="withBase(reference.link + '.html')">{{ reference.text }}</a><template v-if="index < topic.references.length - 1">, </template>
          </template>
        </p>
      </section>
    </div>
  </div>
</template>
