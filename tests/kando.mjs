#!/usr/bin/env node
// Use exact pinned upstream schemas/selection method, rather than another schema.
// Args: rendered tests/kando.nix JSON, general schema TS, menu schema TS,
//       menu-window.ts, and the upstream-lockfile integrity-checked zod module.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
const [fixture, general, menus, window, zod, patched, typescript] = process.argv.slice(2);
const data = JSON.parse(fs.readFileSync(fixture, 'utf8'));
const z = await import(pathToFileURL(zod));
function schema(path, symbol) {
  const code = fs.readFileSync(path, 'utf8')
    .replace(/^import .*;$/gm, '').replace(/^export type .*;$/gm, '')
    .replaceAll('export const ', 'const ');
  return new Function('z', 'version', `${code}\nreturn ${symbol};`)(z, '2.3.0');
}
const parsed = schema(menus, 'MENU_SETTINGS_SCHEMA_V1').parse(data.menus);
schema(general, 'GENERAL_SETTINGS_SCHEMA_V1').parse(data.settings);
assert.equal(parsed.version, '2.3.0');
assert.equal(data.settings.version, '2.3.0');
// Extract the real complete method, deleting only its TypeScript annotations.
const source = fs.readFileSync(window, 'utf8');
const body = source.slice(source.indexOf('  public chooseMenu('), source.indexOf('\n  }', source.indexOf('  public chooseMenu(')) + 4)
  .replace('public chooseMenu(request: ShowMenuRequest, info: WMInfo)', 'chooseMenu(request, info)')
  .replace('const scores: number[]', 'const scores')
  .replace('(condition: string, value: string)', '(condition, value)')
  .replace('const bestMenus: DeepReadonly<Menu>[]', 'const bestMenus');
const choose = new Function(`return ({${body}}).chooseMenu;`)();
const context = {kando: {
  getMenuSettings: () => ({get: () => parsed.menus}),
  getGeneralSettings: () => ({get: () => 'first'}),
  getBackend: () => ({getBackendInfo: () => ({supportsShortcuts: false})}),
}};
for (const [appName, expected] of [['firefox','Firefox'], ['Firefox','Firefox'], ['codex-desktop','ChatGPT'], ['codex-desktop-sandboxed','ChatGPT'], ['foot','Context'], ['firefox-extra','Context'], ['codex-desktop-extra','Context']]) {
  assert.equal(choose.call(context, {trigger:'contextual-menu'}, {appName, windowName:'', pointer:{x:0,y:0}}).root.name, expected);
}
const global = choose.call(context, {trigger:'global-menu'}, {appName:'firefox'});
assert.equal(global.root.children.length, 6);
for (const item of global.root.children) {
  assert.equal(item.data.isolated, true, 'launched apps must escape Kando service lifecycle');
  assert.ok(item.data.command.includes('XDG_CONFIG_HOME=/home/fixture/.config '));
}
const firefox = parsed.menus.find(menu => menu.root.name === 'Firefox');
assert.equal(firefox.root.children.find(i => i.name === 'Back').angle, 270);
assert.equal(firefox.root.children.find(i => i.name === 'Forward').angle, 90);
for (const menu of parsed.menus) {
  assert.ok(menu.root.children.every(item => item.iconTheme === 'material-symbols-rounded'));
  const angles = menu.root.children.map(item => item.angle);
  assert.deepEqual(angles, [...angles].sort((a,b)=>a-b));
}
assert.ok(data.wrapper.includes('--set XDG_CONFIG_HOME'));
assert.ok(data.wrapper.includes('--ozone-platform=wayland'));
assert.ok(data.wrapper.includes('Exec=$out/bin/kando'));
assert.ok(data.service.Service.ExecStart.endsWith('/bin/kando'));
assert.equal(data.service.Service.ExecStartPre.length, 2);
assert.ok(data.lua.includes('hl.bind("mouse:276", hl.dsp.global("menu.kando.Kando:global-menu"))'));
assert.ok(data.lua.includes('hl.bind("mouse:275", hl.dsp.global("menu.kando.Kando:contextual-menu"))'));
assert.equal(data.settings.warpMouse, false);
assert.ok(data.wrapper.includes('--set KANDO_HOLD_SHORTCUT_IDS global-menu,contextual-menu'));
for (const name of ['Firefox', 'ChatGPT']) {
  const children = parsed.menus.find(m => m.root.name === name).root.children;
  assert.equal(children.find(i => i.name === 'Fullscreen').angle, 0);
  assert.equal(children.find(i => i.name === 'Fullscreen').data.hotkey, 'F11');
  assert.equal(new Set(children.map(i => i.angle)).size, children.length);
  assert.ok(children.find(i => i.name === 'Copy'));
}
assert.ok(global.root.children.find(i=>i.name==='Next workspace').data.command.includes("hl.dsp.focus({workspace='+1'})"));
console.log('Kando: exact upstream schemas, real context selection, angle mappings and launch ownership passed');

