# Phoenix WoW Toolkit

The extraction repository name is `phoenix-wow-toolkit`. The installed add-on folder
and TOC retain `PhoenixWoWToolkit`; source feature directories use lowercase kebab-case.

## Intentions

Small independently configurable features share initialization, account-wide
preferences and one native Settings page. Keep implementation, research, tests and
manual acceptance with their feature so this directory can become its own repository.
Preserve other add-ons, user profiles, bindings and secure input authority.

## Install and use

Copy or symlink this directory as `Interface/AddOns/PhoenixWoWToolkit`. `/pwt` opens
**Options → AddOns → Phoenix WoW Toolkit**. **General** contains tracker/OPie
options; **Tooltip** contains appearance, preview and comparison options; **Combat**
contains configurable combat indicators and class/spec presets. Preferences live in WoW-owned
`PhoenixWoWToolkitDB.features.<id>`; removing the add-on does not delete them.

Retail loads the features listed below. Forever loads the shared core and Settings
foundation only; its pages are empty until features are individually checked and added.
The ElvUI hold-to-cast workaround is not implemented.

The PhoenixOS deployment adapter lives outside this directory. It installs an
immutable Nix-store package, not a live checkout link. Editing this source therefore
requires a new deployment before `/reload` can load it. Reload generally reloads an
already-discovered add-on's Lua/TOC, but discovering a newly installed physical add-on
may require a client restart. A restart cannot expose an undeployed package.

## Features

- [Objective Tracker](features/objective-tracker/README.md): hide the global header and independently make section buttons invisible but clickable.

- [OPie Visual Delay](features/opie-visual-delay/README.md): experimental version-pinned visual delay, without intentional action latency. Local proof passes; client/combat acceptance remains.

- [Item Tooltips](features/universal-item-tooltips/README.md): choose the current UI with compact replacement deltas or Dialogue UI's actual renderer and overlapping 3D preview; preserves item information and annotations.

- [Comparison Cleanup](features/comparison-cleanup/README.md): independently hide the verified native equipped-item stat footer, with conservative fallbacks.

- [Combat Tracking](features/combat-tracking/README.md): configurable priority aura bars and combined DoT borders for any class, with Druid presets and ElvUI movers; client/combat acceptance remains.

## Architecture and extension

- `Core.lua`: versioned feature registration, saved preferences, lifecycle, dependency
  refresh and `/pwt`. It knows no OPie, tracker or tooltip implementation details.
- `Options.lua`: a scrollable native Settings canvas with General, Tooltip and Combat pages.
  Features may set `optionsTab = "Tooltip"` or `"Combat"`; omitted/unknown values use General.
  Each section has one heading; contributors on the same page share named sections. Checkbox descriptions use a
  smaller indented font beneath their labels. Compatibility/implementation essays
  belong in module docs, not in the player's settings flow.
- `features/<name>/`: the complete feature, including `Feature.lua`, helpers, README
  and `tests/`. List runtime Lua files in deterministic order in the TOC. Test files
  are never loaded by WoW. Tests requiring upstream code receive an explicit source path.
- `PhoenixWoWToolkit_Camelot.toc`: Forever's separate client manifest. Add only
  features verified for Forever; shared features may appear in both manifests.
- `tests/`: core tests and the standalone runner, independent of PhoenixOS tooling.

The bundle remains one physical add-on: this preserves the working SavedVariables
and install contract. Separate physical add-ons add TOCs, packaging and load-order
contracts without improving current behavior. Extraction later needs a small bootstrap
and a TOC dependency on the core, rather than a new settings framework.

The public registration object is `PhoenixWoWToolkit`, `apiVersion = 1`. An external
add-on declares `## Dependencies: PhoenixWoWToolkit`, checks the API version and calls
`PhoenixWoWToolkit:RegisterFeature(feature)` even after core initialization. Feature
IDs must be unique. A registration provides:

```lua
local Toolkit = PhoenixWoWToolkit
Toolkit:RegisterFeature({
    id = "uniqueFeature", section = "My feature",
    defaults = { enabled = true }, dependencies = {}, -- Optional add-on-load triggers.
    GetAvailability = function(self) return true end,
    Enable = function(self) -- Start reversible behavior; self.settings is initialized.
    end,
    Disable = function(self) -- Restore only owned changes; gate permanent hooks.
    end,
    RegisterSettings = function(self, panel, y)
        self.checkbox = Toolkit.Options.Checkbox(panel, "Enable my feature", y,
            self.settings, "enabled", function() Toolkit:RefreshFeatures() end,
            "A short player-facing description.")
        return y - 64
    end,
    RefreshSettings = function(self) self.checkbox:SetChecked(self.settings.enabled) end,
})
```

Keep dependencies and capability detection within the feature; `dependencies` merely
requests reevaluation when a named add-on loads. Preserve existing IDs/default keys
when moving files. Late registrations rebuild the canvas on its next refresh.
Independent distribution still requires choosing whether the core owns preferences
or the extracted add-on migrates them; no speculative migration system is included.

## Validation

```sh
python3 tests/run.py --lua /path/to/lua
# Optional local upstream sources, never downloaded by the tests:
python3 tests/run.py --lua /path/to/lua --opie /path/to/AddOns/OPie
```

Mocks check contracts, not WoW's GPU rendering, protected execution or taint. Each
feature's README owns its in-game acceptance checklist. Run those after approved
installation; never treat a passing local test as combat or desktop acceptance.
