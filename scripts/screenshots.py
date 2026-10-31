"""Render the Smart Comfort panel with mock data and save the README screenshots, in the light and the dark theme.

Usage: python scripts/screenshots.py  (needs `pip install playwright` and `playwright install chromium`)
CHROMIUM_PATH=/path/to/chrome to use another browser. The clock is frozen and the time zone is UTC, so the times stay
the same. The panel runs in a page that mimics Home Assistant: a static sidebar, the theme variables, and stand-ins for
<ha-icon>, <ha-menu-button> and <ha-form> (its text, number, select, boolean, entity and expandable fields). The
WebSocket commands of the panel (config, subscribe, discover, translations) answer with the mock data below; the
alert and control defaults and the field labels come from the integration itself (const.py, translations/en.json).
"""

import importlib.util
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components/smart_comfort"
PANEL_JS = (COMPONENT / "frontend/smart-comfort-panel.js").read_text()
TRANSLATIONS = json.loads((COMPONENT / "translations/en.json").read_text())
DOMAIN = "smart_comfort"
NOW = "2026-10-24T11:45:00Z"
URL = "http://homeassistant.local/smart-comfort"
WIDTH = 1280

# const.py only imports typing: load it alone, without the package (which needs Home Assistant).
_spec = importlib.util.spec_from_file_location("smart_comfort_const", COMPONENT / "const.py")
const = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(const)

THEMES = {
    "light": {
        "--primary-background-color": "#fafafa",
        "--secondary-background-color": "#e5e5e5",
        "--card-background-color": "#ffffff",
        "--primary-text-color": "#212121",
        "--secondary-text-color": "#727272",
        "--disabled-text-color": "#bdbdbd",
        "--divider-color": "rgba(0,0,0,.12)",
        "--app-header-background-color": "#ffffff",
        "--app-header-text-color": "#212121",
        "--sidebar-background-color": "#ffffff",
        "--sidebar-icon-color": "rgba(0,0,0,.5)",
        "--input-fill-color": "#f5f5f5",
        "--input-line-color": "rgba(0,0,0,.42)",
        "--switch-off-track": "rgba(0,0,0,.38)",
        "--switch-off-thumb": "#fafafa",
        "--rgb-primary-text-color": "33,33,33",
    },
    "dark": {
        "--primary-background-color": "#111111",
        "--secondary-background-color": "#282828",
        "--card-background-color": "#1c1c1c",
        "--primary-text-color": "#e1e1e1",
        "--secondary-text-color": "#9b9b9b",
        "--disabled-text-color": "#6f6f6f",
        "--divider-color": "rgba(225,225,225,.12)",
        "--app-header-background-color": "#1c1c1c",
        "--app-header-text-color": "#e1e1e1",
        "--sidebar-background-color": "#1c1c1c",
        "--sidebar-icon-color": "rgba(225,225,225,.6)",
        "--input-fill-color": "#262626",
        "--input-line-color": "rgba(225,225,225,.42)",
        "--switch-off-track": "rgba(225,225,225,.3)",
        "--switch-off-thumb": "#bbbbbb",
        "--rgb-primary-text-color": "225,225,225",
    },
}
COMMON = {
    "--primary-color": "#03a9f4",
    "--rgb-primary-color": "3,169,244",
    "--info-color": "#039be5",
    "--rgb-info-color": "3,155,229",
    "--success-color": "#43a047",
    "--warning-color": "#ffa600",
    "--error-color": "#db4437",
    "--text-primary-color": "#ffffff",
    "--header-height": "56px",
    "--app-header-border-bottom": "1px solid var(--divider-color)",
}

