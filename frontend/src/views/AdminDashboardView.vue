<script setup>
const menus = [
  { to: '/admin/users', label: '用户管理', desc: '封禁 / 解封 / 称号' },
  { to: '/admin/contests', label: '比赛管理', desc: '创建 / 编辑 / 删除' },
  { to: '/admin/appeals', label: '申诉审核', desc: '录像复核 / 作弊判定' },
  { to: '/admin/audit', label: '陶片放逐', desc: '管理员操作审计' },
  { to: '/admin/review', label: '题目审核', desc: '通过 / 驳回投稿' },
  { to: '/admin/tags', label: '标签管理', desc: '知识点维护' },
]
</script>

<template>
  <div class="admin-layout">
    <aside class="admin-side">
      <div class="admin-brand">管理后台</div>
      <nav>
        <router-link v-for="m in menus" :key="m.to" :to="m.to" class="admin-link">
          <strong>{{ m.label }}</strong>
          <small>{{ m.desc }}</small>
        </router-link>
      </nav>
    </aside>
    <section class="admin-main">
      <router-view />
    </section>
  </div>
</template>

<style scoped>
.admin-layout {
  width: min(1320px, calc(100% - 40px));
  margin: 20px auto 40px;
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}
.admin-side {
  position: sticky;
  top: 82px;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid var(--border);
  background: #fff;
}
.admin-brand { font-weight: 800; font-size: 16px; padding: 4px 8px 14px; }
.admin-link {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border-radius: 10px;
  color: var(--text-strong);
  text-decoration: none;
  border: 1px solid transparent;
}
.admin-link small { color: var(--muted); font-size: 11px; }
.admin-link:hover { background: #f5f8fc; }
.admin-link.router-link-active {
  background: #eef4ff;
  border-color: #d6e4ff;
  color: #1d4ed8;
}
.admin-link.router-link-active small { color: #5b7cc9; }
.admin-main { min-width: 0; }
@media (max-width: 860px) {
  .admin-layout { grid-template-columns: 1fr; }
  .admin-side { position: static; }
  .admin-side nav { display: flex; gap: 6px; overflow-x: auto; }
  .admin-link { min-width: 120px; }
}
</style>
