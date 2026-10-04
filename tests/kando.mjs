#!/usr/bin/env node
// Use exact pinned upstream schemas/selection method, rather than another schema.
// Args: rendered tests/kando.nix JSON, general schema TS, menu schema TS,
//       menu-window.ts, and the upstream-lockfile integrity-checked zod module.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
const [fixture, general, menus, window, zod] = process.argv.slice(2);
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
for (const [appName, expected] of [['firefox','Firefox'], ['Firefox','Firefox'], ['codex-desktop','Codex'], ['codex-desktop-sandboxed','Codex'], ['foot','Context'], ['firefox-extra','Context'], ['codex-desktop-extra','Context']]) {
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
assert.ok(data.lua.includes('mouse:275') && data.lua.includes('mouse:276'));
assert.ok(global.root.children.find(i=>i.name==='Next workspace').data.command.includes("hl.dsp.focus({workspace='+1'})"));
console.log('Kando: exact upstream schemas, real context selection, angle mappings and launch ownership passed');
