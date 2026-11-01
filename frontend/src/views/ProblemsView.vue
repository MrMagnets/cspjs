<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { problemApi, tagApi } from '@/api'
import ProblemCard from '@/components/ProblemCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import { SOURCE_LABELS, TYPE_LABELS } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)
const tags = ref([])

const filters = reactive({
  type: '',
  tag: '',
  source_tag: '',
  exam: '',
  year: null,
  keyword: '',
})

const years = computed(() => {
  const current = new Date().getFullYear()
  return Array.from({ length: 10 }, (_, i) => current - i)
})

const knowledgeTags = computed(() => tags.value.filter((t) => t.category === '知识点'))
const sourceTags = computed(() => tags.value.filter((t) => t.category !== '知识点'))

const activeFilterCount = computed(
  () => [filters.type, filters.tag, filters.source_tag, filters.exam, filters.year, filters.keyword].filter(Boolean).length,
)

let keywordTimer = null

function syncQuery() {
  const query = {}
  if (filters.type) query.type = filters.type
  if (filters.tag) query.tag = filters.tag
  if (filters.source_tag) query.source_tag = filters.source_tag
  if (filters.exam) query.exam = filters.exam
  if (filters.year) query.year = String(filters.year)
  if (filters.keyword.trim()) query.keyword = filters.keyword.trim()
  if (page.value > 1) query.page = String(page.value)
  router.replace({ name: 'problems', query })
}

function hydrateFromQuery(query) {
  const wanted = {
    type: typeof query.type === 'string' ? query.type : '',
    tag: typeof query.tag === 'string' ? query.tag : '',
    source_tag: typeof query.source_tag === 'string' ? query.source_tag : '',
    exam: typeof query.exam === 'string' ? query.exam : '',
    year: query.year ? Number(query.year) || null : null,
    keyword: typeof query.keyword === 'string' ? query.keyword : '',
  }
  const wantedPage = Math.max(1, Number(query.page) || 1)
  const same =
    wanted.type === filters.type &&
    wanted.tag === filters.tag &&
    wanted.source_tag === filters.source_tag &&
    wanted.exam === filters.exam &&
    wanted.year === filters.year &&
    wanted.keyword === filters.keyword &&
    wantedPage === page.value
  if (same) return false
  Object.assign(filters, wanted)
  page.value = wantedPage
  return true
}

