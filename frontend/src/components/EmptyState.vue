<script setup>
defineProps({
  title: { type: String, default: '暂无数据' },
  description: { type: String, default: '' },
  actionText: { type: String, default: '' },
})
defineEmits(['action'])
</script>

<template>
  <div class="empty-state">
    <div class="es-mark">∅</div>
    <p class="es-title">{{ title }}</p>
    <p v-if="description" class="es-desc">{{ description }}</p>
    <el-button v-if="actionText" type="primary" plain size="small" @click="$emit('action')">
      {{ actionText }}
    </el-button>
  </div>
</template>

<style scoped>
.empty-state {
  text-align: center;
  padding: 46px 20px;
  color: var(--muted);
}

.es-mark {
  width: 52px;
  height: 52px;
  margin: 0 auto 12px;
  border-radius: 50%;
  background: #f0f4f7;
  color: #9aabb9;
  font-size: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--mono);
}

.es-title {
  margin: 0 0 6px;
  font-size: 15px;
  color: #41525f;
  font-weight: 600;
}

.es-desc {
  margin: 0 0 14px;
  font-size: 13px;
  line-height: 1.7;
}
</style>
