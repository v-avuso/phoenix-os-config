local root = assert(arg[1])
local combat, loaded, calls = false, false, {}
local frames = {}
local function frame()
    local f = {events = {}, bindings = {}, attrs = {}, refs = {}}
    function f:RegisterEvent(e) self.events[e] = true end
    function f:SetScript(e, fn) self[e] = fn end
    function f:SetAttribute(k, v) self.attrs[k] = v end
    function f:GetAttribute(k) return self.attrs[k] end
    function f:SetFrameRef(k, v) self.refs[k] = v end
    function f:GetFrameRef(k) return self.refs[k] end
    function f:ClearBindings() self.bindings = {} end
    function f:CallMethod(name) self[name](self) end
    frames[#frames + 1] = f
    return f
end
CreateFrame = frame
UIParent = {}
InCombatLockdown = function() return combat end
C_AddOns = { IsAddOnLoaded = function(name) return name == 'ElvUI' or (name == 'HoldToCastFix' and loaded) end }
local bars = { HandleBinds = function() end }
ElvUI = {{ private = { actionbar = { enable = true } }, db = {actionbar = {bar1 = {paging = {DRUID = '[bonusbar:1] 7; [mod:shift] 4;'}}}}, myclass = 'DRUID', GetModule = function() return bars end }}
GetBindingKey = function(command)
    if command == 'ACTIONBUTTON1' then return '1' end
    if command == 'MULTIACTIONBAR3BUTTON1' then return 'SHIFT-1' end
end
SetOverrideBinding = function(owner, _, key, command) assert(not combat); owner.bindings[key] = command end
ClearOverrideBindings = function(owner) assert(not combat); owner.bindings = {} end
RegisterStateDriver = function(f, _, conditions) assert(not combat); f.conditions = conditions; calls.register = (calls.register or 0) + 1 end
UnregisterStateDriver = function(f) assert(not combat); f.conditions = nil end
hooksecurefunc = function(_, _, fn) calls.hook = fn end
ActionBarController = { registered = {}, RegisterEvent = function(self, e) self.registered[e] = true end, UnregisterEvent = function(self, e) self.registered[e] = nil end, IsEventRegistered = function(self, e) return self.registered[e] end }
local toolkit = { Options = {} }
function toolkit:RegisterFeature(f) self.feature = f end
function toolkit:RefreshFeatures() end
toolkit.Options.Checkbox = function(_, _, _, _, _, fn) calls.click = fn; return {SetChecked = function() end} end
assert(loadfile(root .. '/features/elvui-hold-to-cast/Feature.lua'))('PhoenixWoWToolkit', toolkit)
local feature = toolkit.feature
feature.settings = {enabled = true}
assert(feature:GetAvailability())
feature:Enable()
assert(frames[1].bindings['1'] == 'ACTIONBUTTON1')
assert(frames[2].bindings['SHIFT-1'] == 'MULTIACTIONBAR3BUTTON1')
assert(frames[3].conditions:find('%[mod:shift%] %-4'))
assert(ActionBarController.registered.UPDATE_BONUS_ACTIONBAR)
local function securePage(page)
    local state = frames[3]
    state.attrs['state-pwtpage'] = page
    local env = setmetatable({self = state, newstate = page}, {__index = _G})
    assert(load(state.attrs['_onstate-pwtpage'], 'secure state', 't', env))()
end
combat = true
securePage('0')
assert(next(frames[1].bindings) == nil and frames[2].bindings['SHIFT-1'])
securePage('1')
assert(feature.pending and next(frames[1].bindings) == nil)
combat = false
frames[4].OnEvent(frames[4], 'PLAYER_REGEN_ENABLED')
assert(frames[1].bindings['1'] == 'ACTIONBUTTON1')
combat = true
feature:Disable()
assert(frames[1].bindings['1'], 'bindings must not be mutated in combat')
combat = false
frames[4].OnEvent(frames[4], 'PLAYER_REGEN_ENABLED')
assert(next(frames[1].bindings) == nil and next(frames[2].bindings) == nil)
assert(not ActionBarController.registered.UPDATE_BONUS_ACTIONBAR)
calls.hook()
assert(next(frames[1].bindings) == nil, 'disabled hook must not reinstall bindings')
loaded = true
assert(not feature:GetAvailability(), 'avoid competing with the standalone fix')
loaded = false
ElvUI[1].private.actionbar.enable = false
assert(not feature:GetAvailability(), 'avoid changing bindings when ElvUI bars are disabled')
print('ElvUI hold-to-cast: bindings, paging, combat deferral, restoration and conflict gate passed')
