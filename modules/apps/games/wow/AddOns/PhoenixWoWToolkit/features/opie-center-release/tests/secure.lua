-- Run the actual patched restricted snippets under a small Lua frame simulation.
local file = assert(io.open(arg[1], "rb"))
local core = file:read("*a")
file:close()

local function snippet(name)
    local equals, start = core:match(name .. " = %[(=*)%[.-\0\n()")
    local finish = assert(core:find("]" .. equals .. "]", start, true))
    return assert(load(core:sub(start, finish - 1), name, "t", _ENV))
end

local function noop() end
local function wipe(t) for k in pairs(t) do t[k] = nil end return t end
newtable, _G.wipe, floor, abs = function() return {} end, wipe, math.floor, math.abs
ORL_OpenRing = snippet("ORL_OpenRing")
ORL_PrepareCollection = snippet("ORL_PrepareCollection")
ORL_GetCursorSlice = snippet("ORL_GetCursorSlice")
ORL_OnClick = snippet("ORL_OnClick")
ORL_PerformSliceAction = snippet("ORL_PerformSliceAction")
ORL_ResolveNestedSlice = snippet("ORL_ResolveNestedSlice")
ORL_SetMotionTrapArmed, ORL_UpdateInteractionBindings = noop, noop
local x, y, used, attributes = 0, 0, {}, {}
collections, ctokens, rotationMode, fcIgnore, rtokens = {}, {}, {}, {}, {}
emptyTable, visitedSlices, ORL_StoredCA = {}, {}, {}
pmode_RotationModeMap = {}
ALL_MODIFIERS, BUTTON_NAMEKEY_MAP, bindOverrides = "", {}, {}
ORL_RingData = {
    {action=10, name="trial", PrimaryAction="use", CenterAction=true, centerReleaseAction=99,
     scale=1, ofsx=0, ofsy=0, ofsDeg=0, RightAction="close"},
    {action=20, name="stock", PrimaryAction="use", CenterAction=true, OpprotunisticCA=true,
     scale=1, ofsx=0, ofsy=0, ofsDeg=0, RightAction="close"},
}
ORL_KnownCollections = {}
ORL_CloseActiveRing = function()
    activeRing, AIP_VirtualKey, AIP_Action = nil, nil, nil
end
ORL_CheckButtonBindings = noop
owner = {
    Run = function(_, fn, ...) return fn(...) end,
    RunFor = function(_, _, fn, ...) return fn(...) end,
    CallMethod = noop, SetScale=noop, SetPoint=noop, GetEffectiveScale=function() return 1 end,
    GetMousePosition = function() return 0.5+x/100, 0.5+y/100 end,
    SetAttribute = function(_, key, value) attributes[key] = value end,
}
self, sizeSq = owner, 10000
KR, RW = {RunAttribute=noop}, {GetAttribute=noop}
AB = {
    RunAttribute = function(_, key, id)
        if key == "UseAction" then
            used[#used+1] = id
            return "macro " .. id
        end
        assert(key == "GetCollectionContent")
        local rows = {}
        for i=1,8 do rows[i] = ("\n%d %d %d token%d_%d %d"):format(id, i, id+i, id, i, id == 10 and 7 or 5) end
        if id == 20 then rows[9] = "\n20 0 98 stockOnOpen 7" end
        return table.concat(rows)
    end,
}

local function open(key)
    AI_ClickStackIndex, AI_ClickStack = 0, {}
    ORL_OnClick(key, true)
    AIP_VirtualKey = key -- normally set by the binding-update snippet
end

open("r1")
assert(#openCollection == 8 and #used == 0)
assert(ORL_OnClick("r1", true) == false and #used == 0)
assert(ORL_PerformSliceAction(-2, false, false, "use-binding") == false and #used == 0)
ORL_OnClick("r1", false)
assert(used[1] == 99 and attributes.macrotext == "macro 99" and attributes.typerelease == "macro")
for i=1,8 do
    local angle = (i-1)*math.pi/4
    x, y = math.sin(angle)*50, math.cos(angle)*50
    open("r1")
    assert(#openCollection == 8 and #used == i)
    ORL_OnClick("r1", false)
    assert(used[i+1] == 10+i, ("direction %d dispatched %s"):format(i, tostring(used[i+1])))
end
x, y = 30, 0
open("r1")
ORL_OnClick("r1", false)
assert(#used == 9 and not activeRing)
x, y = 0, 0
open("r1")
ORL_OnClick("close", true)
ORL_OnClick("r1", false)
assert(#used == 9)
open("r2")
assert(used[10] == 98 and #openCollection == 8)
ORL_OnClick("r2", false)
assert(used[11] == 21 and #used == 11)
print("OPie secure snippet simulation passed")
