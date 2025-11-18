# kde-ulauncher

Generate an Ulauncher theme from the active KDE color scheme.

This repository provides a small Python utility that reads your current KDE
color scheme and generates an Ulauncher theme (a `manifest.json`
and `theme.css`) by applying the colors based in templates contained in
the `template/` directory.

**Requirements**
- Python 3.6+
- `kreadconfig6` (required) — used to detect the active KDE color scheme automatically.
- Ulauncher (to install/use the generated theme), optional for generation itself.

**Repository layout**
- `src/kde_ulauncher.py` — main generator script.
- `template/` — template `manifest.json`, `theme.css`, `LICENSE`, and GTK CSS.
- `install.sh`, `uninstall.sh` — convenience scripts for optional system-wide install.

**Usage**

Generate a theme into a destination directory (example):

```sh
kde-ulauncher -o ~/.config/ulauncher/user-themes/KDE-Theme -t ~/.config/kde_ulauncher/template
```

- `-o, --output`: output folder for the generated Ulauncher configuration. The folder will be created if needed.
- `-t, --template`: path to the template folder (defaults to this repository's `template/`).

What the script does:
- Detects the active KDE color scheme (using `kreadconfig6` or falling back to `~/.config/kdeglobals`).
- Builds a color palette and substitutes placeholders in the template `manifest.json` and `theme.css`.
- Writes `manifest.json` and `theme.css` to the output folder and copies `LICENSE` and `theme-gtk-3.20.css` if missing.
- If target files already exist, they are backed up with a `.bak` suffix before being overwritten.

**Install / Uninstall (optional)**

Install system-wide (if desired):

```sh
chmod +x install.sh
sudo sh ./install.sh
```

Uninstall:

```sh
chmod +x uninstall.sh
sudo sh ./uninstall.sh
```
