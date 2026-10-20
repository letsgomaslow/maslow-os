echo "Add the trackpad widget to the bar"

# The widget is now in the default layout, just right of the audio widget. It
# hides itself unless a touchpad is detected, so adding it to every existing bar
# is free: a desktop without one never sees it. A bar that already carries the
# widget keeps it where the user put it.

omarchy-bar put omarchy.trackpad --after omarchy.audio
