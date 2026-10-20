-- Apply trackpad choices saved by omarchy-trackpad-set (the Trackpad panel).
-- The settings file is plain key=value data, never Lua: only whitelisted keys
-- with validated values are applied, and the device name comes from USB
-- descriptors so it is passed to Hyprland as a string, not interpolated.

local paths = require("default.hypr.paths")

local booleans = {
  tap_to_click = true,
  natural_scroll = true,
  clickfinger_behavior = true,
  disable_while_typing = true,
}

local function read_settings()
  local settings = {}
  -- Hardcoded to ~/.local/state like omarchy-trackpad-set and the sibling
  -- toggle tools, which write there regardless of XDG_STATE_HOME.
  local file = io.open(paths.home .. "/.local/state/omarchy/toggles/hypr/trackpad-settings", "r")
  if not file then
    return settings
  end

  for line in file:lines() do
    local key, value = line:match("^([%w_]+)=(.*)$")
    if key then
      settings[key] = value
    end
  end

  file:close()
  return settings
end

local settings = read_settings()

local touchpad = {}
for key in pairs(booleans) do
  if settings[key] == "true" then
    touchpad[key] = true
  elseif settings[key] == "false" then
    touchpad[key] = false
  end
end

if next(touchpad) then
  hl.config({ input = { touchpad = touchpad } })
end

if settings.workspace_swipe == "true" then
  hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
end

local sensitivity = tonumber(settings.sensitivity)
local device = settings.device
if sensitivity and sensitivity >= -1 and sensitivity <= 1 and device and device ~= "" and not device:find("%c") then
  hl.device({ name = device, sensitivity = sensitivity })
end
