#!/usr/bin/env sh
# Simple installer script: install the Python script into /usr/bin

set -e

PY_SCRIPT="src/kde_ulauncher.py"

echo "Installing files (sudo required to copy to /usr/bin)..."

echo "Installing Python script to /usr/bin/kde-ulauncher..."
if [ -f "$PY_SCRIPT" ]; then
  sudo cp "$PY_SCRIPT" /usr/bin/kde-ulauncher
  sudo chmod 755 /usr/bin/kde-ulauncher
else
  echo "Error: $PY_SCRIPT not found in the repository." >&2
  exit 1
fi

# Determine target user home directory. If script is run with sudo,
# prefer the original user's home directory (from SUDO_USER). Otherwise use $HOME.
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

CONFIG_DIR="$USER_HOME/.config/kde_ulauncher"
mkdir -p "$CONFIG_DIR"

if [ -d "template" ]; then
  # Copy contents of template dir into the user's config directory
  cp -r "template/"* "$CONFIG_DIR/" || true
  # If we created/copied as root (sudo), make sure the files are owned by the user.
  if [ -n "$SUDO_USER" ]; then
    USER_GROUP=$(id -gn "$SUDO_USER" 2>/dev/null || echo "$SUDO_USER")
    chown -R "$SUDO_USER":"$USER_GROUP" "$CONFIG_DIR" || true
  fi
  echo "Template installed to $CONFIG_DIR/"
else
  echo "Warning: template/ not found in repository." >&2
fi

echo "Installation complete — Python script installed as /usr/bin/kde-ulauncher."