# Material Design Icons paths used by the panel, the form fields and the sidebar (from @mdi/js 7.4.47).
ICONS = {
    "motion-sensor": "M10,0.2C9,0.2 8.2,1 8.2,2C8.2,3 9,3.8 10,3.8C11,3.8 11.8,3 11.8,2C11.8,1 11,0.2 10,0.2M15.67,1A7.33,7.33 0 0,0 23,8.33V7A6,6 0 0,1 17,1H15.67M18.33,1C18.33,3.58 20.42,5.67 23,5.67V4.33C21.16,4.33 19.67,2.84 19.67,1H18.33M21,1A2,2 0 0,0 23,3V1H21M7.92,4.03C7.75,4.03 7.58,4.06 7.42,4.11L2,5.8V11H3.8V7.33L5.91,6.67L2,22H3.8L6.67,13.89L9,17V22H10.8V15.59L8.31,11.05L9.04,8.18L10.12,10H15V8.2H11.38L9.38,4.87C9.08,4.37 8.54,4.03 7.92,4.03Z",
    "brightness-5": "M12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6A6,6 0 0,1 18,12A6,6 0 0,1 12,18M20,15.31L23.31,12L20,8.69V4H15.31L12,0.69L8.69,4H4V8.69L0.69,12L4,15.31V20H8.69L12,23.31L15.31,20H20V15.31Z",
    "sofa": "M12.5 7C12.5 5.89 13.39 5 14.5 5H18C19.1 5 20 5.9 20 7V9.16C18.84 9.57 18 10.67 18 11.97V14H12.5V7M6 11.96V14H11.5V7C11.5 5.89 10.61 5 9.5 5H6C4.9 5 4 5.9 4 7V9.15C5.16 9.56 6 10.67 6 11.96M20.66 10.03C19.68 10.19 19 11.12 19 12.12V15H5V12C5 10.9 4.11 10 3 10S1 10.9 1 12V17C1 18.1 1.9 19 3 19V21H5V19H19V21H21V19C22.1 19 23 18.1 23 17V12C23 10.79 21.91 9.82 20.66 10.03Z",
    "bed": "M19,7H11V14H3V5H1V20H3V17H21V20H23V11A4,4 0 0,0 19,7M7,13A3,3 0 0,0 10,10A3,3 0 0,0 7,7A3,3 0 0,0 4,10A3,3 0 0,0 7,13Z",
    "shower": "M21,14V15C21,16.91 19.93,18.57 18.35,19.41L19,22H17L16.5,20C16.33,20 16.17,20 16,20H8C7.83,20 7.67,20 7.5,20L7,22H5L5.65,19.41C4.07,18.57 3,16.91 3,15V14H2V12H20V5A1,1 0 0,0 19,4C18.5,4 18.12,4.34 18,4.79C18.63,5.33 19,6.13 19,7H13A3,3 0 0,1 16,4C16.06,4 16.11,4 16.17,4C16.58,2.84 17.69,2 19,2A3,3 0 0,1 22,5V14H21V14M19,14H5V15A3,3 0 0,0 8,18H16A3,3 0 0,0 19,15V14Z",
    "desk": "M3 6H21C21.55 6 22 6.45 22 7C22 7.55 21.55 8 21 8V19H19V17H15V19H13V8H5V19H3V8C2.45 8 2 7.55 2 7C2 6.45 2.45 6 3 6M16 10.5V11H18V10.5C18 10.22 17.78 10 17.5 10H16.5C16.22 10 16 10.22 16 10.5M16 14.5V15H18V14.5C18 14.22 17.78 14 17.5 14H16.5C16.22 14 16 14.22 16 14.5Z",
    "flower": "M3,13A9,9 0 0,0 12,22C12,17 7.97,13 3,13M12,5.5A2.5,2.5 0 0,1 14.5,8A2.5,2.5 0 0,1 12,10.5A2.5,2.5 0 0,1 9.5,8A2.5,2.5 0 0,1 12,5.5M5.6,10.25A2.5,2.5 0 0,0 8.1,12.75C8.63,12.75 9.12,12.58 9.5,12.31C9.5,12.37 9.5,12.43 9.5,12.5A2.5,2.5 0 0,0 12,15A2.5,2.5 0 0,0 14.5,12.5C14.5,12.43 14.5,12.37 14.5,12.31C14.88,12.58 15.37,12.75 15.9,12.75C17.28,12.75 18.4,11.63 18.4,10.25C18.4,9.25 17.81,8.4 16.97,8C17.81,7.6 18.4,6.74 18.4,5.75C18.4,4.37 17.28,3.25 15.9,3.25C15.37,3.25 14.88,3.41 14.5,3.69C14.5,3.63 14.5,3.56 14.5,3.5A2.5,2.5 0 0,0 12,1A2.5,2.5 0 0,0 9.5,3.5C9.5,3.56 9.5,3.63 9.5,3.69C9.12,3.41 8.63,3.25 8.1,3.25A2.5,2.5 0 0,0 5.6,5.75C5.6,6.74 6.19,7.6 7.03,8C6.19,8.4 5.6,9.25 5.6,10.25M12,22A9,9 0 0,0 21,13C16,13 12,17 12,22Z",
    "home-outline": "M12 5.69L17 10.19V18H15V12H9V18H7V10.19L12 5.69M12 3L2 12H5V20H11V14H13V20H19V12H22",
    "toilet": "M9,22H17V19.5C19.41,17.87 21,15.12 21,12V4A2,2 0 0,0 19,2H15C13.89,2 13,2.9 13,4V12H3C3,15.09 5,18 9,19.5V22M5.29,14H18.71C18.14,15.91 16.77,17.5 15,18.33V20H11V18.33C9,18 5.86,15.91 5.29,14M15,4H19V12H15V4M16,5V8H18V5H16Z",
    "silverware-fork-knife": "M11,9H9V2H7V9H5V2H3V9C3,11.12 4.66,12.84 6.75,12.97V22H9.25V12.97C11.34,12.84 13,11.12 13,9V2H11V9M16,6V14H18.5V22H21V2C18.24,2 16,4.24 16,6Z",
    "door": "M8,3C6.89,3 6,3.89 6,5V21H18V5C18,3.89 17.11,3 16,3H8M8,5H16V19H8V5M13,11V13H15V11H13Z",
    "door-open": "M12,3C10.89,3 10,3.89 10,5H3V19H2V21H22V19H21V5C21,3.89 20.11,3 19,3H12M12,5H19V19H12V5M5,11H7V13H5V11Z",
    "table-furniture": "M2 7H22V10H20L21 19H18.5L17.94 14H6.06L5.5 19H3L4 10H2V7M17.5 10H6.5L6.29 12H17.71L17.5 10Z",
    "chevron-up": "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z",
    "plus": "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z",
    "tune-variant": "M8 13C6.14 13 4.59 14.28 4.14 16H2V18H4.14C4.59 19.72 6.14 21 8 21S11.41 19.72 11.86 18H22V16H11.86C11.41 14.28 9.86 13 8 13M8 19C6.9 19 6 18.1 6 17C6 15.9 6.9 15 8 15S10 15.9 10 17C10 18.1 9.1 19 8 19M19.86 6C19.41 4.28 17.86 3 16 3S12.59 4.28 12.14 6H2V8H12.14C12.59 9.72 14.14 11 16 11S19.41 9.72 19.86 8H22V6H19.86M16 9C14.9 9 14 8.1 14 7C14 5.9 14.9 5 16 5S18 5.9 18 7C18 8.1 17.1 9 16 9Z",
    "clock-outline": "M12,20A8,8 0 0,0 20,12A8,8 0 0,0 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22C6.47,22 2,17.5 2,12A10,10 0 0,1 12,2M12.5,7V12.25L17,14.92L16.25,16.15L11,13V7H12.5Z",
    "clock-edit-outline": "M21 13.1C20.9 13.1 20.7 13.2 20.6 13.3L19.6 14.3L21.7 16.4L22.7 15.4C22.9 15.2 22.9 14.8 22.7 14.6L21.4 13.3C21.3 13.2 21.2 13.1 21 13.1M19.1 14.9L13 20.9V23H15.1L21.2 16.9L19.1 14.9M12.5 7V12.2L16.5 14.6L15.5 15.6L11 13V7H12.5M11 21.9C5.9 21.4 2 17.1 2 12C2 6.5 6.5 2 12 2C17.3 2 21.6 6.1 22 11.3C21.7 11.2 21.4 11.1 21 11.1C20.6 11.1 20.3 11.2 20 11.3C19.6 7.2 16.2 4 12 4C7.6 4 4 7.6 4 12C4 16.1 7.1 19.5 11.1 19.9L11 20.1V21.9Z",
    "bell-sleep-outline": "M10,21H14A2,2 0 0,1 12,23A2,2 0 0,1 10,21M21,19V20H3V19L5,17V11C5,7.9 7.03,5.17 10,4.29C10,4.19 10,4.1 10,4A2,2 0 0,1 12,2A2,2 0 0,1 14,4C14,4.1 14,4.19 14,4.29C16.97,5.17 19,7.9 19,11V17L21,19M17,11A5,5 0 0,0 12,6A5,5 0 0,0 7,11V18H17V11M9,9V11H12.24L9,13.7V16H15V14H11.76L15,11.3V9H9Z",
    "weather-sunset-up": "M3,12H7A5,5 0 0,1 12,7A5,5 0 0,1 17,12H21A1,1 0 0,1 22,13A1,1 0 0,1 21,14H3A1,1 0 0,1 2,13A1,1 0 0,1 3,12M15,12A3,3 0 0,0 12,9A3,3 0 0,0 9,12H15M12,2L14.39,5.42C13.65,5.15 12.84,5 12,5C11.16,5 10.35,5.15 9.61,5.42L12,2M3.34,7L7.5,6.65C6.9,7.16 6.36,7.78 5.94,8.5C5.5,9.24 5.25,10 5.11,10.79L3.34,7M20.65,7L18.88,10.79C18.74,10 18.47,9.23 18.05,8.5C17.63,7.78 17.1,7.15 16.5,6.64L20.65,7M12.71,16.3L15.82,19.41C16.21,19.8 16.21,20.43 15.82,20.82C15.43,21.21 14.8,21.21 14.41,20.82L12,18.41L9.59,20.82C9.2,21.21 8.57,21.21 8.18,20.82C7.79,20.43 7.79,19.8 8.18,19.41L11.29,16.3C11.5,16.1 11.74,16 12,16C12.26,16 12.5,16.1 12.71,16.3Z",
    "bell-alert-outline": "M12 2A2 2 0 0 0 10 4A2 2 0 0 0 10 4.29C7.12 5.14 5 7.82 5 11V17L3 19V20H21V19L19 17V11C19 7.82 16.88 5.14 14 4.29A2 2 0 0 0 14 4A2 2 0 0 0 12 2M12 6A5 5 0 0 1 17 11V18H7V11A5 5 0 0 1 12 6M21 7V13H23V7H21M21 15V17H23V15H21M10 21A2 2 0 0 0 12 23A2 2 0 0 0 14 21H10Z",
    "weather-partly-cloudy": "M12.74,5.47C15.1,6.5 16.35,9.03 15.92,11.46C17.19,12.56 18,14.19 18,16V16.17C18.31,16.06 18.65,16 19,16A3,3 0 0,1 22,19A3,3 0 0,1 19,22H6A4,4 0 0,1 2,18A4,4 0 0,1 6,14H6.27C5,12.45 4.6,10.24 5.5,8.26C6.72,5.5 9.97,4.24 12.74,5.47M11.93,7.3C10.16,6.5 8.09,7.31 7.31,9.07C6.85,10.09 6.93,11.22 7.41,12.13C8.5,10.83 10.16,10 12,10C12.7,10 13.38,10.12 14,10.34C13.94,9.06 13.18,7.86 11.93,7.3M13.55,3.64C13,3.4 12.45,3.23 11.88,3.12L14.37,1.82L15.27,4.71C14.76,4.29 14.19,3.93 13.55,3.64M6.09,4.44C5.6,4.79 5.17,5.19 4.8,5.63L4.91,2.82L7.87,3.5C7.25,3.71 6.65,4.03 6.09,4.44M18,9.71C17.91,9.12 17.78,8.55 17.59,8L19.97,9.5L17.92,11.73C18.03,11.08 18.05,10.4 18,9.71M3.04,11.3C3.11,11.9 3.24,12.47 3.43,13L1.06,11.5L3.1,9.28C3,9.93 2.97,10.61 3.04,11.3M19,18H16V16A4,4 0 0,0 12,12A4,4 0 0,0 8,16H6A2,2 0 0,0 4,18A2,2 0 0,0 6,20H19A1,1 0 0,0 20,19A1,1 0 0,0 19,18Z",
    "lamp": "M8,2H16L20,14H4L8,2M11,15H13V20H18V22H6V20H11V15Z",
    "lightbulb-auto": "M9 2C5.13 2 2 5.13 2 9C2 11.38 3.19 13.47 5 14.74V17C5 17.55 5.45 18 6 18H12C12.55 18 13 17.55 13 17V14.74C14.81 13.47 16 11.38 16 9C16 5.13 12.87 2 9 2M6 21C6 21.55 6.45 22 7 22H11C11.55 22 12 21.55 12 21V20H6V21M19 13H17L13.8 22H15.7L16.4 20H19.6L20.3 22H22.2L19 13M16.85 18.65L18 15L19.15 18.65H16.85Z",
    "lightbulb-auto-outline": "M9 2C12.87 2 16 5.13 16 9C16 11.38 14.81 13.47 13 14.74V17C13 17.55 12.55 18 12 18H6C5.45 18 5 17.55 5 17V14.74C3.19 13.47 2 11.38 2 9C2 5.13 5.13 2 9 2M6 21V20H12V21C12 21.55 11.55 22 11 22H7C6.45 22 6 21.55 6 21M9 4C6.24 4 4 6.24 4 9C4 11.05 5.23 12.81 7 13.58V16H11V13.58C12.77 12.81 14 11.05 14 9C14 6.24 11.76 4 9 4M19 13H17L13.8 22H15.7L16.4 20H19.6L20.3 22H22.2L19 13M16.85 18.65L18 15L19.15 18.65H16.85Z",
    "lightbulb-off-outline": "M12,2C9.76,2 7.78,3.05 6.5,4.68L7.93,6.11C8.84,4.84 10.32,4 12,4A5,5 0 0,1 17,9C17,10.68 16.16,12.16 14.89,13.06L16.31,14.5C17.94,13.21 19,11.24 19,9A7,7 0 0,0 12,2M3.28,4L2,5.27L5.04,8.3C5,8.53 5,8.76 5,9C5,11.38 6.19,13.47 8,14.74V17A1,1 0 0,0 9,18H14.73L18.73,22L20,20.72L3.28,4M7.23,10.5L12.73,16H10V13.58C8.68,13 7.66,11.88 7.23,10.5M9,20V21A1,1 0 0,0 10,22H14A1,1 0 0,0 15,21V20H9Z",
    "lightbulb-outline": "M12,2A7,7 0 0,1 19,9C19,11.38 17.81,13.47 16,14.74V17A1,1 0 0,1 15,18H9A1,1 0 0,1 8,17V14.74C6.19,13.47 5,11.38 5,9A7,7 0 0,1 12,2M9,21V20H15V21A1,1 0 0,1 14,22H10A1,1 0 0,1 9,21M12,4A5,5 0 0,0 7,9C7,11.05 8.23,12.81 10,13.58V16H14V13.58C15.77,12.81 17,11.05 17,9A5,5 0 0,0 12,4Z",
    "ceiling-light": "M8,9H11V4H13V9H16L20,17H4L8,9M14,18A2,2 0 0,1 12,20A2,2 0 0,1 10,18H14Z",
    "floor-lamp": "M15,2L17,9H7L9,2M11,10H13V20H16V22H8V20H11V10Z",
    "lightbulb-night": "M6 21C6 21.55 6.45 22 7 22H11C11.55 22 12 21.55 12 21V20H6V21M13 16.32V17C13 17.55 12.55 18 12 18H6C5.45 18 5 17.55 5 17V14.74C3.19 13.47 2 11.38 2 9C2 5.13 5.13 2 9 2C10.65 2 12.16 2.57 13.35 3.5C10.8 4.57 9 7.07 9 10C9 12.79 10.64 15.19 13 16.32M20.92 9.94L19.5 9.03L18.1 10L18.5 8.35L17.17 7.32L18.85 7.21L19.41 5.6L20.04 7.18L21.72 7.22L20.42 8.3L20.92 9.94M19.39 13C17.5 15.27 14.03 15.19 12.22 12.95C10 10.13 11.56 6 15 5.34C15.34 5.29 15.64 5.63 15.5 5.97C15.05 7.25 15.12 8.71 15.85 9.97C16.58 11.24 17.79 12.03 19.12 12.25C19.47 12.3 19.62 12.74 19.39 13Z",
    "thermometer-high": "M15 13V5A3 3 0 0 0 9 5V13A5 5 0 1 0 15 13M12 4A1 1 0 0 1 13 5H11A1 1 0 0 1 12 4Z",
    "window-closed-variant": "M21 20V2H3V20H1V23H23V20M19 4V11H13V4M5 4H11V11H5M5 20V13H11V20M13 20V13H19V20Z",
    "code-braces": "M8,3A2,2 0 0,0 6,5V9A2,2 0 0,1 4,11H3V13H4A2,2 0 0,1 6,15V19A2,2 0 0,0 8,21H10V19H8V14A2,2 0 0,0 6,12A2,2 0 0,0 8,10V5H10V3M16,3A2,2 0 0,1 18,5V9A2,2 0 0,0 20,11H21V13H20A2,2 0 0,0 18,15V19A2,2 0 0,1 16,21H14V19H16V14A2,2 0 0,1 18,12A2,2 0 0,1 16,10V5H14V3H16Z",
    "led-off": "M12,6A4,4 0 0,0 8,10V16H6V18H9V23H11V18H13V23H15V18H18V16H16V10A4,4 0 0,0 12,6Z",
    "led-on": "M11,0V4H13V0H11M18.3,2.29L15.24,5.29L16.64,6.71L19.7,3.71L18.3,2.29M5.71,2.29L4.29,3.71L7.29,6.71L8.71,5.29L5.71,2.29M12,6A4,4 0 0,0 8,10V16H6V18H9V23H11V18H13V23H15V18H18V16H16V10A4,4 0 0,0 12,6M2,9V11H6V9H2M18,9V11H22V9H18Z",
    "window-open-variant": "M21 20V2H3V20H1V23H23V20M19 4V11H17V4M5 4H7V11H5M5 20V13H7V20M9 20V4H15V20M17 20V13H19V20Z",
    "thermometer-low": "M15 13V5A3 3 0 0 0 9 5V13A5 5 0 1 0 15 13M12 4A1 1 0 0 1 13 5V12H11V5A1 1 0 0 1 12 4Z",
    "snowflake-alert": "M16.46,9.41L13,7.38V5.12L14.71,3.41L13.29,2L12,3.29L10.71,2L9.29,3.41L11,5.12V7.38L8.5,8.82L6.5,7.69L5.92,5.36L4,5.88L4.47,7.65L2.7,8.12L3.22,10.05L5.55,9.43L7.55,10.56V13.45L5.55,14.58L3.22,13.96L2.7,15.89L4.47,16.36L4,18.12L5.93,18.64L6.55,16.31L8.55,15.18L11,16.62V18.88L9.29,20.59L10.71,22L12,20.71L13.29,22L14.7,20.59L13,18.88V16.62L16.46,14.61M9.5,10.56L12,9.11L14.5,10.56V13.44L12,14.89L9.5,13.44M19,13V7H21V13H19M19,17V15H21V17H19Z",
    "molecule-co2": "M5,7A2,2 0 0,0 3,9V15A2,2 0 0,0 5,17H8V15H5V9H8V7H5M11,7A2,2 0 0,0 9,9V15A2,2 0 0,0 11,17H13A2,2 0 0,0 15,15V9A2,2 0 0,0 13,7H11M11,9H13V15H11V9M16,10.5V12H19V13.5H17.5A1.5,1.5 0 0,0 16,15V18H20.5V16.5H17.5V15H19A1.5,1.5 0 0,0 20.5,13.5V12A1.5,1.5 0 0,0 19,10.5H16Z",
    "water-percent-alert": "M20 7V13H18V7H20M18 17H20V15H18V17M10 3.25C10 3.25 4 10 4 14C4 17.32 6.69 20 10 20S16 17.31 16 14C16 10 10 3.25 10 3.25M7.75 10C8.44 10 9 10.56 9 11.25S8.44 12.5 7.75 12.5 6.5 11.94 6.5 11.25 7.06 10 7.75 10M12.25 17C11.56 17 11 16.44 11 15.75S11.56 14.5 12.25 14.5 13.5 15.06 13.5 15.75 12.94 17 12.25 17M7.53 17.03L6.47 15.97L12.47 9.97L13.53 11.03L7.53 17.03Z",
    "volume-high": "M14,3.23V5.29C16.89,6.15 19,8.83 19,12C19,15.17 16.89,17.84 14,18.7V20.77C18,19.86 21,16.28 21,12C21,7.72 18,4.14 14,3.23M16.5,12C16.5,10.23 15.5,8.71 14,7.97V16C15.5,15.29 16.5,13.76 16.5,12M3,9V15H7L12,20V4L7,9H3Z",
    "volume-off": "M12,4L9.91,6.09L12,8.18M4.27,3L3,4.27L7.73,9H3V15H7L12,20V13.27L16.25,17.53C15.58,18.04 14.83,18.46 14,18.7V20.77C15.38,20.45 16.63,19.82 17.68,18.96L19.73,21L21,19.73L12,10.73M19,12C19,12.94 18.8,13.82 18.46,14.64L19.97,16.15C20.62,14.91 21,13.5 21,12C21,7.72 18,4.14 14,3.23V5.29C16.89,6.15 19,8.83 19,12M16.5,12C16.5,10.23 15.5,8.71 14,7.97V10.18L16.45,12.63C16.5,12.43 16.5,12.21 16.5,12Z",
    "weather-hazy": "M12,2L14.39,5.42C13.65,5.15 12.84,5 12,5C11.16,5 10.35,5.15 9.61,5.42L12,2M3.34,7L7.5,6.65C6.9,7.16 6.36,7.78 5.94,8.5C5.5,9.24 5.25,10 5.11,10.79L3.34,7M20.65,7L18.88,10.79C18.74,10 18.47,9.23 18.05,8.5C17.63,7.78 17.1,7.15 16.5,6.64M14,15A1,1 0 0,0 13,14H3A1,1 0 0,0 2,15A1,1 0 0,0 3,16H13A1,1 0 0,0 14,15M22,15A1,1 0 0,0 21,14H17A1,1 0 0,0 16,15A1,1 0 0,0 17,16H21A1,1 0 0,0 22,15M10,19A1,1 0 0,0 11,20H20A1,1 0 0,0 21,19A1,1 0 0,0 20,18H11A1,1 0 0,0 10,19M3,19A1,1 0 0,0 4,20H7A1,1 0 0,0 8,19A1,1 0 0,0 7,18H4A1,1 0 0,0 3,19M12,9A3,3 0 0,1 15,12H17A5,5 0 0,0 12,7A5,5 0 0,0 7,12H9A3,3 0 0,1 12,9Z",
    "alert": "M13 14H11V9H13M13 18H11V16H13M1 21H23L12 2L1 21Z",
    "alert-circle-outline": "M11,15H13V17H11V15M11,7H13V13H11V7M12,2C6.47,2 2,6.5 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20Z",
    "home-thermometer-outline": "M19 8C20.11 8 21 8.9 21 10V16.76C21.61 17.31 22 18.11 22 19C22 20.66 20.66 22 19 22C17.34 22 16 20.66 16 19C16 18.11 16.39 17.31 17 16.76V10C17 8.9 17.9 8 19 8M19 9C18.45 9 18 9.45 18 10V11H20V10C20 9.45 19.55 9 19 9M12 5.69L7 10.19V18H14.1L14 19L14.1 20H5V12H2L12 3L16.4 6.96C15.89 7.4 15.5 7.97 15.25 8.61L12 5.69Z",
    "volume-medium": "M5,9V15H9L14,20V4L9,9M18.5,12C18.5,10.23 17.5,8.71 16,7.97V16C17.5,15.29 18.5,13.76 18.5,12Z",
    "weather-night": "M17.75,4.09L15.22,6.03L16.13,9.09L13.5,7.28L10.87,9.09L11.78,6.03L9.25,4.09L12.44,4L13.5,1L14.56,4L17.75,4.09M21.25,11L19.61,12.25L20.2,14.23L18.5,13.06L16.8,14.23L17.39,12.25L15.75,11L17.81,10.95L18.5,9L19.19,10.95L21.25,11M18.97,15.95C19.8,15.87 20.69,17.05 20.16,17.8C19.84,18.25 19.5,18.67 19.08,19.07C15.17,23 8.84,23 4.94,19.07C1.03,15.17 1.03,8.83 4.94,4.93C5.34,4.53 5.76,4.17 6.21,3.85C6.96,3.32 8.14,4.21 8.06,5.04C7.79,7.9 8.75,10.87 10.95,13.06C13.14,15.26 16.1,16.22 18.97,15.95M17.33,17.97C14.5,17.81 11.7,16.64 9.53,14.5C7.36,12.31 6.2,9.5 6.04,6.68C3.23,9.82 3.34,14.64 6.35,17.66C9.37,20.67 14.19,20.78 17.33,17.97Z",
    "bell": "M21,19V20H3V19L5,17V11C5,7.9 7.03,5.17 10,4.29C10,4.19 10,4.1 10,4A2,2 0 0,1 12,2A2,2 0 0,1 14,4C14,4.1 14,4.19 14,4.29C16.97,5.17 19,7.9 19,11V17L21,19M14,21A2,2 0 0,1 12,23A2,2 0 0,1 10,21",
    "bell-off": "M20.84,22.73L18.11,20H3V19L5,17V11C5,9.86 5.29,8.73 5.83,7.72L1.11,3L2.39,1.73L22.11,21.46L20.84,22.73M19,15.8V11C19,7.9 16.97,5.17 14,4.29C14,4.19 14,4.1 14,4A2,2 0 0,0 12,2A2,2 0 0,0 10,4C10,4.1 10,4.19 10,4.29C9.39,4.47 8.8,4.74 8.26,5.09L19,15.8M12,23A2,2 0 0,0 14,21H10A2,2 0 0,0 12,23Z",
    "air-conditioner": "M6.59,0.66C8.93,-1.15 11.47,1.06 12.04,4.5C12.47,4.5 12.89,4.62 13.27,4.84C13.79,4.24 14.25,3.42 14.07,2.5C13.65,0.35 16.06,-1.39 18.35,1.58C20.16,3.92 17.95,6.46 14.5,7.03C14.5,7.46 14.39,7.89 14.16,8.27C14.76,8.78 15.58,9.24 16.5,9.06C18.63,8.64 20.38,11.04 17.41,13.34C15.07,15.15 12.53,12.94 11.96,9.5C11.53,9.5 11.11,9.37 10.74,9.15C10.22,9.75 9.75,10.58 9.93,11.5C10.35,13.64 7.94,15.39 5.65,12.42C3.83,10.07 6.05,7.53 9.5,6.97C9.5,6.54 9.63,6.12 9.85,5.74C9.25,5.23 8.43,4.76 7.5,4.94C5.37,5.36 3.62,2.96 6.59,0.66M5,16H7A2,2 0 0,1 9,18V24H7V22H5V24H3V18A2,2 0 0,1 5,16M5,18V20H7V18H5M12.93,16H15L12.07,24H10L12.93,16M18,16H21V18H18V22H21V24H18A2,2 0 0,1 16,22V18A2,2 0 0,1 18,16Z",
    "hand-back-right-off": "M20.84 22.73L19.17 21.06C17.7 22.85 15.5 24 13 24C9.74 24 6.81 22 5.6 19L2.57 11.37C2.26 10.58 3 9.79 3.81 10.05L4.6 10.31C5.16 10.5 5.62 10.92 5.84 11.47L7.25 15H8V9.89L1.11 3L2.39 1.73L22.11 21.46L20.84 22.73M14 1.25C14 .56 13.44 0 12.75 0S11.5 .56 11.5 1.25V8.3L14 10.8V1.25M21 16V5.75C21 5.06 20.44 4.5 19.75 4.5S18.5 5.06 18.5 5.75V12H17.5V2.75C17.5 2.06 16.94 1.5 16.25 1.5S15 2.06 15 2.75V11.8L20.83 17.63C20.94 17.11 21 16.56 21 16M10.5 3.25C10.5 2.56 9.94 2 9.25 2S8 2.56 8 3.25V4.8L10.5 7.3V3.25Z",
    "bell-ring-outline": "M10,21H14A2,2 0 0,1 12,23A2,2 0 0,1 10,21M21,19V20H3V19L5,17V11C5,7.9 7.03,5.17 10,4.29C10,4.19 10,4.1 10,4A2,2 0 0,1 12,2A2,2 0 0,1 14,4C14,4.1 14,4.19 14,4.29C16.97,5.17 19,7.9 19,11V17L21,19M17,11A5,5 0 0,0 12,6A5,5 0 0,0 7,11V18H17V11M19.75,3.19L18.33,4.61C20.04,6.3 21,8.6 21,11H23C23,8.07 21.84,5.25 19.75,3.19M1,11H3C3,8.6 3.96,6.3 5.67,4.61L4.25,3.19C2.16,5.25 1,8.07 1,11Z",
    "alarm-snooze": "M7.88,3.39L6.6,1.86L2,5.71L3.29,7.24L7.88,3.39M22,5.72L17.4,1.86L16.11,3.39L20.71,7.25L22,5.72M12,4A9,9 0 0,0 3,13A9,9 0 0,0 12,22A9,9 0 0,0 21,13A9,9 0 0,0 12,4M12,20A7,7 0 0,1 5,13A7,7 0 0,1 12,6A7,7 0 0,1 19,13A7,7 0 0,1 12,20M9,11H12.63L9,15.2V17H15V15H11.37L15,10.8V9H9V11Z",
    "check": "M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z",
    "home-heart": "M2,12L12,3L22,12H19V20H5V12H2M12,18L12.72,17.34C15.3,15 17,13.46 17,11.57C17,10.03 15.79,8.82 14.25,8.82C13.38,8.82 12.55,9.23 12,9.87C11.45,9.23 10.62,8.82 9.75,8.82C8.21,8.82 7,10.03 7,11.57C7,13.46 8.7,15 11.28,17.34L12,18Z",
    "thermometer": "M15 13V5A3 3 0 0 0 9 5V13A5 5 0 1 0 15 13M12 4A1 1 0 0 1 13 5V8H11V5A1 1 0 0 1 12 4Z",
    "water-percent": "M12,3.25C12,3.25 6,10 6,14C6,17.32 8.69,20 12,20A6,6 0 0,0 18,14C18,10 12,3.25 12,3.25M14.47,9.97L15.53,11.03L9.53,17.03L8.47,15.97M9.75,10A1.25,1.25 0 0,1 11,11.25A1.25,1.25 0 0,1 9.75,12.5A1.25,1.25 0 0,1 8.5,11.25A1.25,1.25 0 0,1 9.75,10M14.25,14.5A1.25,1.25 0 0,1 15.5,15.75A1.25,1.25 0 0,1 14.25,17A1.25,1.25 0 0,1 13,15.75A1.25,1.25 0 0,1 14.25,14.5Z",
    "tree-outline": "M10.5,3C8,3 6,5 6,7.5C6,8.11 6.13,8.71 6.37,9.27C5.5,10.12 5,11.28 5,12.5C5,15 7,17 9.5,17C10,17 10.5,16.89 11,16.72V21H13V15.77C13.5,15.91 14,16 14.5,16A5.5,5.5 0 0,0 20,10.5A5.5,5.5 0 0,0 14.5,5C14.41,5 14.33,5 14.24,5C13.41,3.76 12,3 10.5,3M10.5,5C11.82,5 12.91,6.03 13,7.35C13.46,7.12 14,7 14.5,7A3.5,3.5 0 0,1 18,10.5A3.5,3.5 0 0,1 14.5,14C13.54,14 12.63,13.61 11.96,12.91C11.76,14.12 10.72,15 9.5,15A2.5,2.5 0 0,1 7,12.5C7,11.12 7.8,10.54 9,9.79C8.2,8.76 8,8.16 8,7.5A2.5,2.5 0 0,1 10.5,5Z",
    "bell-outline": "M10 21H14C14 22.1 13.1 23 12 23S10 22.1 10 21M21 19V20H3V19L5 17V11C5 7.9 7 5.2 10 4.3V4C10 2.9 10.9 2 12 2S14 2.9 14 4V4.3C17 5.2 19 7.9 19 11V17L21 19M17 11C17 8.2 14.8 6 12 6S7 8.2 7 11V18H17V11Z",
    "bell-cog-outline": "M22.72 19.5C22.74 19.33 22.75 19.17 22.75 19S22.74 18.67 22.72 18.5L23.77 17.68C23.87 17.61 23.89 17.5 23.83 17.36L22.83 15.64C22.77 15.53 22.64 15.5 22.53 15.53L21.28 16C21 15.83 20.75 15.66 20.44 15.54L20.25 14.21C20.23 14.09 20.13 14 20 14H18C17.88 14 17.77 14.09 17.75 14.21L17.57 15.54C17.25 15.66 17 15.83 16.72 16L15.5 15.53C15.37 15.5 15.23 15.53 15.17 15.64L14.17 17.36C14.11 17.5 14.14 17.61 14.23 17.68L15.29 18.5C15.27 18.67 15.25 18.84 15.25 19S15.27 19.33 15.29 19.5L14.23 20.32C14.14 20.39 14.11 20.53 14.17 20.64L15.17 22.37C15.23 22.5 15.37 22.5 15.5 22.5L16.72 21.97C17 22.17 17.25 22.34 17.57 22.47L17.75 23.79C17.77 23.91 17.88 24 18 24H20C20.13 24 20.23 23.91 20.25 23.79L20.44 22.47C20.75 22.34 21 22.17 21.28 21.97L22.53 22.5C22.64 22.5 22.77 22.5 22.83 22.37L23.83 20.64C23.89 20.53 23.87 20.39 23.77 20.32L22.72 19.5M19 20.75C18.04 20.75 17.25 19.97 17.25 19S18.04 17.25 19 17.25 20.75 18.03 20.75 19 19.97 20.75 19 20.75M12.08 20H3V19L5 17V11C5 7.9 7 5.2 10 4.3V4C10 2.9 10.9 2 12 2S14 2.9 14 4V4.3C17 5.2 19 7.9 19 11V12C18.31 12 17.63 12.11 17 12.29V11C17 8.2 14.8 6 12 6S7 8.2 7 11V18H12.08C12.03 18.33 12 18.66 12 19C12 19.34 12.03 19.67 12.08 20M12.3 21C12.5 21.6 12.74 22.17 13.06 22.69C12.75 22.88 12.39 23 12 23C10.9 23 10 22.1 10 21H12.3Z",
    "home-search-outline": "M19.31 18.9C19.75 18.21 20 17.38 20 16.5C20 14 18 12 15.5 12S11 14 11 16.5 13 21 15.5 21C16.37 21 17.19 20.75 17.88 20.32L21 23.39L22.39 22L19.31 18.9M15.5 19C14.12 19 13 17.88 13 16.5S14.12 14 15.5 14 18 15.12 18 16.5 16.88 19 15.5 19M5 20V12H2L12 3L22 12H20.18C19.33 11.11 18.23 10.47 17 10.18L12 5.69L7 10.19V18H9.18C9.35 18.72 9.64 19.39 10.03 20H5Z",
    "chevron-down": "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z",
    "chevron-right": "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",
    "delete-outline": "M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19M8,9H16V19H8V9M15.5,4L14.5,3H9.5L8.5,4H5V6H19V4H15.5Z",
    "arrow-up": "M13,20H11V8L5.5,13.5L4.08,12.08L12,4.16L19.92,12.08L18.5,13.5L13,8V20Z",
    "arrow-down": "M11,4H13V16L18.5,10.5L19.92,11.92L12,19.84L4.08,11.92L5.5,10.5L11,16V4Z",
    "fan": "M12,11A1,1 0 0,0 11,12A1,1 0 0,0 12,13A1,1 0 0,0 13,12A1,1 0 0,0 12,11M12.5,2C17,2 17.11,5.57 14.75,6.75C13.76,7.24 13.32,8.29 13.13,9.22C13.61,9.42 14.03,9.73 14.35,10.13C18.05,8.13 22.03,8.92 22.03,12.5C22.03,17 18.46,17.1 17.28,14.73C16.78,13.74 15.72,13.3 14.79,13.11C14.59,13.59 14.28,14 13.88,14.34C15.87,18.03 15.08,22 11.5,22C7,22 6.91,18.42 9.27,17.24C10.25,16.75 10.69,15.71 10.89,14.79C10.4,14.59 9.97,14.27 9.65,13.87C5.96,15.85 2,15.07 2,11.5C2,7 5.56,6.89 6.74,9.26C7.24,10.25 8.29,10.68 9.22,10.87C9.41,10.39 9.73,9.97 10.14,9.65C8.15,5.96 8.94,2 12.5,2Z",
    "air-purifier": "M11,9A4,4 0 0,1 15,13A4,4 0 0,1 11,17A4,4 0 0,1 7,13A4,4 0 0,1 11,9M11,11A2,2 0 0,0 9,13A2,2 0 0,0 11,15A2,2 0 0,0 13,13A2,2 0 0,0 11,11M7,4H14A4,4 0 0,1 18,8V9H16V8A2,2 0 0,0 14,6H7A2,2 0 0,0 5,8V20H16V18H18V22H3V8A4,4 0 0,1 7,4M16,11C18.5,11 18.5,9 21,9V11C18.5,11 18.5,13 16,13V11M16,15C18.5,15 18.5,13 21,13V15C18.5,15 18.5,17 16,17V15Z",
    "close": "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
    "menu-down": "M7,10L12,15L17,10H7Z",
    "playlist-plus": "M3 16H10V14H3M18 14V10H16V14H12V16H16V20H18V16H22V14M14 6H3V8H14M14 10H3V12H14V10Z",
    "home": "M10,20V14H14V20H19V12H22L12,3L2,12H5V20H10Z",
    "account-box": "M6,17C6,15 10,13.9 12,13.9C14,13.9 18,15 18,17V18H6M15,9A3,3 0 0,1 12,12A3,3 0 0,1 9,9A3,3 0 0,1 12,6A3,3 0 0,1 15,9M3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5A2,2 0 0,0 19,3H5C3.89,3 3,3.9 3,5Z",
    "format-list-bulleted-type": "M5,9.5L7.5,14H2.5L5,9.5M3,4H7V8H3V4M5,20A2,2 0 0,0 7,18A2,2 0 0,0 5,16A2,2 0 0,0 3,18A2,2 0 0,0 5,20M9,5V7H21V5H9M9,19H21V17H9V19M9,13H21V11H9V13Z",
    "chart-box": "M19 3H5C3.9 3 3 3.9 3 5V19C3 20.1 3.9 21 5 21H19C20.1 21 21 20.1 21 19V5C21 3.9 20.1 3 19 3M9 17H7V10H9V17M13 17H11V7H13V17M17 17H15V13H17V17Z",
    "home-thermometer": "M19 8C20.11 8 21 8.9 21 10V16.76C21.61 17.31 22 18.11 22 19C22 20.66 20.66 22 19 22C17.34 22 16 20.66 16 19C16 18.11 16.39 17.31 17 16.76V10C17 8.9 17.9 8 19 8M19 9C18.45 9 18 9.45 18 10V11H20V10C20 9.45 19.55 9 19 9M5 20V12H2L12 3L16.4 6.96C15.54 7.69 15 8.78 15 10V16C14.37 16.83 14 17.87 14 19L14.1 20H5Z",
    "clipboard-list": "M19 3H14.82C14.4 1.84 13.3 1 12 1S9.6 1.84 9.18 3H5C3.9 3 3 3.9 3 5V19C3 20.1 3.9 21 5 21H19C20.1 21 21 20.1 21 19V5C21 3.9 20.1 3 19 3M7 8H9V12H8V9H7V8M10 17V18H7V17.08L9 15H7V14H9.25C9.66 14 10 14.34 10 14.75C10 14.95 9.92 15.14 9.79 15.27L8.12 17H10M11 4C11 3.45 11.45 3 12 3S13 3.45 13 4 12.55 5 12 5 11 4.55 11 4M17 17H12V15H17V17M17 11H12V9H17V11Z",
    "cog": "M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.21,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.21,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.67 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z",
    "menu-open": "M21,15.61L19.59,17L14.58,12L19.59,7L21,8.39L17.44,12L21,15.61M3,6H16V8H3V6M3,13V11H13V13H3M3,18V16H16V18H3Z",
    "window-closed": "M6,11H10V9H14V11H18V4H6V11M18,13H6V20H18V13M6,2H18A2,2 0 0,1 20,4V20A2,2 0 0,1 18,22H6A2,2 0 0,1 4,20V4A2,2 0 0,1 6,2Z",
    "air-filter": "M19,18.31V20A2,2 0 0,1 17,22H7A2,2 0 0,1 5,20V16.3C4.54,16.12 3.95,16 3,16A1,1 0 0,1 2,15A1,1 0 0,1 3,14C3.82,14 4.47,14.08 5,14.21V12.3C4.54,12.12 3.95,12 3,12A1,1 0 0,1 2,11A1,1 0 0,1 3,10C3.82,10 4.47,10.08 5,10.21V8.3C4.54,8.12 3.95,8 3,8A1,1 0 0,1 2,7A1,1 0 0,1 3,6C3.82,6 4.47,6.08 5,6.21V4A2,2 0 0,1 7,2H17A2,2 0 0,1 19,4V6.16C20.78,6.47 21.54,7.13 21.71,7.29C22.1,7.68 22.1,8.32 21.71,8.71C21.32,9.1 20.8,9.09 20.29,8.71V8.71C20.29,8.71 19.25,8 17,8C15.74,8 14.91,8.41 13.95,8.9C12.91,9.41 11.74,10 10,10C9.64,10 9.31,10 9,9.96V7.95C9.3,8 9.63,8 10,8C11.26,8 12.09,7.59 13.05,7.11C14.09,6.59 15.27,6 17,6V4H7V20H17V18C18.5,18 18.97,18.29 19,18.31M17,10C15.27,10 14.09,10.59 13.05,11.11C12.09,11.59 11.26,12 10,12C9.63,12 9.3,12 9,11.95V13.96C9.31,14 9.64,14 10,14C11.74,14 12.91,13.41 13.95,12.9C14.91,12.42 15.74,12 17,12C19.25,12 20.29,12.71 20.29,12.71V12.71C20.8,13.1 21.32,13.1 21.71,12.71C22.1,12.32 22.1,11.69 21.71,11.29C21.5,11.08 20.25,10 17,10M17,14C15.27,14 14.09,14.59 13.05,15.11C12.09,15.59 11.26,16 10,16C9.63,16 9.3,16 9,15.95V17.96C9.31,18 9.64,18 10,18C11.74,18 12.91,17.41 13.95,16.9C14.91,16.42 15.74,16 17,16C19.25,16 20.29,16.71 20.29,16.71V16.71C20.8,17.1 21.32,17.1 21.71,16.71C22.1,16.32 22.1,15.69 21.71,15.29C21.5,15.08 20.25,14 17,14Z",
    "ear-hearing": "M17,20C16.71,20 16.44,19.94 16.24,19.85C15.53,19.5 15.03,18.97 14.53,17.47C14,15.91 13.06,15.18 12.14,14.47C11.35,13.86 10.53,13.23 9.82,11.94C9.29,11 9,9.93 9,9C9,6.2 11.2,4 14,4C16.8,4 19,6.2 19,9H21C21,5.07 17.93,2 14,2C10.07,2 7,5.07 7,9C7,10.26 7.38,11.65 8.07,12.9C9,14.55 10.05,15.38 10.92,16.05C11.73,16.67 12.31,17.12 12.63,18.1C13.23,19.92 14,20.94 15.36,21.65C15.87,21.88 16.43,22 17,22A4,4 0 0,0 21,18H19A2,2 0 0,1 17,20M7.64,2.64L6.22,1.22C4.23,3.21 3,5.96 3,9C3,12.04 4.23,14.79 6.22,16.78L7.63,15.37C6,13.74 5,11.5 5,9C5,6.5 6,4.26 7.64,2.64M11.5,9A2.5,2.5 0 0,0 14,11.5A2.5,2.5 0 0,0 16.5,9A2.5,2.5 0 0,0 14,6.5A2.5,2.5 0 0,0 11.5,9Z",
}

