// Actual owner socket/dispatcher; Electron APIs are explicit stubs, no GUI.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const {EventEmitter, once} = require('node:events');
const {createControl} = require('../gui-control.cjs');
const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'phoenix-gui-control-'));
fs.chmodSync(directory, 0o700);
const token = 'a'.repeat(64);
let links = [], focused = 0, windows = 0, quits = 0, choice = 0, resolveDialog, dialogSignal;
const app = new EventEmitter();
app.whenReady = async () => {};
app.on('activate', () => { focused++; });
const secondInstance = (event, argv, cwd, additionalData) => {
  assert.deepEqual(event, {});
  assert.deepEqual(additionalData, {});
  assert.equal(cwd, process.cwd());
  assert.equal(argv[0], process.execPath);
  assert.equal(argv.length, 2);
  links.push(argv[1]);
};
app.on('second-instance', secondInstance);
app.quit = () => { quits++; }; // no forced process exit; upstream cancellation modeled below
const electron = {app, BrowserWindow:{getFocusedWindow:()=>null},
  Menu:{getApplicationMenu:()=>({getMenuItemById:id=>id==='phoenix-shared-new-window' ? {enabled:true,click:async()=>{windows++;}} : null})},
  dialog:{showMessageBox:async options=>{
    assert.deepEqual(options.buttons,['Keep current','Close and switch']);
    assert.equal(options.cancelId,0);
    dialogSignal=options.signal;
    if (choice==='pending') return new Promise(resolve=>{resolveDialog=resolve;});
    return {response:choice};
  }}};
const originalTimer = global.setTimeout;
// Exercise production absolute connection deadline cheaply; behavior unchanged.
global.setTimeout = (fn, ms, ...args) => originalTimer(fn, ms === 45000 ? 80 : ms, ...args);
const control = createControl(electron,{directory,token,variant:'native'});
const msg=(action,target='native')=>({token,action,target});
const request=body=>new Promise((resolve,reject)=>{
  const socket=net.connect(control.socketPath,()=>socket.end(body));
  let data=''; socket.on('data',chunk=>{data+=chunk;});
  socket.on('error',error=>{ if (error.code!=='ECONNRESET') reject(error); });socket.on('close',()=>resolve(data ? JSON.parse(data) : null));
});
(async()=>{
 try {
  await once(control.server,'listening');
  assert.equal(fs.statSync(control.socketPath).mode & 0o777,0o600);
  assert.deepEqual(await request(JSON.stringify({...msg('activate'),token:'b'.repeat(64)})+'\n'),{status:'denied'});
  assert.deepEqual(await request(JSON.stringify({...msg('activate'),url:'https://example.com'})+'\n'),{status:'denied'});
  assert.equal(await request('x'.repeat(32769)),null);
  assert.deepEqual(await control.handle(msg('activate')),{status:'handled'});
  assert.deepEqual(await control.handle(msg('new-window')),{status:'handled'});
  assert.equal(focused,1);assert.equal(windows,1);
  for (const uri of ['codex://thread/fixture', 'codex-browser-sidebar://oauth/callback?state='+'a'.repeat(1024)]) {
    assert.deepEqual(await request(JSON.stringify({...msg('open-link'), uri})+'\n'),{status:'handled'});
  }
  assert.equal(links.length,2);
  app.removeListener('second-instance', secondInstance);
  assert.deepEqual(await control.handle({...msg('open-link'),uri:'codex://thread/fixture'}),{status:'unavailable'});
  app.on('second-instance', secondInstance);
  for (const uri of ['https://example.com', 'file:///tmp/file', 'codex://thread/ bad', 'codex://[', 'codex://'+'a'.repeat(4097), 'codex://user:pass@thread/fixture', 7]) {
    assert.deepEqual(await control.handle({...msg('open-link'),uri}),{status:'denied'});
  }
  assert.deepEqual(await control.handle({...msg('open-link','sandbox'),uri:'codex://thread/fixture'}),{status:'denied'});
  assert.deepEqual(await control.handle(msg('switch','sandbox')),{status:'kept'});
  assert.equal(quits,0);
  choice='pending'; const abort=new AbortController();
  const pending=control.handle(msg('switch','sandbox'),abort.signal);
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(await control.handle(msg('switch','sandbox')),{status:'busy'});
  assert.deepEqual(await control.handle(msg('new-window')),{status:'busy'});
  assert.deepEqual(await control.handle({...msg('open-link'),uri:'codex://thread/fixture'}),{status:'busy'});
  abort.abort();assert.equal(dialogSignal.aborted,true);
  resolveDialog({response:1});assert.deepEqual(await pending,{status:'kept'});
  assert.equal(quits,0);
  // A partial request is terminated by an absolute deadline, not idle timeout.
  const slow=net.connect(control.socketPath);slow.on('error',()=>{});await once(slow,'connect');slow.write('{');
  const drip=setInterval(()=>slow.write(' '),10);
  await new Promise(resolve=>slow.once('close',resolve));clearInterval(drip);
  choice=1; assert.deepEqual(await control.handle(msg('switch','sandbox')),{status:'closing'});
  await new Promise(resolve=>setImmediate(resolve));assert.equal(quits,1);
  // App quit may be vetoed by upstream active work; no competing request bypasses it.
  assert.deepEqual(await control.handle(msg('switch','sandbox')),{status:'busy'});
  assert.deepEqual(await control.handle(msg('new-window')),{status:'busy'});
  assert.deepEqual(await control.handle({...msg('open-link'),uri:'codex://thread/fixture'}),{status:'busy'});
  console.log('agent-gui-control: fixed authenticated actions, cancellation, bounds and closing serialization passed (Electron stub)');
 } finally {
  control.close();
  if (control.server.listening) await once(control.server,'close');
  global.setTimeout=originalTimer;
  fs.rmSync(directory,{recursive:true,force:true});
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
