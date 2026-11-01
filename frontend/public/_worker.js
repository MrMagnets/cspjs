/**
 * Cloudflare Pages 高级模式 Worker：把 /api/* 反向代理到后端 Worker。
 *
 * 关键点：
 * 1. POST/PUT/PATCH 必须显式把 request body 读成 ArrayBuffer 再转发，
 *    不能依赖 `new Request(url, request)`（在 Workers 里容易丢 body / duplex 报错）。
 * 2. 保留原始 method、headers、query string，并补上 X-Forwarded-* 方便后端排查。
 * 3. OPTIONS 预检直接在这里返回，不再转发给 FastAPI。
 * 4. 如果上游返回非 JSON（例如 Cloudflare 的纯文本 "Bad Gateway"），
 *    统一转换成 JSON 错误，避免前端拿到 200 text/plain 后解析出 null。
 *
 * 后端地址可以用 Pages 环境变量 API_ORIGIN 覆盖，避免改代码。
 */
const DEFAULT_API_ORIGIN = 'https://cspjs-api-hf.3625099190.workers.dev'

function corsHeaders(request) {
  const origin = request.headers.get('Origin')
  const headers = {
    'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type, Accept',
    'Access-Control-Max-Age': '86400',
  }
  if (origin) {
    headers['Access-Control-Allow-Origin'] = origin
    headers['Vary'] = 'Origin'
  } else {
    headers['Access-Control-Allow-Origin'] = '*'
  }
  return headers
}

function jsonResponse(payload, status, request) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
      ...corsHeaders(request),
    },
  })
}

async function proxyToApi(request, env, url, apiOrigin) {
  const target = new URL(url.pathname + url.search, apiOrigin)

  const headers = new Headers(request.headers)
  // 这些头由 fetch 重新计算或不应透传
  headers.delete('host')
  headers.delete('content-length')
  headers.set('X-Forwarded-Host', url.host)
  headers.set('X-Forwarded-Proto', url.protocol.replace(':', ''))

  const init = {
    method: request.method,
    headers,
    redirect: 'manual',
  }

  // 关键：非 GET/HEAD 必须显式携带 body
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = await request.arrayBuffer()
  }

  let upstream
  try {
    upstream = await fetch(new Request(target.toString(), init))
  } catch (error) {
    return jsonResponse(
      { detail: 'API 网关错误：无法连接后端 Worker', error: String(error) },
      502,
      request,
    )
  }

  const contentType = upstream.headers.get('Content-Type') || ''
  const isJson = contentType.includes('application/json')
  const noBody = upstream.status === 204 || upstream.status === 304

  // 上游返回非 JSON（Bad Gateway / Method Not Allowed 纯文本等）时，
  // 转成标准 JSON，避免前端 res.json() 得到 null。
  if (!noBody && !isJson) {
    const text = await upstream.text()
    return jsonResponse(
      {
        detail: '上游 API 返回了非 JSON 响应',
        upstream_status: upstream.status,
        upstream_content_type: contentType || null,
        upstream_body: text.slice(0, 500),
      },
      upstream.status === 200 ? 502 : upstream.status,
      request,
    )
  }

  const responseHeaders = new Headers(upstream.headers)
  for (const [key, value] of Object.entries(corsHeaders(request))) {
    responseHeaders.set(key, value)
  }

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  })
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url)

    if (!url.pathname.startsWith('/api/')) {
      return env.ASSETS.fetch(request)
    }

    // 预检直接返回，不转发
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders(request) })
    }

    const apiOrigin = (env.API_ORIGIN || DEFAULT_API_ORIGIN).replace(/\/+$/, '')
    return proxyToApi(request, env, url, apiOrigin)
  },
}
