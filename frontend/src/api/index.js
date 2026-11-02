import request from './client'

export const authApi = {
  register: (body) => request('/auth/register', { method: 'POST', body }),
  login: (body) => request('/auth/login', { method: 'POST', body }),
  me: () => request('/auth/me'),
}

export const problemApi = {
  list: (params) => request('/problems', { params }),
  detail: (id) => request(`/problems/${id}`),
  create: (body) => request('/problems', { method: 'POST', body }),
  update: (id, body) => request(`/problems/${id}`, { method: 'PUT', body }),
  remove: (id) => request(`/problems/${id}`, { method: 'DELETE' }),
  review: (id, body) => request(`/problems/${id}/review`, { method: 'POST', body }),
  answer: (id, answers) => request(`/problems/${id}/answer`, { method: 'POST', body: { answers } }),
  submissions: (id) => request(`/problems/${id}/submissions`),
  pending: (params) => request('/admin/pending', { params }),
}

export const tagApi = {
  list: () => request('/tags'),
  create: (body) => request('/tags', { method: 'POST', body }),
  remove: (id) => request(`/tags/${id}`, { method: 'DELETE' }),
}

export const listApi = {
  list: (params) => request('/problem-lists', { params }),
  detail: (id) => request(`/problem-lists/${id}`),
  create: (body) => request('/problem-lists', { method: 'POST', body }),
  update: (id, body) => request(`/problem-lists/${id}`, { method: 'PUT', body }),
  remove: (id) => request(`/problem-lists/${id}`, { method: 'DELETE' }),
  addItem: (id, problemId) =>
    request(`/problem-lists/${id}/items`, { method: 'POST', body: { problem_id: problemId } }),
  removeItem: (id, problemId) =>
    request(`/problem-lists/${id}/items/${problemId}`, { method: 'DELETE' }),
  reorder: (id, problemIds) =>
    request(`/problem-lists/${id}/reorder`, { method: 'PUT', body: { problem_ids: problemIds } }),
}

export const wrongApi = {
  list: (params) => request('/wrong-questions', { params }),
  detail: (id) => request(`/wrong-questions/${id}/detail`),
  todayCount: () => request('/wrong-questions/today-count'),
  setErrorType: (id, errorType) =>
    request(`/wrong-questions/${id}`, { method: 'PATCH', body: { error_type: errorType } }),
  review: (id, reviewResult) =>
    request(`/wrong-questions/${id}/review`, { method: 'POST', body: { review_result: reviewResult } }),
  remove: (id) => request(`/wrong-questions/${id}`, { method: 'DELETE' }),
}

export const statsApi = {
  me: () => request('/stats/me'),
}

export const mockApi = {
  create: (examType) => request('/mock-exams', { method: 'POST', body: { exam_type: examType } }),
  list: () => request('/mock-exams'),
  detail: (id) => request(`/mock-exams/${id}`),
  submit: (id, answers) => request(`/mock-exams/${id}/submit`, { method: 'POST', body: { answers } }),
  result: (id) => request(`/mock-exams/${id}/result`),
}

export const healthApi = {
  check: () => request('/health'),
}

export const rankingApi = {
  list: (params) => request('/rankings', { params }),
}

export const contestApi = {
  list: (params) => request('/contests', { params }),
  detail: (id) => request(`/contests/${id}`),
  create: (body) => request('/contests', { method: 'POST', body }),
  update: (id, body) => request(`/contests/${id}`, { method: 'PUT', body }),
  remove: (id) => request(`/contests/${id}`, { method: 'DELETE' }),
  antiCheat: (id, body) => request(`/contests/${id}/anti-cheat`, { method: 'POST', body }),
  submit: (id, body) => request(`/contests/${id}/submit`, { method: 'POST', body }),
  judge: (id, body) => request(`/contests/${id}/judge`, { method: 'POST', body }),
}

export const discussionApi = {
  list: (params) => request('/discussions', { params }),
  detail: (id) => request(`/discussions/${id}`),
  create: (body) => request('/discussions', { method: 'POST', body }),
  comment: (id, body) => request(`/discussions/${id}/comments`, { method: 'POST', body }),
  report: (body) => request('/reports', { method: 'POST', body }),
  pin: (id, isPinned) =>
    request(`/admin/discussions/${id}/pin`, { method: 'POST', body: { is_pinned: isPinned } }),
  reports: () => request('/admin/reports'),
  resolveReport: (id) => request(`/admin/reports/${id}/resolve`, { method: 'POST' }),
}

export const appealApi = {
  create: (body) => request('/appeals', { method: 'POST', body }),
  mine: () => request('/appeals/me'),
  all: () => request('/admin/appeals'),
  review: (id, body) => request(`/admin/appeals/${id}/review`, { method: 'POST', body }),
}

export const adminUserApi = {
  list: (params) => request('/admin/users', { params }),
  unban: (id) => request(`/admin/users/${id}/unban`, { method: 'POST' }),
  toggleCreate: (id, enabled) =>
    request(`/admin/users/${id}/toggle-create-problem`, {
      method: 'POST',
      body: { can_create_problem: enabled },
    }),
  ban: (id) => request(`/admin/users/${id}/ban`, { method: 'POST' }),
  avatars: (status = 'pending') => request('/admin/avatars', { params: { status } }),
  reviewAvatar: (id, action) =>
    request(`/admin/avatars/${id}/review`, { method: 'POST', body: { action } }),
}

export const userApi = {
  changeName: (newUsername) =>
    request('/users/change-name', { method: 'PUT', body: { new_username: newUsername } }),
  updateAvatar: (avatarUrl) =>
    request('/users/avatar', { method: 'PUT', body: { avatar_url: avatarUrl } }),
}

export const auditApi = {
  list: () => request('/admin/audit-logs'),
}