// Execute patched upstream TypeScript directly. No Electron or input injection.
const ts = (await import(pathToFileURL(typescript))).default;
function compile(code, deps = {}) {
  const output = ts.transpileModule(code, {compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
  }}).outputText;
  const module = {exports: {}};
  new Function('require', 'exports', 'module', output)(
    name => { assert.ok(name in deps, `Unexpected import ${name}`); return deps[name]; },
    module.exports, module);
  return module.exports;
}
const read = path => fs.readFileSync(`${patched}/${path}`, 'utf8');
const math = compile(read('src/common/math/index.ts'), {'.': {}});
const common = {SelectionSource: {eGesture: 0, eClick: 1}};
const input = compile(read('src/menu-renderer/input-methods/input-method.ts'),
  {'../../common': common});
const {EventEmitter} = await import('node:events');
const {GestureDetector} = compile(read('src/menu-renderer/input-methods/gesture-detector.ts'), {
  events: {EventEmitter}, '../../common/math': math, '../../common': common,
});
const {PointerInput} = compile(read('src/menu-renderer/input-methods/pointer-input.ts'), {
  '../../common/math': math, '../../common': common,
  './input-method': input, './gesture-detector': {GestureDetector},
});
globalThis.MouseEvent = class {
  constructor(x, y) {this.clientX = x; this.clientY = y;}
  preventDefault() {} stopPropagation() {}
};
globalThis.requestAnimationFrame = callback => callback();
globalThis.TouchEvent = class {};
const pointer = new PointerInput();
let selects = 0, cancels = 0;
pointer.onSelection(() => selects++);
pointer.onCloseMenu(() => cancels++);
pointer.onShowMenu(false, true);
pointer.setCurrentCenter({x: 100, y: 100}, 50);
assert.equal(pointer.buttonState, input.ButtonState.eDragged);
pointer.releaseShortcut();
assert.equal(cancels, 1, 'release in center cancels');
assert.equal(selects, 0);
pointer.onShowMenu(false, true);
pointer.setCurrentCenter({x: 100, y: 100}, 50);
pointer.update({x: 100, y: 40}, {x: 100, y: 100}, input.ButtonState.eDragged);
pointer.releaseShortcut();
assert.equal(selects, 1, 'release outside upstream center radius selects');
assert.equal(pointer.buttonState, input.ButtonState.eReleased);
pointer.releaseShortcut();
assert.equal(selects, 1, 'duplicate release cannot select twice');
pointer.onShowMenu(false);
assert.equal(pointer.buttonState, input.ButtonState.eReleased, 'ordinary menu stays ordinary');

// Linux actions use mapKeys, rather than Electron accelerator aliases.
const keyCodes = compile(read('src/common/key-codes.ts'), {'.': {}});
for (const menu of parsed.menus) {
  for (const item of menu.root.children.filter(i => i.type === 'hotkey')) {
    assert.ok(keyCodes.mapKeys(item.data.hotkey.split('+').map(name => ({name})), 'linux')
      .every(Number.isInteger));
  }
}
assert.throws(() => keyCodes.mapKeys([{name:'Alt'}], 'linux'), /Unknown key/);

