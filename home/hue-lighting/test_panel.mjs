import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('./panel.html', import.meta.url), 'utf8');
const elements = Object.fromEntries(['sync', 'source', 'screen', 'level', 'status', 'value'].map(id => [id, {
  events: {}, attributes: {},
  replaceChildren(...children) { this.children = children; },
  addEventListener(event, listener) { this.events[event] = listener; },
  setAttribute(name, value) { this.attributes[name] = value; },
}]));
let state = {enabled: true, ready: true, level: 0, message: 'Sync on', screens: [{name: 'DP-1', label: 'Display 1'}, {name: 'DP-3', label: 'Display 2'}], selected_screen: 'DP-3'};
const mutations = [];
const context = vm.createContext({
  document: {querySelector: selector => elements[selector.slice(1)], createElement: () => ({})},
  setInterval() {},
  async fetch(path, options) {
    if (options) {
      const body = JSON.parse(options.body);
      mutations.push({path, body});
      if (path === '/api/level') state.level = body.level;
      if (path === '/api/source') state.selected_screen = body.screen;
    }
    return {ok: true, async json() { return {...state}; }};
  },
});
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1], context);
await new Promise(resolve => setImmediate(resolve));
assert.equal(elements.level.value, 25, 'neutral must appear a quarter along the slider');
assert.equal(elements.screen.disabled, false);
assert.equal(elements.source.value, 'DP-3');
elements.source.value = 'DP-1';
await elements.source.events.change();
assert.deepEqual(mutations.pop(), {path: '/api/source', body: {screen: 'DP-1'}});
for (const [position, glow] of [[0, -1], [25, 0], [100, 1], [62.5, .5]]) {
  assert.equal(context.toGlow(position), glow);
  assert.equal(context.toPosition(glow), position);
}
for (let position = 1; position <= 100; position++) {
  assert.ok(context.toGlow(position) > context.toGlow(position - 1));
}
elements.level.value = '70';
elements.level.events.input();
assert.equal(elements.value.textContent, '0.60');
await elements.level.events.change();
assert.deepEqual(mutations.pop(), {path: '/api/level', body: {level: .6}});
await elements.screen.events.click();
assert.deepEqual(mutations.pop(), {path: '/api/screen', body: {}});
state.enabled = false;
state.ready = false;
await context.refresh();
assert.equal(elements.screen.disabled, true);
assert.equal(elements.level.disabled, true);
assert.equal(elements.source.disabled, false, 'display can be chosen before enabling sync');
console.log('Hue panel: slider mapping, saved gamma, screen action and disabled controls pass');