# Minimal stand-ins for Home Assistant's <ha-icon>, <ha-menu-button> and <ha-form>. ha-form renders each field the
# way Home Assistant draws it (filled text fields, entity pickers with their "Add entity" button, toggles, closed
# expandable sections); nothing is editable.
HA_ELEMENTS = (
    "const ICONS = "
    + json.dumps(ICONS)
    + ";"
    + r"""
const svg = (name, size = 24) =>
  `<svg viewBox="0 0 24 24" style="width:${size}px;height:${size}px;fill:currentColor;display:block"><path d="${ICONS[(name || "").replace("mdi:", "")] || ""}"/></svg>`;
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

customElements.define("ha-icon", class extends HTMLElement {
  static get observedAttributes() { return ["icon"]; }
  set icon(value) { this._icon = value; this._draw(); }
  get icon() { return this._icon; }
  connectedCallback() { this._draw(); }
  attributeChangedCallback(_, __, value) { this._icon = value; this._draw(); }
  _draw() {
    this.style.display = "inline-flex";
    this.style.flex = "none";
    this.innerHTML = '<svg viewBox="0 0 24 24" style="width:var(--mdc-icon-size,24px);height:var(--mdc-icon-size,24px);fill:currentColor"><path d="' +
      (ICONS[(this._icon || "").replace("mdi:", "")] || "") + '"/></svg>';
  }
});

customElements.define("ha-menu-button", class extends HTMLElement {});

const FORM_STYLE = `
  :host { display: block; color: var(--primary-text-color); font-size: 14px; }
  .fields { display: flex; flex-direction: column; gap: 24px; }
  .label { margin: 0 0 8px; }
  .field { position: relative; display: flex; align-items: center; gap: 12px; min-height: 56px; padding: 0 12px 0 16px;
    box-sizing: border-box; background: var(--input-fill-color); border-radius: 4px 4px 0 0;
    border-bottom: 1px solid var(--input-line-color); }
  .field + .field { margin-top: 8px; }
  .field .text { flex: 1; min-width: 0; display: flex; flex-direction: column; justify-content: center; }
  .field .small { font-size: 12px; color: var(--secondary-text-color); line-height: 16px; }
  .field .value { font-size: 16px; line-height: 22px; }
  .field .placeholder { color: var(--secondary-text-color); font-size: 14px; }
  .field .name { font-size: 14px; line-height: 20px; }
  .field .unit { color: var(--secondary-text-color); font-size: 14px; }
  .field .icon { color: var(--secondary-text-color); display: flex; }
  .field .end { display: flex; align-items: center; gap: 8px; color: var(--secondary-text-color); }
  .helper { font-size: 12px; color: var(--secondary-text-color); padding: 4px 16px 0; }
  .add { display: inline-flex; align-items: center; gap: 6px; margin-top: 8px; padding: 6px 14px 6px 10px; border-radius: 18px;
    background: rgba(var(--rgb-primary-color), 0.12); color: var(--primary-color); font-weight: 500; }
  .boolean { display: flex; align-items: center; justify-content: space-between; min-height: 40px; }
  .switch { position: relative; width: 36px; height: 14px; border-radius: 7px; background: var(--switch-off-track); margin-right: 4px; }
  .switch::after { content: ""; position: absolute; top: -3px; left: -3px; width: 20px; height: 20px; border-radius: 50%;
    background: var(--switch-off-thumb); box-shadow: 0 1px 3px rgba(0,0,0,.4); }
  .switch.on { background: rgba(var(--rgb-primary-color), 0.5); }
  .switch.on::after { left: 19px; background: var(--primary-color); }
  .slider { display: flex; align-items: center; gap: 16px; }
  .slider .track { flex: 1; height: 4px; border-radius: 2px; background: rgba(var(--rgb-primary-color), 0.3); position: relative; }
  .slider .fill { position: absolute; inset: 0 auto 0 0; background: var(--primary-color); border-radius: 2px; }
  .expandable { border: 1px solid var(--divider-color); border-radius: 8px; display: flex; align-items: center; gap: 12px;
    min-height: 48px; padding: 0 12px; font-weight: 500; }
  .expandable .title { flex: 1; }
  .expandable .icon { display: flex; color: var(--primary-text-color); }
  .expanded { border: 1px solid var(--divider-color); border-radius: 8px; }
  .expanded .expandable { border: none; }
  .fields.inner { padding: 8px 12px 16px; }
`;

customElements.define("ha-form", class extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }
  set hass(v) { this._hass = v; this._queue(); }
  set schema(v) { this._schema = v; this._queue(); }
  set data(v) { this._data = v; this._queue(); }
  set computeLabel(v) { this._label = v; this._queue(); }
  set computeHelper(v) { this._helperFn = v; this._queue(); }
  _queue() {
    if (this._pending) return;
    this._pending = true;
    queueMicrotask(() => { this._pending = false; this._render(); });
  }
  _render() {
    if (!this._schema) return;
    const data = this._data || {};
    this.shadowRoot.innerHTML = `<style>${FORM_STYLE}</style><div class="fields">${this._schema.map((s) => this._field(s, data)).join("")}</div>`;
  }
  _labelOf(s) { return this._label ? this._label(s) : s.name; }
  _field(s, data) {
    if (s.type === "grid") {
      return `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(${s.column_min_width || "200px"},1fr));gap:8px 12px">${s.schema.map((c) => this._field(c, data)).join("")}</div>`;
    }
    if (s.type === "expandable" && s.expanded) {
      const inner = s.flatten ? data : data[s.name] || {};
      const icon = s.icon ? `<span class="icon">${svg(s.icon)}</span>` : "";
      return `<div class="expanded"><div class="expandable open">${icon}<span class="title">${esc(this._labelOf(s))}</span>${svg("chevron-up")}</div><div class="fields inner">${s.schema.map((c) => this._field(c, inner)).join("")}</div></div>`;
    }
    if (s.type === "expandable") {
      const icon = s.icon ? `<span class="icon">${svg(s.icon)}</span>` : "";
      return `<div class="expandable">${icon}<span class="title">${esc(this._labelOf(s))}</span>${svg("chevron-down")}</div>`;
    }
    const sel = s.selector || {};
    const value = data[s.name];
    const label = esc(this._labelOf(s)) + (s.required ? "*" : "");
    const helpText = this._helperFn ? this._helperFn(s) : undefined;
    const help = helpText ? `<div class="helper">${esc(helpText)}</div>` : "";
    if (sel.boolean) {
      return `<div class="boolean"><span>${label}</span><span class="switch${value ? " on" : ""}"></span></div>`;
    }
    if (sel.entity) {
      const ids = (Array.isArray(value) ? value : value ? [value] : []).filter(Boolean);
      const multiple = sel.entity.multiple;
      const rows = ids.map((id) => this._entity(id)).join("");
      const empty = !ids.length && !multiple
        ? `<div class="field"><div class="text"><span class="placeholder">Select an entity</span></div><span class="end">${svg("menu-down")}</span></div>`
        : "";
      const add = multiple ? `<div><span class="add">${svg("playlist-plus", 20)}Add entity</span></div>` : "";
      return `<div><div class="label">${label}</div>${rows}${empty}${add}${help}</div>`;
    }
    if (sel.number && sel.number.mode === "slider") {
      const { min = 0, max = 100 } = sel.number;
      const v = typeof value === "number" ? value : min;
      return `<div><div class="label">${label}</div><div class="slider"><div class="track"><div class="fill" style="width:${((v - min) / (max - min)) * 100}%"></div></div><span>${esc(value ?? "")}</span></div>${help}</div>`;
    }
    if (sel.select) {
      const options = (sel.select.options || []).map((o) => (typeof o === "string" ? { value: o, label: o } : o));
      const shown = (Array.isArray(value) ? value : [value]).filter((v) => v !== undefined && v !== null && v !== "");
      const text = shown.map((v) => options.find((o) => o.value === v)?.label ?? v).join(", ");
      const clear = shown.length ? svg("close", 20) : "";
      return `<div><div class="field"><div class="text"><span class="small">${label}</span><span class="value">${esc(text)}</span></div><span class="end">${clear}${svg("menu-down")}</span></div>${help}</div>`;
    }
    const unit = sel.number?.unit_of_measurement ? `<span class="unit">${esc(sel.number.unit_of_measurement)}</span>` : "";
    return `<div><div class="field"><div class="text"><span class="small">${label}</span><span class="value">${esc(value ?? "")}</span></div>${unit}</div>${help}</div>`;
  }
  _entity(id) {
    const state = this._hass?.states?.[id];
    const name = state?.attributes?.friendly_name || id;
    const icon = state?.attributes?.icon || "mdi:alert";
    const areaId = this._hass?.entities?.[id]?.area_id;
    const area = areaId ? this._hass.areas?.[areaId]?.name : "";
    const second = area ? `<span class="small">${esc(area)}</span>` : "";
    return `<div class="field"><span class="icon">${svg(icon)}</span><div class="text"><span class="name">${esc(name)}</span>${second}</div><span class="end">${svg("close", 20)}${svg("menu-down")}</span></div>`;
  }
});
"""
)

