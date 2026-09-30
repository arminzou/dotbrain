import type { Theme } from 'vitepress'
import base from '@dotbrain/theme'
import brain from '@brain/theme'
import '@brain/style'

// A Brain's `.brain/site/theme/index.ts` either exports a whole theme (with a Layout or extends),
// which replaces the default, or an object whose enhanceApp adds to it.
const replaces = (theme: Partial<Theme> | undefined) => Boolean(theme && (theme.Layout || theme.extends))

export default (replaces(brain)
  ? brain
  : {
      ...base,
      enhanceApp(ctx) {
        base.enhanceApp?.(ctx)
        brain?.enhanceApp?.(ctx)
      }
    }) as Theme
