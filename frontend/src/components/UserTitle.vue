<script setup>
import { computed } from 'vue'

const props = defineProps({
  user: { type: Object, default: null },
  title: { type: String, default: '' },
  role: { type: String, default: '' },
})

const rawTitle = computed(() => props.user?.title ?? props.title ?? '')
const role = computed(() => props.user?.role ?? props.role ?? '')

const isAdmin = computed(() => role.value === 'admin')
const isCheater = computed(() => /作弊|棕名/.test(rawTitle.value))

const label = computed(() => {
  if (isAdmin.value) return '紫名管理员'
  if (isCheater.value) return '作弊者'
  return rawTitle.value.trim()
})

const kind = computed(() => {
  if (isAdmin.value) return 'admin'
  if (isCheater.value) return 'cheater'
  return 'normal'
})
</script>

<template>
  <span v-if="label" class="user-title" :class="kind">{{ label }}</span>
</template>

<style scoped>
.user-title {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  line-height: 18px;
  white-space: nowrap;
}
.user-title.admin {
  color: #6d28d9;
  background: linear-gradient(135deg, #f3e8ff, #ede9fe);
  border: 1px solid #c4b5fd;
  box-shadow: 0 0 0 1px rgba(139, 92, 246, .08);
}
.user-title.cheater {
  color: #7a4a1d;
  background: #f3e7da;
  border: 1px solid #d8b894;
}
.user-title.normal {
  color: #b7791f;
  background: #fff7e6;
  border: 1px solid #f2d39b;
}
</style>