# The page around the panel: Home Assistant's sidebar, static.
SIDEBAR = [
    ("home", "Overview"),
    ("account-box", "Map"),
    ("format-list-bulleted-type", "Activity"),
    ("chart-box", "History"),
    ("home-thermometer", "Smart Comfort"),
    ("clipboard-list", "To-do lists"),
]
SIDEBAR_BOTTOM = [("cog", "Settings"), ("bell", "Notifications")]


def sidebar_html():
    def item(icon, label):
        selected = " selected" if label == "Smart Comfort" else ""
        return f'<div class="item{selected}"><ha-icon icon="mdi:{icon}"></ha-icon><span>{label}</span></div>'

    return (
        '<aside class="sidebar"><div class="brand"><ha-icon icon="mdi:menu-open"></ha-icon>Home Assistant</div>'
        + "".join(item(*i) for i in SIDEBAR)
        + '<div class="spacer"></div>'
        + "".join(item(*i) for i in SIDEBAR_BOTTOM)
        + '<div class="item user"><span class="avatar">A</span><span>Admin</span></div></aside>'
    )


def page_html(theme):
    variables = "".join(f"{k}:{v};" for k, v in {**THEMES[theme], **COMMON}.items())
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
:root {{ {variables} color-scheme: {theme}; }}
html, body {{ margin: 0; background: var(--primary-background-color); color: var(--primary-text-color);
             font-family: Roboto, "Segoe UI", Helvetica, Arial, sans-serif; }}
