#!/usr/bin/env sh
set -e

PKG_PY="/usr/bin/kde-ulauncher"
REPO_TEMPLATE_DIR="template"

# Determine the target user's home (mirror install.sh behavior)
if [ -n "$SUDO_USER" ]; then
  USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
  if [ -z "$USER_HOME" ]; then
    USER_HOME=$(eval echo "~$SUDO_USER")
  fi
  if [ -z "$USER_HOME" ]; then
    USER_HOME="$HOME"
  fi
else
  USER_HOME="$HOME"
fi

INST_TEMPLATE_DIR="$USER_HOME/.config/kde_ulauncher"

echo "Uninstalling installed files (sudo required for system files)..."
sudo rm -f "$PKG_PY" || true

if [ -d "$INST_TEMPLATE_DIR" ] && [ -d "$REPO_TEMPLATE_DIR" ]; then
  # Compare directories recursively; if identical, remove installed template
  if diff -r -q "$REPO_TEMPLATE_DIR" "$INST_TEMPLATE_DIR" >/dev/null 2>&1; then
    echo "Installed template matches the repository template; removing $INST_TEMPLATE_DIR"
    rm -rf "$INST_TEMPLATE_DIR"
  else
    echo "Installed template $INST_TEMPLATE_DIR differs from repository template; leaving it in place."
  fi
fi

echo "Uninstall complete."