// Test the actual app listener with deferred show completion and distinct IDs.
const appSource = read('src/main/app.ts');
const begin = appSource.indexOf('  private shortcutHold:');
const end = appSource.indexOf("    this.backend.on('shortcutPressed'", begin);
const {HoldApp} = compile(`export class HoldApp {${appSource.slice(begin, end)} } }`);
const app = new HoldApp();
app.backend = new EventEmitter();
const messages = [];
app.menuWindow = {webContents: {send: message => messages.push(message)}};
let resolveShow;
app.showMenu = request => {
  app.menuWindow.lastRequest = request;
  return new Promise(resolve => {resolveShow = resolve;});
};
await app.init();
app.backend.emit('shortcutHold', 'contextual-menu', true);
app.backend.emit('shortcutHold', 'global-menu', false);
assert.equal(messages.length, 0, 'irrelevant release ignored');
app.backend.emit('shortcutHold', 'contextual-menu', false);
app.backend.emit('shortcutHold', 'contextual-menu', false);
assert.equal(messages.length, 0, 'release waits for menu readiness');
resolveShow();
await Promise.resolve(); await Promise.resolve();
assert.deepEqual(messages, ['menu-window.release-shortcut'], 'early release delivered once');
assert.equal(app.shortcutHold, null);
app.backend.emit('shortcutHold', 'global-menu', true);
const firstHold = app.shortcutHold;
app.backend.emit('shortcutHold', 'contextual-menu', true);
assert.equal(app.shortcutHold, firstHold, 'second held button cannot steal lifetime');
app.backend.emit('shortcutHold', 'global-menu', false);
app.shortcutHold = null; // actual onCancel/onSelect callbacks clear ownership
resolveShow();
await Promise.resolve(); await Promise.resolve();
assert.equal(messages.length, 1, 'cancelled lifetime ignores deferred release');
app.backend.emit('shortcutHold', 'contextual-menu', true);
app.backend.emit('shortcutHold', 'contextual-menu', false);
resolveShow();
await Promise.resolve(); await Promise.resolve();
assert.equal(messages.length, 2, 'next contextual hold works after cancellation');
app.showMenu = () => Promise.reject(new Error('fixture readiness failure'));
const logError = console.error;
let failureReported = false;
console.error = () => {failureReported = true;};
app.backend.emit('shortcutHold', 'global-menu', true);
await app.shortcutHold.ready;
console.error = logError;
assert.equal(app.shortcutHold, null, 'readiness failure clears hold ownership');
assert.equal(failureReported, true);
assert.ok(appSource.includes('if (!request.shortcutHold) this.shortcutHold = null;'));
assert.ok(read('src/main/backends/linux/portals/global-shortcuts.ts').includes("this.interface.on('Deactivated'"));
assert.ok(read('src/main/backends/linux/hyprland/backend.ts').includes("this.emit('shortcutHold', shortcutID, false)"));
assert.ok(read('src/menu-renderer/index.ts').includes('if (menuShown === showing) menu.releaseShortcut();'));
console.log('Kando: Linux backend key mapping and exact patched hold/early-release/cancel lifecycle passed');

// Run the real renderer subscription block to verify release during icon loading.
const indexSource = read('src/menu-renderer/index.ts');
const renderBegin = indexSource.indexOf('  let menuShown =');
const renderEnd = indexSource.indexOf('  // Hide the menu', renderBegin);
const rendererListeners = {};
const renderEvents = [];
let resolveIcons;
const rendererDependencies = {
  window: {menuAPI: {
    onShowMenu: cb => {rendererListeners.show = cb;},
    onReleaseShortcut: cb => {rendererListeners.release = cb;},
  }},
  menu: {show: root => renderEvents.push(`show:${root}`), releaseShortcut: () => renderEvents.push('release')},
  settingsButton: {show() {}},
  IconThemeRegistry: {getInstance: () => ({reloadSystemIcons: () => new Promise(resolve => {resolveIcons = resolve;})})},
};
const rendererOutput = ts.transpileModule(indexSource.slice(renderBegin, renderEnd), {
  compilerOptions: {target: ts.ScriptTarget.ES2022},
}).outputText;
new Function(...Object.keys(rendererDependencies), rendererOutput)(...Object.values(rendererDependencies));
rendererListeners.show('context', {systemIconsChanged: true});
rendererListeners.release();
assert.deepEqual(renderEvents, []);
resolveIcons();
await Promise.resolve(); await Promise.resolve(); await Promise.resolve();
assert.deepEqual(renderEvents, ['show:context', 'release']);
console.log('Kando: renderer defers early release behind asynchronous icon readiness');