.sidebar {{ position: fixed; inset: 0 auto 0 0; width: 256px; box-sizing: border-box; display: flex; flex-direction: column;
           background: var(--sidebar-background-color); border-right: 1px solid var(--divider-color); padding: 0 4px 4px; }}
.brand {{ display: flex; align-items: center; gap: 18px; height: 56px; margin: 0 -4px 4px; padding: 0 16px; font-size: 20px;
         border-bottom: 1px solid var(--divider-color); }}
.brand ha-icon {{ color: var(--sidebar-icon-color); --mdc-icon-size: 20px; }}
.item {{ display: flex; align-items: center; gap: 20px; height: 40px; padding: 0 12px; margin: 4px 0; border-radius: 4px;
        font-size: 14px; font-weight: 500; }}
.item ha-icon {{ color: var(--sidebar-icon-color); }}
.item.selected {{ background: rgba(var(--rgb-primary-color), 0.12); color: var(--primary-color); }}
.item.selected ha-icon {{ color: var(--primary-color); }}
.spacer {{ flex: 1; }}
.avatar {{ width: 40px; height: 40px; margin-left: -8px; margin-right: -8px; border-radius: 50%; display: flex; align-items: center;
          justify-content: center; background: rgba(var(--rgb-primary-color), 0.3); font-size: 14px; font-weight: 400; }}
