export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    if (url.pathname.startsWith('/api/')) {
      const targetUrl = 'https://cspjs-api-hf.3625099190.workers.dev' + url.pathname + url.search;
      const modifiedRequest = new Request(targetUrl, request);
      return fetch(modifiedRequest);
    }
    
    return env.ASSETS.fetch(request);
  }
};