async function load() {
  loading.value = true
  try {
    const data = await problemApi.list({
      type: filters.type || undefined,
      tag: filters.tag || undefined,
      source_tag: filters.source_tag || undefined,
      exam: filters.exam || undefined,
      year: filters.year || undefined,
      keyword: filters.keyword.trim() || undefined,
      page: page.value,
      page_size: pageSize.value,
      status: 'approved',
    })
    items.value = data.items
    total.value = data.total
  } catch (err) {
    ElMessage.error(err.message || '加载题库失败')
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  page.value = 1
  syncQuery()
  load()
}

function resetFilters() {
  Object.assign(filters, { type: '', tag: '', source_tag: '', exam: '', year: null, keyword: '' })
  applyFilters()
}

function toggleTag(name) {
  filters.tag = filters.tag === name ? '' : name
  applyFilters()
}

function changePage(next) {
  page.value = next
  syncQuery()
  load()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

watch(
  () => filters.keyword,
  () => {
    clearTimeout(keywordTimer)
    keywordTimer = setTimeout(applyFilters, 400)
  },
)

watch(
  () => [filters.type, filters.source_tag, filters.exam, filters.year],
  () => applyFilters(),
)

// 支持从 URL 直接带筛选条件（如 /problems?type=reading&tag=排序）
watch(
  () => route.query,
  (query) => {
    if (route.name !== 'problems') return
    if (hydrateFromQuery(query)) load()
  },
)

onMounted(async () => {
  hydrateFromQuery(route.query)
  await load()
  try {
    tags.value = await tagApi.list()
  } catch {
    /* 标签加载失败不影响题库浏览 */
  }
})
</script>

<template>
  <div class="page">
    <div class="page-title">
      题库
      <span class="sub">共 {{ total }} 道已通过审核的题目</span>
      <span class="spacer" />
      <el-button type="primary" @click="router.push({ name: 'problem-create' })">投稿题目</el-button>
    </div>

    <div class="layout">
      <aside class="filters card">
        <div class="filter-head">
          <span>筛选</span>
          <el-button v-if="activeFilterCount" link type="primary" size="small" @click="resetFilters">
            清空
          </el-button>
        </div>

        <div class="field">
          <label>关键词</label>
          <el-input v-model="filters.keyword" placeholder="标题或题干关键字" clearable />
        </div>

        <div class="field">
          <label>题型</label>
          <el-select v-model="filters.type" placeholder="全部题型" clearable style="width: 100%">
            <el-option v-for="(label, value) in TYPE_LABELS" :key="value" :label="label" :value="value" />
          </el-select>
        </div>

        <div class="field">
          <label>来源</label>
          <el-select v-model="filters.source_tag" placeholder="全部来源" clearable style="width: 100%">
            <el-option v-for="(label, value) in SOURCE_LABELS" :key="value" :label="label" :value="value" />
          </el-select>
        </div>

        <div class="field">
          <label>试卷</label>
          <el-select v-model="filters.exam" placeholder="全部试卷" clearable style="width: 100%">
            <el-option label="CSP-J" value="CSP-J" />
            <el-option label="CSP-S" value="CSP-S" />
          </el-select>
        </div>

        <div class="field">
          <label>年份</label>
          <el-select v-model="filters.year" placeholder="全部年份" clearable style="width: 100%">
            <el-option v-for="y in years" :key="y" :label="`${y} 年`" :value="y" />
          </el-select>
        </div>

        <div class="field">
          <label>知识点</label>
          <div class="tag-cloud">
            <button
              v-for="tag in knowledgeTags"
              :key="tag.id"
              class="tag-chip"
              :class="{ active: filters.tag === tag.name }"
              @click="toggleTag(tag.name)"
            >
              {{ tag.name }}
            </button>
          </div>
        </div>

        <div v-if="sourceTags.length" class="field">
          <label>来源标签</label>
          <div class="tag-cloud">
            <button
              v-for="tag in sourceTags"
              :key="tag.id"
              class="tag-chip"
              :class="{ active: filters.tag === tag.name }"
              @click="toggleTag(tag.name)"
            >
              {{ tag.name }}
            </button>
          </div>
        </div>
      </aside>

      <section class="results">
        <div v-loading="loading" class="result-grid">
          <ProblemCard v-for="problem in items" :key="problem.id" :problem="problem" />
        </div>

        <EmptyState
          v-if="!loading && !items.length"
          title="没有匹配的题目"
          description="试试减少筛选条件，或者投稿一道新题目"
          action-text="清空筛选"
          @action="resetFilters"
        />

        <div v-if="total > pageSize" class="pager">
          <el-pagination
            layout="prev, pager, next"
            :total="total"
            :page-size="pageSize"
            :current-page="page"
            background
            @current-change="changePage"
          />
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 244px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

.filters {
  position: sticky;
  top: 82px;
  padding: 18px;
}

.filter-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 700;
  font-size: 14.5px;
  margin-bottom: 12px;
}

.field {
  margin-bottom: 16px;
}

.field label {
  display: block;
  font-size: 12.5px;
  color: var(--muted);
  margin-bottom: 6px;
  font-weight: 550;
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-chip {
  border: 1px solid var(--border);
  background: #fff;
  color: #55697a;
  font-size: 12.5px;
  padding: 3px 10px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.tag-chip:hover {
  border-color: #b9d6cd;
  color: var(--brand-dark);
}

.tag-chip.active {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  min-height: 120px;
}

.pager {
  display: flex;
  justify-content: center;
  margin-top: 26px;
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }

  .filters {
    position: static;
  }

  .result-grid {
    grid-template-columns: 1fr;
  }
}
</style>
