#!/bin/bash

# Keep the ARM development preview's visible login identity after its upstream
# Omarchy package is upgraded. The hook itself is comparison-gated and becomes
# a no-op once Maslow packages own the installed login assets.
hook="$OMARCHY_PATH/install/user/first-run/maslow-login-branding.hook"
[[ -f $hook ]] && omarchy-hook-install post-update "$hook"