class FakeWLRBackend extends EventEmitter {
  isShortcutInhibited(id) {return id === 'inhibited';}
  onShortcutPressed(id) {this.emit('shortcutPressed', id);}
}
class FakeGlobalShortcuts extends EventEmitter {}
const holdEnv = process.env.KANDO_HOLD_SHORTCUT_IDS;
process.env.KANDO_HOLD_SHORTCUT_IDS = 'global-menu,contextual-menu,inhibited';
const {HyprBackend} = compile(read('src/main/backends/linux/hyprland/backend.ts'), {
  'i18next': {t: key => key}, 'child_process': {exec() {throw new Error('Unexpected compositor call');}},
  'lodash': {}, '../wlroots/backend': {WLRBackend: FakeWLRBackend},
  '../portals/global-shortcuts': {GlobalShortcuts: FakeGlobalShortcuts}, 'electron': {screen: {}},
});
const backend = new HyprBackend();
if (holdEnv === undefined) delete process.env.KANDO_HOLD_SHORTCUT_IDS;
else process.env.KANDO_HOLD_SHORTCUT_IDS = holdEnv;
const backendEdges = [];
backend.on('shortcutHold', (id, pressed) => backendEdges.push([id, pressed]));
backend.on('shortcutPressed', id => backendEdges.push([id, 'ordinary']));
await backend.init();
backend.globalShortcuts.emit('ShortcutActivated', 'global-menu');
backend.globalShortcuts.emit('ShortcutDeactivated', 'global-menu');
backend.globalShortcuts.emit('ShortcutActivated', 'keyboard-menu');
backend.globalShortcuts.emit('ShortcutDeactivated', 'keyboard-menu');
backend.globalShortcuts.emit('ShortcutActivated', 'inhibited');
assert.deepEqual(backendEdges, [
  ['global-menu', true], ['global-menu', false], ['keyboard-menu', 'ordinary'],
]);
console.log('Kando: exact Hyprland backend preserves portal edges and ordinary/inhibited triggers');

// Execute upstream motion and menu selection together, with one sample per frame.
// The default theme's child center is 100px away: stopping there must execute
// immediately, without an extra movement, click, pause, or button release.
assert.equal(data.settings.fixedStrokeLength, 50);
assert.equal(data.settings.hoverModeNeedsConfirmation, false);
assert.ok(parsed.menus.every(m => m.hoverMode === true));
const menuSource = read('src/menu-renderer/menu.ts');
const selectionBegin = menuSource.indexOf('    const onSelection =');
const selectionEnd = menuSource.indexOf('    this.pointerInput.onCloseMenu', selectionBegin);
const selectionCode = ts.transpileModule(menuSource.slice(selectionBegin, selectionEnd), {
  compilerOptions: {target: ts.ScriptTarget.ES2022},
}).outputText;
const realMenuSelection = new Function('SelectionType', `${selectionCode}\nreturn onSelection;`);
function straightHold(hoverMode, direction = {x:0, y:-1}) {
  const pointer = new PointerInput();
  const selections = [];
  const root = {type:'submenu'};
  const leaf = {type:'hotkey'};
  const menu = {
    container: {classList: {contains: () => false}},
    root, selectionChain: [root], hoveredItem: root,
    settings: {centerDeadZone:50}, latestInput: {},
    selectItem: item => selections.push(item), cancel: () => selections.push('cancel'),
  };
  pointer.onUpdateState(state => {
    menu.latestInput = state;
    menu.hoveredItem = state.distance > 50 ? leaf : root;
  });
  pointer.onSelection(realMenuSelection.call(menu, input.SelectionType));
  pointer.enableHoverMode = hoverMode;
  pointer.hoverModeNeedsConfirmation = data.settings.hoverModeNeedsConfirmation;
  pointer.gestureDetector.fixedStrokeLength = data.settings.fixedStrokeLength;
  pointer.gestureDetector.centerDeadZone = 50;
  pointer.onShowMenu(false, true);
  pointer.setCurrentCenter({x:100, y:100}, 50);
  let frame;
  globalThis.requestAnimationFrame = callback => {frame = callback;};
  const move = distance => {
    pointer.onMotionEvent(new MouseEvent(100 + direction.x * distance, 100 + direction.y * distance));
    if (frame) {const done = frame; frame = null; done();}
  };
  move(0); move(1); // Real two-event startup filter, no fixture bypass.
  move(50); move(99);
  assert.deepEqual(selections, [], 'dead zone and inner stroke never execute');
  move(100); // First and final crossing sample; no follow-up motion.
  assert.equal(pointer.shortcutHeld, true, 'execution precedes physical release');
  assert.deepEqual(selections, hoverMode ? [leaf] : [], 'real menu callback selects leaf only in hover mode');
  pointer.gestureDetector.reset();
}
straightHold(false);
for (const direction of [{x:0,y:-1}, {x:1,y:0}, {x:0,y:1}, {x:-1,y:0}]) {
  straightHold(true, direction);
}
globalThis.requestAnimationFrame = callback => callback();
console.log('Kando: real menu executes leaf on first held 100px crossing in every direction');
