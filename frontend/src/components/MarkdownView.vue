<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import katexModule from '@chyi13/markdown-it-katex'
import hljs from 'highlight.js/lib/core'
import cpp from 'highlight.js/lib/languages/cpp'
import c from 'highlight.js/lib/languages/c'
import python from 'highlight.js/lib/languages/python'
import javascript from 'highlight.js/lib/languages/javascript'
import plaintext from 'highlight.js/lib/languages/plaintext'
import DOMPurify from 'dompurify'

hljs.registerLanguage('cpp', cpp)
hljs.registerLanguage('c', c)
hljs.registerLanguage('python', python)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('plaintext', plaintext)

const props = defineProps({
  content: { type: String, default: '' },
})

const katexPlugin = katexModule?.default ?? katexModule

function escapeHtml(text) {
  return String(text).replace(
    /[&<>"']/g,
    (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch],
  )
}

function highlightCode(code, lang) {
  if (lang && hljs.getLanguage(lang)) {
    try {
      return `<pre class="hljs"><code>${hljs.highlight(code, { language: lang, ignoreIllegals: true }).value}</code></pre>`
    } catch {
      /* 落到纯文本 */
    }
  }
  return `<pre class="hljs"><code>${escapeHtml(code)}</code></pre>`
}

const md = new MarkdownIt({
  html: false, // 禁用原始 HTML，配合 DOMPurify 双重防护
  linkify: true,
  breaks: true,
  typographer: false,
  highlight: highlightCode,
})

md.use(katexPlugin, { throwOnError: false, errorColor: '#cc0000' })

// 外链新窗口打开
const defaultLinkOpen =
  md.renderer.rules.link_open || ((tokens, idx, options, env, self) => self.renderToken(tokens, idx, options))
md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  tokens[idx].attrSet('target', '_blank')
  tokens[idx].attrSet('rel', 'noopener noreferrer')
  return defaultLinkOpen(tokens, idx, options, env, self)
}

const html = computed(() => {
  if (!props.content) return ''
  const rendered = md.render(props.content)
  return DOMPurify.sanitize(rendered, {
    USE_PROFILES: { html: true, mathMl: true, svg: true },
    FORBID_TAGS: ['style', 'script', 'iframe', 'object', 'embed', 'form', 'input', 'button', 'textarea'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'srcdoc'],
  })
})
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html -->
  <div class="markdown-body" v-html="html" />
</template>
