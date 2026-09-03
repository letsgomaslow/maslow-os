if grep -qx 'high_contrast=true' "$HOME/.config/maslow-os/accessibility.conf" 2>/dev/null; then
  gsettings set org.gnome.desktop.interface gtk-theme "HighContrast"
else
  gsettings set org.gnome.desktop.interface gtk-theme "Adwaita-dark"
fi
gsettings set org.gnome.desktop.interface color-scheme "prefer-dark"
gsettings set org.gnome.desktop.interface icon-theme "Yaru-blue"
