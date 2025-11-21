#!/usr/bin/env python3
import argparse
import configparser
import json
import shutil
import os
import re
import subprocess
from pathlib import Path

def get_active_color_scheme():
    try:
        result = subprocess.run(
            ["kreadconfig6", "--file", "kdeglobals", "--group", "General", "--key", "ColorScheme"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip() or None
    except (FileNotFoundError, subprocess.CalledProcessError):
        kdeglobals = Path("~/.config/kdeglobals").expanduser()
        if kdeglobals.exists():
            config = configparser.ConfigParser()
            config.read(kdeglobals)
            return config.get("General", "ColorScheme", fallback=None)
    return None

def get_color_scheme_path(scheme_name):
    kde_colors_dir = Path("~/.local/share/color-schemes").expanduser()
    scheme_file = kde_colors_dir / f"{scheme_name}.colors"
    if scheme_file.exists():
        return scheme_file
    return None

def get_color(scheme_path, color_section, color_key):
    config = configparser.ConfigParser()
    config.read(scheme_path)
    try:
        color_value = config.get(color_section, color_key)
        match = re.match(r"#?([0-9A-Fa-f]{6})", color_value)
        if match:
            # Return in format #rrggbb (lowercase)
            return f"#{match.group(1).lower()}"
    except (configparser.NoSectionError, configparser.NoOptionError):
        pass
    return None


def normalize_color(c):
    """Normalize a color value to '#rrggbb' format or return None."""
    if not c:
        return None
    if not isinstance(c, str):
        return None
    s = c.strip()
    m = re.match(r"#?([0-9A-Fa-f]{6})", s)
    if not m:
        return None
    return f"#{m.group(1).lower()}"

def hex_to_rgb(hex_color):
    # Accept format with or without '#'
    if isinstance(hex_color, str) and hex_color.startswith('#'):
        hex_color = hex_color[1:]

    if not isinstance(hex_color, str) or len(hex_color) != 6:
        raise ValueError(f"Invalid hex color value: {hex_color}")

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return r, g, b

def rgb_to_hex(r, g, b):
    return f'#{r:02x}{g:02x}{b:02x}'

def get_accent_color():
    try:
        result = subprocess.run(
            ["kreadconfig6", "--file", "kdeglobals", "--group", "General", "--key", "AccentColor"],
            capture_output=True, text=True, check=True
        )
        accent_temp = result.stdout.strip()
        accent_hex = None
        accent_rgb = None
        
        # RGB format (r, g, b)
        if re.fullmatch(r'\d{1,3},\s*\d{1,3},\s*\d{1,3}', accent_temp):
            r, g, b = [int(c.strip()) for c in accent_temp.split(',')]
            accent_hex = rgb_to_hex(r, g, b)
            accent_rgb = (r, g, b)
            return accent_hex, accent_rgb
            
        # Hexadecimal format
        if re.fullmatch(r'#[0-9A-Fa-f]{6}', accent_temp):
            accent_hex = accent_temp
            accent_rgb = hex_to_rgb(accent_hex[1:])
            return accent_hex, accent_rgb
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    return None, None

def better_contrast_selection(base_color, colors=None):
    if colors is None:
        colors = []

    def srgb_channel_to_linear(c8):
        c = c8 / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    def luminance_from_rgb(rgb):
        r, g, b = rgb
        return 0.2126 * srgb_channel_to_linear(r) + \
               0.7152 * srgb_channel_to_linear(g) + \
               0.0722 * srgb_channel_to_linear(b)

    def contrast_ratio(lum1, lum2):
        L1, L2 = max(lum1, lum2), min(lum1, lum2)
        return (L1 + 0.05) / (L2 + 0.05)

    # normalize base_color and compute luminance
    base_rgb = hex_to_rgb(base_color)
    base_lum = luminance_from_rgb(base_rgb)

    best_color = None
    best_contrast = -1.0

    for c in colors:
        if not c:
            continue
        rgb = hex_to_rgb(c)
        lum = luminance_from_rgb(rgb)
        cr = contrast_ratio(base_lum, lum)
        if cr > best_contrast:
            best_contrast = cr
            best_color = c

    # If there are no valid candidates, choose between black/white
    if best_color is None:
        black_lum = luminance_from_rgb(hex_to_rgb('#000000'))
        white_lum = luminance_from_rgb(hex_to_rgb('#ffffff'))
        bcr = contrast_ratio(base_lum, black_lum)
        wcr = contrast_ratio(base_lum, white_lum)
        return '#000000' if bcr >= wcr else '#ffffff'

    return best_color

def darkest_brightest_color(colors):
    """Return the darkest and brightest colors from a list of hex colors."""
    if not colors:
        return '#000000', '#ffffff'
    
    # Filter out None values and normalize colors
    valid_colors = [normalize_color(c) for c in colors if normalize_color(c)]
    
    if not valid_colors:
        return '#000000', '#ffffff'
    
    def srgb_channel_to_linear(c8):
        c = c8 / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    def luminance_from_rgb(rgb):
        r, g, b = rgb
        return 0.2126 * srgb_channel_to_linear(r) + \
               0.7152 * srgb_channel_to_linear(g) + \
               0.0722 * srgb_channel_to_linear(b)
    
    darkest = valid_colors[0]
    brightest = valid_colors[0]
    min_lum = luminance_from_rgb(hex_to_rgb(darkest))
    max_lum = min_lum
    
    for color in valid_colors[1:]:
        rgb = hex_to_rgb(color)
        lum = luminance_from_rgb(rgb)
        
        if lum < min_lum:
            min_lum = lum
            darkest = color
        
        if lum > max_lum:
            max_lum = lum
            brightest = color
    
    return darkest, brightest

def build_ulauncher_palette(scheme_path, accent_hex):
    # Load pywal colors
    json_path = Path('~/.cache/wal/colors.json').expanduser()
    special = {}
    colors = {}
    if json_path.exists():
        with open(json_path, 'r') as jf:
            data = json.load(jf)
            special = data.get('special', {})
            colors = data.get('colors', {})
        if accent_hex is None:
            accent_hex = colors.get('color1', '#ff0000')
        term_text = special.get('foreground', None)
    else:
        if accent_hex is None:
            accent_hex = '#ff0000'
        term_text = get_color(scheme_path, "Colors:Window", "ForegroundNormal")

    # Normalize `accent_hex` to a '#rrggbb' string
    accent_hex = normalize_color(accent_hex)
    
    text = normalize_color(get_color(scheme_path, "Colors:Window", "ForegroundNormal"))
    text2 = normalize_color(get_color(scheme_path, "Colors:Selection", "ForegroundActive"))
    term_text = normalize_color(term_text)
    accent_text = better_contrast_selection(accent_hex, [text, text2, term_text])

    bg_color = normalize_color(get_color(scheme_path, "Colors:Window", "BackgroundNormal"))
    window_border_color = normalize_color(get_color(scheme_path, "Colors:Window", "BackgroundAlternate"))
    prefs_bg = normalize_color(get_color(scheme_path, "Colors:Window", "ForegroundInactive"))
    input_color = normalize_color(get_color(scheme_path, "Colors:Window", "ForegroundNormal"))
    selected_bg_color = normalize_color(get_color(scheme_path, "Colors:Selection", "BackgroundNormal"))
    selected_fg_color = normalize_color(get_color(scheme_path, "Colors:Selection", "ForegroundNormal"))
    item_name = normalize_color(get_color(scheme_path, "Colors:Window", "ForegroundNormal"))
    item_text = normalize_color(get_color(scheme_path, "Colors:Window", "ForegroundInactive"))
    item_shortcut_color = normalize_color(get_color(scheme_path, "Colors:Selection", "DecorationFocus"))
    item_box_selected = normalize_color(accent_hex)
    item_name_selected = normalize_color(darkest_brightest_color([text, text2, term_text])[0])#normalize_color(accent_text)
    item_text_selected = normalize_color(darkest_brightest_color([text, text2, term_text])[0])#normalize_color(accent_text)
    item_shortcut_color_sel = normalize_color(darkest_brightest_color([text, text2, term_text])[1])
    when_selected = normalize_color(darkest_brightest_color([text, text2, term_text])[1])
    #when_not_selected = normalize_color(get_color(scheme_path, "Colors:Selection", "DecorationFocus"))
    #when_not_selected = normalize_color(accent_hex)
    when_not_selected = normalize_color(better_contrast_selection(bg_color, [accent_hex, item_shortcut_color]))


    #darkest, brightest = darkest_brightest_color([text, text2, term_text, accent_text])
    #print(text, text2, term_text, accent_text)
    #print("Oscuro", darkest)
    #print("Brillante", brightest)

    return {
        'bg_color': bg_color,
        'window_border_color': window_border_color,
        'prefs_background': prefs_bg,
        'input_color': input_color,
        'selected_bg_color': selected_bg_color,
        'selected_fg_color': selected_fg_color,
        'item_name': item_name,
        'item_text': item_text,
        'item_shortcut_color': item_shortcut_color,
        'item_box_selected': item_box_selected,
        'item_name_selected': item_name_selected,
        'item_text_selected': item_text_selected,
        'item_shortcut_color_sel': item_shortcut_color_sel,
        'when_selected': when_selected,
        'when_not_selected': when_not_selected
    }

def gen_ulauncher_config(palette, template_dir):
    # gen_ulauncher_config reads template files and replaces placeholders with actual colors and returns the generated manifest and css content for out_manifest and out_css.
    template_manifest_path = Path(template_dir) / "manifest.json"
    template_css_path = Path(template_dir) / "theme.css"
    if not template_manifest_path.exists():
        raise FileNotFoundError(f"Template manifest file not found: {template_manifest_path}")
    if not template_css_path.exists():
        raise FileNotFoundError(f"Template CSS file not found: {template_css_path}")
    with open(template_manifest_path, 'r') as f:
        template_manifest = f.read()
    with open(template_css_path, 'r') as f:
        template_css = f.read()

    def hex_to_rgba(hex_color, alpha=0.8):
        #print(f"Converting hex color {hex_color} to rgba with alpha {alpha}")
        r, g, b = hex_to_rgb(hex_color)
        return f'rgba({r}, {g}, {b}, {alpha})'
    
    # Replace placeholders in manifest
    # Example:
    #"when_selected": "hex_color",
    #"when_not_selected": "hex_color"

    for key, value in palette.items():
        placeholder = f'"{key}": "hex_color"'
        replacement = f'"{key}": "{value}"'
        template_manifest = template_manifest.replace(placeholder, replacement)

    # Replace placeholders in readed template_css
    # Example:
    # @define-color bg_color rgba_color;
    # @define-color input_color hex_color;

    for key, value in palette.items():
        placeholder1 = f'@define-color {key} rgba_color;'
        replacement1 = f'@define-color {key} {hex_to_rgba(value)};'
        placeholder2 = f'@define-color {key} hex_color;'
        replacement2 = f'@define-color {key} {value};'
        template_css = template_css.replace(placeholder1, replacement1)
        template_css = template_css.replace(placeholder2, replacement2)
    
    #print("Generated Ulauncher manifest and CSS configuration.")

    return template_manifest, template_css

def refresh_ulauncher():
    ulauncher_settings_path = Path(f"{os.environ['HOME']}/.config/ulauncher") / "settings.json"
    #print("Ulauncher settings path:", ulauncher_settings_path)

    if ulauncher_settings_path.exists():
        current_theme = None
        with open(ulauncher_settings_path, 'r') as f:
            for line in f:
                if "theme-name" in line:
                    current_theme = line.split(':')[1].strip().strip('",')
                    #print(f"Current Ulauncher theme: {current_theme}")
                    if current_theme != "KDE_theme":
                        #print("Setting Ulauncher theme to KDE_theme")
                        f.seek(0)
                        settings_data = f.read()
                        settings_data = re.sub(r'"theme-name"\s*:\s*".*?"', '"theme-name": "KDE_theme"', settings_data)
                        with open(ulauncher_settings_path, 'w') as fw:
                            fw.write(settings_data)
                    break

    if subprocess.run(['pgrep', 'ulauncher'], capture_output=True).stdout:
        subprocess.run(['pkill', 'ulauncher'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Restart or open Ulauncher
    env = os.environ.copy()
    env['GDK_BACKEND'] = 'x11'
    subprocess.Popen(
        ['ulauncher', '--hide-window', '--no-window-shadow'],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

def main():
    parser = argparse.ArgumentParser(description="Generate Ulauncher configuration based on the active KDE color scheme.")
    parser.add_argument('-o', '--output', type=str, required=True, help="output folder for the generated Ulauncher configuration.")
    parser.add_argument('-t', '--template', type=str, required=True, help="template folder for the Ulauncher configuration.")
    parser.add_argument('-c', '--accent-color', type=str, dest='accent_color', default=None, help="optional accent color in hex format (e.g., #ff0000). If not provided, the system accent color will be used.")
    parser.add_argument('-r', '--restart', dest='restart_ulauncher', action='store_true', help="restart Ulauncher instance after generation.")
    args = parser.parse_args()

    scheme_name = get_active_color_scheme()
    if not scheme_name:
        print("Could not determine the active KDE color scheme.")
        return

    scheme_path = get_color_scheme_path(scheme_name)
    if not scheme_path:
        print(f"Could not find color scheme file: {scheme_name}")
        return

    accent_hex = args.accent_color if args.accent_color else get_accent_color()[0]

    # Expand user and env vars for template and output paths
    template_path = os.path.expanduser(os.path.expandvars(args.template))
    output_path = os.path.expanduser(os.path.expandvars(args.output))

    # Ensure template exists before proceeding
    if not Path(template_path).exists():
        print(f"Could not find template file: {template_path}")
        return

    palette = build_ulauncher_palette(scheme_path, accent_hex)
    #print("Generated Ulauncher color palette from KDE color scheme.", palette)

    try:
        ulauncher_manifest_config, ulauncher_css_config = gen_ulauncher_config(palette, template_path)
    except FileNotFoundError as e:
        print(str(e))
        return

    # Ensure output directory exists
    out_dir = Path(output_path).expanduser()
    # if user passed a filename, keep parent behavior, else use folder directly
    if out_dir.suffix:  # if has suffix, treat as file path
        out_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_manifest = out_dir / "manifest.json"
    out_css = out_dir / "theme.css"
    out_license = out_dir / "LICENSE"
    out_gtk_css = out_dir / "theme-gtk-3.20.css"

    # backup existing file with shutil
    # Hacer backup solo si los archivos ya existen
    if out_manifest.exists():
        shutil.copy2(out_manifest, out_manifest.with_suffix(".bak"))
    if out_css.exists():
        shutil.copy2(out_css, out_css.with_suffix(".bak"))
    if not out_license.exists():
        shutil.copy(Path(template_path) / "LICENSE", out_dir / "LICENSE")
    if not out_gtk_css.exists():
        shutil.copy(Path(template_path) / "theme-gtk-3.20.css", out_dir / "theme-gtk-3.20.css")

    with open(out_manifest, 'w') as f:
        f.write(ulauncher_manifest_config)

    with open(out_css, 'w') as f:
        f.write(ulauncher_css_config)
    
    if args.restart_ulauncher:
        refresh_ulauncher()

    # print(f"Ulauncher configuration generated at: {out_manifest}")
    # print(f"Ulauncher CSS generated at: {out_css}")

if __name__ == "__main__":
    main()
