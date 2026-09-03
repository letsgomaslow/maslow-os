echo "Label existing Limine boot entries as Maslow OS"

limine_conf="${MASLOW_LIMINE_CONF:-/boot/limine.conf}"

[[ -f $limine_conf ]] || exit 0
grep -Fxq '/+Omarchy' "$limine_conf" || exit 0

if (( EUID == 0 )); then
  as_root() { "$@"; }
else
  as_root() { sudo "$@"; }
fi

as_root sed -i \
  -e 's|^/+Omarchy$|/+Maslow OS|' \
  -e 's|^comment: Omarchy$|comment: Maslow OS|' \
  "$limine_conf"

grep -Fxq '/+Maslow OS' "$limine_conf"
grep -Fxq 'comment: Maslow OS' "$limine_conf"
