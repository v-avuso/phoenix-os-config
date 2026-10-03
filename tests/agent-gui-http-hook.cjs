// Test the actual Electron hook using streams and a mocked Unix transport.
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { PassThrough } = require('node:stream');
const Module = require('node:module');
const http = require('node:http');
let options, connection, response, originalCalls = 0;
const electron = { net: { fetch: async () => { originalCalls++; return new Response('public'); } } };
const originalLoad = Module._load;
Module._load = function(name, ...args) { return name === 'electron' ? electron : originalLoad.call(this, name, ...args); };
http.request = (value, callback) => {
  options = value;
  connection = new EventEmitter();
  connection.end = () => {
    response = new PassThrough();
    response.statusCode = 200;
    response.headers = { 'content-type': 'text/event-stream' };
    response.on('close', () => { connection.closed = true; connection.emit('close'); });
    queueMicrotask(() => { callback(response); response.write('data: first\n\n'); });
  };
  connection.destroy = error => { connection.destroyed = true; response.destroy(error); connection.emit('error', error); };
  return connection;
};
process.env.PHOENIX_GUI_HTTP_SOCKET = '/fixture/fixed.sock';
require('../modules/development/ai/agent/gui-http-hook.cjs');
Module._load = originalLoad;
(async () => {
  const result = await electron.net.fetch('https://chatgpt.com/backend-api/wham/test', {
    headers: { Authorization: 'Bearer opaque-marker', Cookie: 'private-cookie', Host: 'evil.test', 'ChatGPT-Account-Id': 'evil-account' }
  });
  assert.equal(options.socketPath, '/fixture/fixed.sock');
  for (const key of ['authorization', 'cookie', 'host', 'chatgpt-account-id']) assert.equal(options.headers[key], undefined);
  const reader = result.body.getReader();
  assert.equal(new TextDecoder().decode((await reader.read()).value), 'data: first\n\n');
  response.end('data: second\n\n');
  assert.equal(new TextDecoder().decode((await reader.read()).value), 'data: second\n\n');
  assert.equal((await reader.read()).done, true);
  await assert.rejects(electron.net.fetch('https://evil.test/backend-api/test', { headers: { authorization: 'Bearer marker' } }), /outside sandbox/);
  assert.equal(originalCalls, 0);
  await electron.net.fetch('https://public.test/image.png');
  assert.equal(originalCalls, 1);
  const controller = new AbortController();
  const cancelled = await electron.net.fetch('https://chatgpt.com/backend-api/test', { headers: { authorization: 'Bearer marker' }, signal: controller.signal });
  const pending = cancelled.body.getReader();
  await pending.read();
  controller.abort();
  assert.equal(connection.destroyed, true);
  await assert.rejects(pending.read(), /cancelled/);
  const closed = await electron.net.fetch('https://chatgpt.com/backend-api/test', { headers: { authorization: 'Bearer marker' } });
  await closed.body.cancel();
  assert.equal(response.destroyed, true);
  console.log('agent-gui-http-hook: streaming, cancellation and authenticated request boundaries passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
