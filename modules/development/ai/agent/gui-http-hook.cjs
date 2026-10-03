// Loaded only by the immutable Sandboxed desktop bootstrap. Native is untouched.
// Electron/main owns this connection: no renderer sees gateway credentials.
const http = require('node:http');
const electron = require('electron');
const socketPath = process.env.PHOENIX_GUI_HTTP_SOCKET;
if (!socketPath) throw new Error('Sandbox desktop HTTP socket is required');
const allowed = url => url.protocol === 'https:' && url.host === 'chatgpt.com'
  && !url.username && !url.password
  && (url.pathname.startsWith('/backend-api/') || url.pathname.startsWith('/api/codex/'));
const readBody = async request => {
  if (!request.body) return Buffer.alloc(0);
  const reader = request.body.getReader();
  const chunks = [];
  let length = 0;
  const cancel = () => { reader.cancel(request.signal.reason).catch(() => {}); };
  request.signal.addEventListener('abort', cancel, { once: true });
  try {
    while (true) {
      request.signal.throwIfAborted();
      const next = await reader.read();
      request.signal.throwIfAborted();
      if (next.done) break;
      length += next.value.byteLength;
      if (length > 16 * 1024 * 1024) {
        await reader.cancel();
        throw new Error('Sandbox desktop request too large');
      }
      chunks.push(Buffer.from(next.value));
    }
    return Buffer.concat(chunks, length);
  } finally { request.signal.removeEventListener('abort', cancel); }
};
const mediate = async (input, init) => {
  const request = new Request(input, init);
  const url = new URL(request.url);
  if (!allowed(url)) throw new Error('Authenticated request outside sandbox desktop backend');
  if (request.signal.aborted) throw request.signal.reason;
  const body = await readBody(request);
  const headers = Object.fromEntries(request.headers);
  // Never pass app-server's handle, any alternate bearer, cookie or host header.
  for (const key of Object.keys(headers)) {
    if (['authorization', 'cookie', 'host', 'connection', 'content-length', 'transfer-encoding', 'chatgpt-account-id'].includes(key.toLowerCase())) delete headers[key];
  }
  headers['content-length'] = String(body.length);
  return await new Promise((resolve, reject) => {
    const connection = http.request({ socketPath, path: request.url, method: request.method, headers }, response => {
      // The async iterator preserves backpressure and SSE timing. A cancel flag
      // also protects against an already pending read resolving after cancel.
      let cancelled = false;
      const iterator = response[Symbol.asyncIterator]();
      const stream = new ReadableStream({
        async pull(controller) {
          try {
            const next = await iterator.next();
            if (cancelled) return;
            if (next.done) controller.close(); else controller.enqueue(next.value);
          } catch (error) { if (!cancelled) controller.error(error); }
        },
        cancel() { cancelled = true; response.destroy(); }
      });
      const status = response.statusCode;
      const responseBody = request.method === 'HEAD' || [204, 205, 304].includes(status) ? null : stream;
      const result = new Response(responseBody, { status, headers: response.headers });
      Object.defineProperty(result, 'url', { value: request.url });
      resolve(result);
    });
    const abort = () => connection.destroy(new Error('Sandbox desktop request cancelled'));
    request.signal.addEventListener('abort', abort, { once: true });
    connection.on('error', reject);
    connection.on('close', () => request.signal.removeEventListener('abort', abort));
    if (request.signal.aborted) abort(); else connection.end(body);
  });
};
const wrap = original => (input, init) => {
  const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined));
  // Every authenticated request is fail-closed, including unrecognised hosts.
  // Public asset requests retain the upstream fetch implementation.
  return headers.has('authorization') ? mediate(input, init) : original(input, init);
};
electron.net.fetch = wrap(electron.net.fetch.bind(electron.net));
globalThis.fetch = wrap(globalThis.fetch.bind(globalThis));
