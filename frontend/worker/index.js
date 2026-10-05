// Cloudflare Worker：静态资源走 ASSETS，/api/* 同源反代到本机后端隧道。
// 同源反代让前端无需 CORS，也不必在构建期写死后端地址。
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/api" || url.pathname.startsWith("/api/")) {
      const upstream = new URL(url.pathname + url.search, env.API_ORIGIN);
      return fetch(new Request(upstream, request));
    }
    return env.ASSETS.fetch(request);
  },
};
