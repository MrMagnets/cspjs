<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { discussionApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import MarkdownView from '@/components/MarkdownView.vue'
import MarkdownEditor from '@/components/MarkdownEditor.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const loading = ref(true)
const post = ref(null)
const comment = ref('')
const sending = ref(false)
const reportDialog = ref(false)
const reportReason = ref('')
const reporting = ref(false)

async function load() {
  loading.value = true
  try {
    post.value = await discussionApi.detail(route.params.id)
  } catch (err) {
    ElMessage.error(err.message || '帖子加载失败')
  } finally {
    loading.value = false
  }
}

async function sendComment() {
  if (!comment.value.trim()) return
  sending.value = true
  try {
    const c = await discussionApi.comment(route.params.id, { content_md: comment.value })
    post.value.comments.push(c)
    post.value.comment_count += 1
    comment.value = ''
    ElMessage.success('回复成功')
  } catch (err) {
    ElMessage.error(err.message || '回复失败')
  } finally {
    sending.value = false
  }
}

async function submitReport() {
  if (!reportReason.value.trim()) return
  reporting.value = true
  try {
    await discussionApi.report({ target_type: 'discussion', target_id: Number(route.params.id), reason: reportReason.value })
    ElMessage.success('举报已提交，管理员会尽快处理')
    reportDialog.value = false
    reportReason.value = ''
  } catch (err) {
    ElMessage.error(err.message || '举报失败')
  } finally {
    reporting.value = false
  }
}

function fmt(dt) {
  return new Date(dt).toLocaleString('zh-CN', { hour12: false })
}

onMounted(load)
</script>

<template>
  <div class="page detail-page">
    <el-skeleton v-if="loading" :rows="8" animated />
    <template v-else-if="post">
      <el-page-header content="返回讨论区" @back="router.push({ name: 'discussions' })" />
      <article class="post card">
        <div class="post-head">
          <el-tag size="small" effect="plain">{{ post.category }}</el-tag>
          <h1>{{ post.title }}</h1>
          <el-button size="small" type="danger" plain @click="reportDialog = true">举报</el-button>
        </div>
        <div class="post-meta">{{ post.author_name }} · {{ fmt(post.created_at) }}</div>
        <MarkdownView :content="post.content_md" />
      </article>

      <section class="comments">
        <h2>回复 <small>{{ post.comments.length }}</small></h2>
        <div v-for="c in post.comments" :key="c.id" class="comment">
          <div class="c-avatar">{{ c.author_name?.slice(0, 1) || '?' }}</div>
          <div class="c-body">
            <div class="c-meta"><strong>{{ c.author_name }}</strong> · {{ fmt(c.created_at) }}</div>
            <MarkdownView :content="c.content_md" />
          </div>
        </div>
        <el-empty v-if="!post.comments.length" description="还没有回复，来抢沙发" />

        <div v-if="auth.isLoggedIn && !post.is_locked" class="reply-box">
          <MarkdownEditor v-model="comment" :rows="4" placeholder="写下你的回复，支持 Markdown 与 KaTeX..." />
          <div class="reply-actions">
            <el-button type="primary" :loading="sending" @click="sendComment">发表回复</el-button>
          </div>
        </div>
        <el-alert v-else-if="post.is_locked" type="info" :closable="false" title="帖子已被锁定，无法回复" />
        <el-alert v-else type="info" :closable="false" title="登录后即可参与讨论" />
      </section>
    </template>

    <el-dialog v-model="reportDialog" title="举报帖子" width="420px">
      <el-input v-model="reportReason" type="textarea" :rows="4" maxlength="500" show-word-limit placeholder="请说明举报原因" />
      <template #footer>
        <el-button @click="reportDialog = false">取消</el-button>
        <el-button type="danger" :loading="reporting" @click="submitReport">提交举报</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.detail-page { max-width: 880px; margin: 0 auto; }
.post { margin-top: 16px; border-radius: 16px; }
.post-head { display: flex; align-items: center; gap: 10px; }
.post-head h1 { flex: 1; font-size: 24px; margin: 0; }
.post-meta { color: var(--muted); font-size: 12px; margin: 10px 0 18px; }
.comments { margin-top: 28px; }
.comments h2 { font-size: 18px; }
.comments h2 small { color: var(--muted); font-weight: 400; }
.comment { display: flex; gap: 12px; padding: 14px 0; border-bottom: 1px solid var(--border); }
.c-avatar { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 10px; background: #eef4ff; color: #2563eb; font-weight: 700; flex: none; }
.c-body { flex: 1; min-width: 0; }
.c-meta { font-size: 12px; color: var(--muted); margin-bottom: 6px; }
.reply-box { margin-top: 20px; }
.reply-actions { display: flex; justify-content: flex-end; margin-top: 10px; }
</style>
