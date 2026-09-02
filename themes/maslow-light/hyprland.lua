local active_border_color = { colors = { "rgba(a92f73ee)", "rgba(247967ee)" }, angle = 45 }
local inactive_border_color = "rgba(8c95a888)"

hl.config({
  general = {
    gaps_in = 8,
    gaps_out = 16,
    border_size = 2,
    col = {
      active_border = active_border_color,
      inactive_border = inactive_border_color,
    },
  },
  decoration = {
    rounding = 8,
    shadow = { enabled = false },
    blur = { enabled = false },
  },
  group = {
    col = {
      border_active = active_border_color,
      border_inactive = inactive_border_color,
    },
  },
})
