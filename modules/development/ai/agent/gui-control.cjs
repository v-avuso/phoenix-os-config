// Shared-mode owner only. Fixed window actions; no commands, URLs or credentials.
const net = require('node:net');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const MENU_ID = 'phoenix-shared-new-window';

function createControl(electron, {directory, token, variant}) {
  if (!path.isAbsolute(directory) || !/^[a-f0-9]{64}$/.test(token)
      || !['native', 'sandbox'].includes(variant)) throw new Error('Invalid shared GUI control configuration');
  const info = fs.lstatSync(directory);
  if (!info.isDirectory() || info.isSymbolicLink() || info.uid !== process.getuid()
      || (info.mode & 0o777) !== 0o700) throw new Error('Unsafe shared GUI control directory');
  const socketPath = path.join(directory, token.slice(0, 16) + '.sock');
  let pending = false;
  let connections = 0;
  async function handle(message, signal = new AbortController().signal) {
    if (!message || typeof message !== 'object' || Array.isArray(message)
        || Object.keys(message).sort().join(',') !== (message.action === 'open-link' ? 'action,target,token,uri' : 'action,target,token')
        || typeof message.token !== 'string' || !/^[a-f0-9]{64}$/.test(message.token)
        || !crypto.timingSafeEqual(Buffer.from(token), Buffer.from(message.token))
        || !['activate', 'new-window', 'open-link', 'switch'].includes(message.action)
        || !['native', 'sandbox'].includes(message.target)) return {status:'denied'};
    if (message.action === 'open-link') {
      if (typeof message.uri !== 'string' || Buffer.byteLength(message.uri) > 4096
          || !/^(codex|codex-browser-sidebar):\/\//.test(message.uri)
          || /[\s\x00-\x1f\x7f]/.test(message.uri)) return {status:'denied'};
      try { const uri = new URL(message.uri); if (uri.username || uri.password) return {status:'denied'}; } catch { return {status:'denied'}; }
    }
    if (pending) return {status:'busy'};
    if (message.action !== 'switch') {
      if (message.target !== variant) return {status:'denied'};
      if (message.action === 'open-link') {
        if (!electron.app.listenerCount('phoenix-shared-open-link')) return {status:'unavailable'};
        electron.app.emit('phoenix-shared-open-link', message.uri);
      } else if (message.action === 'activate') {
        electron.app.emit('activate'); // pinned handler shows/restores primary; no maximize
      } else {
        const item = electron.Menu.getApplicationMenu()?.getMenuItemById(MENU_ID);
        if (!item || item.enabled === false || typeof item.click !== 'function') return {status:'unavailable'};
        await item.click(item, electron.BrowserWindow.getFocusedWindow(), {});
      }
      return {status:'handled'};
    }
    if (message.target === variant) return {status:'denied'};
    pending = true;
    let closing = false;
    const abort = AbortSignal.any([signal, AbortSignal.timeout(40000)]);
    try {
      const options = {type:'question', title:'Switch ChatGPT variant',
        message:`${variant === 'native' ? 'Native' : 'Sandboxed'} ChatGPT is already open.`,
        detail:'Keep the current app, or close it normally and open the other variant. Active-work confirmation still applies. Running commands do not transfer.',
        buttons:['Keep current', 'Close and switch'], defaultId:0, cancelId:0, noLink:true, signal:abort};
      const parent = electron.BrowserWindow.getFocusedWindow();
      const choice = await (parent ? electron.dialog.showMessageBox(parent, options) : electron.dialog.showMessageBox(options));
      if (abort.aborted || choice.response !== 1) return {status:'kept'};
      // Do not mark quit approved, exit, destroy windows or bypass before-quit.
      closing = true;
      setImmediate(() => electron.app.quit());
      return {status:'closing'};
    } finally {
      // Upstream may cancel its own active-work confirmation. Conservatively
      // reject competing actions for one bounded grace period, never force exit.
      if (closing) setTimeout(() => { pending = false; }, 45000).unref();
      else pending = false;
    }
  }
  const sockets = new Set();
  const server = net.createServer({allowHalfOpen:true}, socket => {
    if (++connections > 4) { connections--; socket.destroy(); return; }
    sockets.add(socket);
    let buffer = Buffer.alloc(0), done = false;
    const abort = new AbortController();
    const deadline = setTimeout(() => { abort.abort(); socket.destroy(); }, 45000);
    deadline.unref();
    socket.setTimeout(60000, () => socket.destroy());
    socket.on('error', () => {});
    socket.on('close', () => { connections--; sockets.delete(socket); clearTimeout(deadline); abort.abort(); });
    socket.on('data', async chunk => {
      if (done) return socket.destroy();
      if (buffer.length + chunk.length > 32768) return socket.destroy();
      buffer = Buffer.concat([buffer, chunk]);
      const end = buffer.indexOf(10);
      if (end < 0) return;
      done = true;
      if (end !== buffer.length - 1) return socket.destroy();
      try {
        const result = await handle(JSON.parse(buffer.subarray(0, end).toString()), abort.signal);
        socket.end(JSON.stringify(result) + '\n');
      } catch { socket.end('{"status":"unavailable"}\n'); }
    });
  });
  server.on('error', () => {}); // control failure cannot close a working GUI
  electron.app.whenReady().then(() => server.listen(socketPath, () => fs.chmodSync(socketPath, 0o600)));
  const close = () => { for (const socket of sockets) socket.destroy(); server.close(); };
  electron.app.once('will-quit', close);
  return {handle, server, socketPath, close};
}
module.exports = {createControl};
if (process.env.PHOENIX_GUI_CONTROL_DIR) createControl(require('electron'), {
  directory:process.env.PHOENIX_GUI_CONTROL_DIR,
  token:process.env.PHOENIX_GUI_OWNER_TOKEN,
  variant:process.env.PHOENIX_GUI_VARIANT
});