main {{ margin-left: 256px; }}
</style></head><body>{sidebar_html()}<main id="root"></main></body></html>"""


# Mock Home Assistant: the entities of the rooms (friendly name, icon, area), the switches of the integration.
ENTITIES = {
    "sensor.living_room_temperature": ("Living room temperature", "mdi:thermometer", "living_room", "27.8"),
    "sensor.living_room_co2": ("Living room CO2", "mdi:molecule-co2", "living_room", "1380"),
    "binary_sensor.living_room_window": ("Living room window", "mdi:window-closed", "living_room", "off"),
    "climate.living_room_ac": ("Living room AC", "mdi:air-conditioner", "living_room", "cool"),
    "fan.living_room_fan": ("Living room fan", "mdi:fan", "living_room", "on"),
    "light.living_room": ("Living room ceiling", "mdi:ceiling-light", "living_room", "on"),
    "light.sofa": ("Sofa lamp", "mdi:floor-lamp", "living_room", "on"),
    "sensor.bedroom_temperature": ("Bedroom temperature", "mdi:thermometer", "bedroom", "21.3"),
    "sensor.bedroom_noise": ("Bedroom noise", "mdi:volume-medium", "bedroom", "64"),
    "binary_sensor.bedroom_window": ("Bedroom window", "mdi:window-closed", "bedroom", "on"),
    "fan.bedroom_purifier": ("Bedroom purifier", "mdi:air-purifier", "bedroom", "on"),
    "light.bedroom_purifier_indicator": ("Bedroom purifier indicator", "mdi:led-on", "bedroom", "on"),
    "light.bedroom": ("Bedroom lamp", "mdi:lamp", "bedroom", "on"),
    "light.bedroom_night_light": ("Bedroom night light", "mdi:lightbulb-night", "bedroom", "off"),
    "sensor.bathroom_humidity": ("Bathroom humidity", "mdi:water-percent", "bathroom", "64"),
    "sensor.office_temperature": ("Office temperature", "mdi:thermometer", "office", "16.2"),
    "light.entrance": ("Entrance", "mdi:ceiling-light", "entrance", "off"),
    "light.hallway": ("Hallway", "mdi:ceiling-light", "entrance", "off"),
    "binary_sensor.entrance_presence": ("Entrance presence", "mdi:motion-sensor", "entrance", "off"),
    "sensor.entrance_light_level": ("Entrance light level", "mdi:brightness-5", "entrance", "3"),
    "sensor.garden_temperature": ("Outdoor temperature", "mdi:thermometer", "garden", "22.4"),
    "sensor.garden_air_quality": ("Garden air quality", "mdi:air-filter", "garden", "4"),
    "sensor.street_noise": ("Street noise", "mdi:ear-hearing", "garden", "71"),
}
AREAS = {
    "living_room": "Living Room",
    "bedroom": "Bedroom",
    "bathroom": "Bathroom",
    "office": "Office",
    "entrance": "Entrance",
    "garden": "Garden",
}

ROOMS = {
    "Living Room": {
        "temperature": "sensor.living_room_temperature",
        "co2": "sensor.living_room_co2",
        "openings": ["binary_sensor.living_room_window"],
        "climate": "climate.living_room_ac",
        "fans": ["fan.living_room_fan"],
        "lights": ["light.living_room", "light.sofa"],
    },
    "Bedroom": {
        "temperature": "sensor.bedroom_temperature",
        "noise": "sensor.bedroom_noise",
        "openings": ["binary_sensor.bedroom_window"],
        "purifiers": [
            {
                "entity_id": "fan.bedroom_purifier",
                "closed_preset": "auto",
                "night_preset": "sleep",
                "display": "light.bedroom_purifier_indicator",
                "reset_at": "20:40:00",
            }
        ],
        "lights": ["light.bedroom", {"entity_id": "light.bedroom_night_light", "night_only": True}],
        "lighting": {"quiet_morning": True},
        "naps": [{"start": "13:30:00", "end": "15:30:00", "days": ["sat", "sun"]}],
    },
    "Bathroom": {"humidity": "sensor.bathroom_humidity"},
    "Office": {"temperature": "sensor.office_temperature"},
    "Entrance": {
        "lights": ["light.entrance"],
        "presence": {
            "sensors": ["binary_sensor.entrance_presence"],
            "lights": ["light.entrance", "light.hallway"],
            "lux": "sensor.entrance_light_level",
            "max_lux": 10,
            "not_during_naps": ["light.hallway"],
            "slots": [
                {"start": "06:30:00", "end": "08:00:00", "days": ["mon", "tue", "wed", "thu", "fri"], "off": True},
                {"start": "20:00:00", "end": "09:00:00", "lights": ["light.entrance"], "brightness": 20},
            ],
        },
    },
}
GARDEN = {
    "name": "Garden",
    "temperature": ["sensor.garden_temperature"],
    "air_quality": ["sensor.garden_air_quality"],
    "noise": ["sensor.street_noise"],
}


def rooms(order):
    return [{"name": name, **ROOMS[name]} for name in order]


# Saved: the rooms in the order the user set. Discovered: the areas in alphabetical order.
SAVED = {
    "rooms": rooms(["Living Room", "Bedroom", "Bathroom", "Office", "Entrance"]),
    "outdoors": [GARDEN],
    "quiet_start": "22:30:00",
    "quiet_end": "08:00:00",
    "control": {"display_off": "20:00:00", "display_on": "10:00:00"},
}
DISCOVERED = {"rooms": rooms(["Bathroom", "Bedroom", "Living Room", "Office"]), "outdoors": [GARDEN]}
REPORT = {
    "added": ["Bathroom", "Bedroom", "Living Room", "Office"],
    "updated": [],
    "outdoors_added": ["Garden"],
    "outdoors_updated": [],
    "outdoor": [],
    "outdoor_noise": [],
    "outdoor_air": [],
}


def alert(room, name, kind, value, *, temperature=None, handled=False):
    return {
        "room": room,
        "room_name": name,
        "kind": kind,
        "value": value,
        "temperature": temperature,
        "since": "2026-10-24T11:38:00+00:00",
        "notified_at": None,
        "snoozed": False,
        "acknowledged": False,
        "handled": handled,
        "openings": [],
    }


def room_status(name, alerts, devices=None, lights=None, **values):
    reading = {"temperature": None, "co2": None, "humidity": None, "noise": None, "open": []}
    return {
        "name": name,
        **reading,
        **values,
        "alerts": alerts,
        "handled": False,
        "devices": devices or {},
        "lights": lights or {},
    }


STATUS = {
    "alerts": [
        alert("bedroom", "Bedroom", "bad_air_outside", 4),
        alert("living_room", "Living Room", "too_hot", 27.8, handled=True),
        alert("living_room", "Living Room", "co2_high", 1380),
        alert("office", "Office", "too_cold", 16.2),
    ],
    "snoozes": {},
    "outdoor_temperature": 22.4,
    "outdoor_noise": 71,
    "outdoor_air": 4,
    "night": True,
    "rooms": [
        room_status(
            "Living Room",
            ["too_hot", "co2_high"],
            {"climate.living_room_ac": {"target": "cool"}, "fan.living_room_fan": {"target": "on"}},
            {"light.living_room": {"target": "100 % · 4000 K"}, "light.sofa": {"target": "100 %"}},
            temperature=27.8,
            co2=1380,
        ),
        room_status(
            "Bedroom",
            ["bad_air_outside"],
            {"fan.bedroom_purifier": {"target": "boost"}},
            {"light.bedroom": {"target": "40 % · 3000 K"}, "light.bedroom_night_light": {"target": None}},
            temperature=21.3,
            noise=64,
            open=["binary_sensor.bedroom_window"],
        ),
        room_status("Bathroom", [], humidity=64),
        room_status("Office", ["too_cold"], temperature=16.2),
        room_status("Entrance", [], None, {"light.entrance": {"target": None}}),
    ],
    "outdoors": [
        {
            "name": "Garden",
            "temperature": 22.4,
            "air_quality": 4,
            "noise": 71,
            "sensors": [*GARDEN["temperature"], *GARDEN["air_quality"], *GARDEN["noise"]],
        }
    ],
    "notifications_enabled": True,
    "control_enabled": True,
    "lighting_enabled": True,
    "lighting_phase": "day",
    "last_notification": None,
}

# Nothing set up yet: no room, nothing measured, the last notification of an earlier setup.
START_STATUS = {
    **STATUS,
    "alerts": [],
    "outdoor_temperature": None,
    "outdoor_noise": None,
    "outdoor_air": None,
    "rooms": [],
    "outdoors": [],
    "last_notification": {
        "title": "3 comfort alerts",
        "message": "Bedroom: outdoor air quality 4/6, close the Bedroom window\nLiving Room: 27.8 °C, too hot\n"
        "Office: 16.2 °C, too cold",
        "at": "2026-10-24T09:12:00+00:00",
    },
}


def flatten(tree, prefix):
    out = {}
    for key, value in tree.items():
        if isinstance(value, dict):
            out.update(flatten(value, f"{prefix}.{key}"))
        else:
            out[f"{prefix}.{key}"] = value
    return out


def config(options):
    return {
        "entry_id": "mock",
        "loaded": True,
        "yaml": True,
        "options": options,
        "defaults": {
            "general": {
                "outdoor_aggregate": "min",
                "digest_window": const.DEFAULT_DIGEST_WINDOW,
                "reminder": const.DEFAULT_REMINDER,
                "snooze_duration": const.DEFAULT_SNOOZE,
                "startup_grace": const.DEFAULT_STARTUP_GRACE,
                "clear_when_resolved": True,
                "critical_volume": const.DEFAULT_CRITICAL_VOLUME,
                "tag": const.DEFAULT_TAG,
            },
            "alerts": const.DEFAULT_ALERTS,
            "control": const.DEFAULT_CONTROL,
            "lighting": const.DEFAULT_LIGHTING,
        },
        "kinds": list(const.KINDS),
        "severities": list(const.SEVERITIES),
        "aggregates": list(const.AGGREGATES),
    }


def mock(options, status):
    states = {
        entity_id: {
            "entity_id": entity_id,
            "state": state,
            "attributes": {"friendly_name": name, "icon": icon},
        }
        for entity_id, (name, icon, _, state) in ENTITIES.items()
    }
    states["climate.living_room_ac"]["attributes"]["fan_modes"] = ["auto", "low", "medium", "high"]
    states["fan.bedroom_purifier"]["attributes"]["preset_modes"] = ["auto", "sleep", "boost"]
    for light in ("light.living_room", "light.sofa", "light.bedroom", "light.bedroom_night_light"):
        states[light]["attributes"]["supported_color_modes"] = ["color_temp"]
    entities = {entity_id: {"entity_id": entity_id, "area_id": area} for entity_id, (_, _, area, _) in ENTITIES.items()}
    for key in ("notifications", "device_control", "adaptive_lighting"):
        entity_id = f"switch.smart_comfort_{key}"
        entities[entity_id] = {"entity_id": entity_id, "platform": DOMAIN, "translation_key": key}
    return {
        "states": states,
        "entities": entities,
        "areas": {area_id: {"area_id": area_id, "name": name} for area_id, name in AREAS.items()},
        "services": {"notify": {"mobile_app_phone": {}}},
        "language": "en",
        "config": config(options),
        "status": status,
        "discover": {"options": DISCOVERED, "report": REPORT},
        "translations": {
            "options": flatten(TRANSLATIONS["options"], f"component.{DOMAIN}.options"),
            "selector": flatten(TRANSLATIONS["selector"], f"component.{DOMAIN}.selector"),
        },
    }


# Mounts the panel the way Home Assistant does (panel, narrow, route, then hass); the WebSocket commands answer with
# the mock data. Resolves once the tab is rendered (and, on the overview, the status received).
MOUNT = """async ([data, tab]) => {
    const el = document.createElement("smart-comfort-panel");
    const pretty = (s) => s.charAt(0).toUpperCase() + s.slice(1);
    const hass = {
        states: data.states, entities: data.entities, areas: data.areas, services: data.services,
        language: data.language, locale: { language: data.language },
        formatEntityState: (state) => pretty(state.state),
        callService: async () => {},
        callWS: async (msg) => {
            if (msg.type === "frontend/get_translations") return { resources: data.translations[msg.category] };
            if (msg.type === "smart_comfort/config") return structuredClone(data.config);
            if (msg.type === "smart_comfort/discover") return structuredClone(data.discover);
            throw new Error(`unexpected ${msg.type}`);
        },
        connection: {
            subscribeMessage: (callback) => {
                setTimeout(() => callback({ status: data.status }), 0);
                return Promise.resolve(() => {});
            },
        },
    };
    el.panel = { url_path: "smart-comfort" };
    el.narrow = false;
    el.route = { path: tab === "overview" ? "" : `/${tab}` };
    el.hass = hass;
    document.getElementById("root").appendChild(el);
    for (let i = 0; i < 100; i++) {
        await new Promise((r) => setTimeout(r, 20));
        const content = el.shadowRoot.querySelector(".content");
        if (content && content.children.length && !content.querySelector(".banner:only-child")) break;
    }
}"""

# Clicks a button of the panel by its text (and waits for what it starts to render).
CLICK = """async ([selector, text]) => {
    const root = document.querySelector("smart-comfort-panel").shadowRoot;
    const all = [...root.querySelectorAll(selector)];
    // Exactly the text, or starting with it (a section line also shows its summary).
    const target = all.find((b) => b.textContent.trim() === text) || all.find((b) => b.textContent.trim().startsWith(text));
    if (!target) throw new Error(`no ${selector} "${text}"`);
    target.click();
    await new Promise((r) => setTimeout(r, 200));
}"""

# Scrolls the page so the element sits just under the sticky toolbar and tabs.
SCROLL = """([selector, text]) => {
    const root = document.querySelector("smart-comfort-panel").shadowRoot;
    const all = [...root.querySelectorAll(selector)];
    const target = all.find((b) => b.textContent.trim() === text) || all.find((b) => b.textContent.trim().startsWith(text));
    const bar = root.querySelector(".toolbar").offsetHeight + root.querySelector(".tabs").offsetHeight;
    window.scrollTo(0, target.getBoundingClientRect().top + window.scrollY - bar - 10);
}"""

# Each state of the README: the saved options or none, the tab, the clicks after loading, the page height.
SHOTS = [
    {"file": "panel-overview", "options": SAVED, "status": STATUS, "tab": "overview", "height": 900},
    {"file": "panel-start", "options": {}, "status": START_STATUS, "tab": "overview", "height": 600},
    {
        "file": "panel-discover",
        "options": {},
        "status": START_STATUS,
        "tab": "overview",
        "clicks": [(".discover .btn", "Discover")],
        "height": 900,
    },
    {
        "file": "panel-room",
        "options": SAVED,
        "status": STATUS,
        "tab": "rooms",
        "clicks": [(".room-toggle", "Living Room"), (".section-head", "Sensors"), (".section-head", "Devices")],
        "height": 1300,
    },
    {
        "file": "panel-naps",
        "options": SAVED,
        "status": STATUS,
        "tab": "rooms",
        "clicks": [(".room-toggle", "Bedroom"), (".section-head", "Lighting")],
        "scroll": (".section-head", "Lighting"),
        "height": 900,
    },
    {
        "file": "panel-outdoors",
        "options": SAVED,
        "status": STATUS,
        "tab": "outdoors",
        "clicks": [(".room-toggle", "Garden")],
        "height": 1100,
    },
    {
        "file": "panel-alerts",
        "options": SAVED,
        "status": STATUS,
        "tab": "alerts",
        "clicks": [(".section-head", "Too hot")],
        "height": 1100,
    },
    {
        "file": "panel-presence",
        "options": SAVED,
        "status": STATUS,
        "tab": "rooms",
        "clicks": [(".room-toggle", "Entrance"), (".section-head", "Lighting")],
        "scroll": (".subheader", "Lights on presence"),
        "height": 1300,
    },
    {"file": "panel-schedule", "options": SAVED, "status": STATUS, "tab": "schedule", "height": 1100},
    {"file": "panel-yaml", "options": SAVED, "status": STATUS, "tab": "yaml_tab", "height": 1100},
    {
        "file": "panel-lighting",
        "options": SAVED,
        "status": STATUS,
        "tab": "settings",
        "scroll": (".card-header", "Adaptive lighting"),
        "height": 900,
    },
]


def render(browser, shot, theme):
    name = shot["file"] + ("-dark" if theme == "dark" else "")
    context = browser.new_context(
        viewport={"width": WIDTH, "height": shot["height"]},
        device_scale_factor=1,
        timezone_id="UTC",
        locale="en-US",
        color_scheme=theme,
    )
    page = context.new_page()
    page.on("pageerror", lambda err: print(f"{name}: page error: {err}"))
    page.clock.set_fixed_time(NOW)
    # A real origin, so the panel can change the URL when it switches tabs.
    page.route(
        "http://homeassistant.local/**", lambda route: route.fulfill(content_type="text/html", body=page_html(theme))
    )
    page.goto(URL)
    page.add_script_tag(content=HA_ELEMENTS)
    page.add_script_tag(content=PANEL_JS)
    page.evaluate(MOUNT, [mock(shot["options"], shot["status"]), shot["tab"]])
    for click in shot.get("clicks", []):
        page.evaluate(CLICK, list(click))
    if "scroll" in shot:
        page.evaluate(SCROLL, list(shot["scroll"]))
    page.wait_for_timeout(200)
    path = ROOT / "screenshots" / f"{name}.png"
    page.screenshot(path=str(path), animations="disabled")
    print(path.relative_to(ROOT))
    context.close()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        for shot in SHOTS:
            for theme in THEMES:
                render(browser, shot, theme)
        browser.close()


if __name__ == "__main__":
    main()
