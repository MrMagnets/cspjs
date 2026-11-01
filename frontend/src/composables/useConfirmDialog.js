/**
 * useConfirmDialog —— 一行代码呼出统一风格的确认 / 输入弹窗。
 *
 *   const { confirm, prompt } = useConfirmDialog()
 *   if (await confirm('确定删除该题单？')) { ... }
 *   const reason = await prompt('请填写驳回原因', { title: '驳回题目' })
 *
 * 所有弹窗由全局挂载的 ConfirmDialog.vue 渲染，禁止使用原生 alert/confirm/prompt
 * 与 ElMessageBox。
 */
import { reactive } from 'vue'

const DEFAULTS = {
  visible: false,
  kind: 'confirm', // confirm | prompt
  title: '确认操作',
  message: '',
  confirmText: '确定',
  cancelText: '取消',
  danger: false,
  placeholder: '',
  value: '',
  required: false,
  maxlength: 500,
  hint: '',
  width: '440px',
}

export const dialogState = reactive({ ...DEFAULTS })

let resolver = null

function open(options) {
  const opts = typeof options === 'string' ? { message: options } : { ...options }
  Object.assign(dialogState, DEFAULTS, opts, { visible: true })
  return new Promise((resolve) => {
    resolver = resolve
  })
}

export function settleDialog(result) {
  dialogState.visible = false
  const resolve = resolver
  resolver = null
  if (resolve) resolve(result)
}

export function useConfirmDialog() {
  /**
   * @param {string|object} options 提示文案，或 { title, message, danger, confirmText }
   * @returns {Promise<boolean>}
   */
  function confirm(options) {
    return open(typeof options === 'string' ? { message: options } : options).then((v) => v === true)
  }

  /**
   * @param {string|object} options 提示文案，或 { title, message, placeholder, required, value }
   * @returns {Promise<string|null>} 取消时返回 null
   */
  function prompt(options) {
    return open(
      typeof options === 'string' ? { kind: 'prompt', message: options } : { ...options, kind: 'prompt' },
    ).then((v) => (typeof v === 'string' && v.trim() ? v.trim() : null))
  }

  function alert(options) {
    return open(
      typeof options === 'string'
        ? { message: options, cancelText: '', confirmText: '知道了' }
        : { cancelText: '', confirmText: '知道了', ...options },
    )
  }

  return { state: dialogState, confirm, prompt, alert, settle: settleDialog }
}
