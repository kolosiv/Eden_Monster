# Eden Analytics Pro - Brand Guidelines

## Overview

Eden Analytics Pro features a professional brand identity that reflects its focus on hockey analytics, financial growth, and intelligent betting strategies.

## Brand Story

The Eden brand combines elements of:
- **The Eden Tree** - Symbolizing growth, prosperity, and wise decision-making
- **Hockey** - Our core sport focus with NHL analytics
- **Financial Success** - Transforming sports insights into profitable outcomes

## Logo Suite

Our logo suite includes multiple variants for different use cases:

### 1. Full Logo (`eden_logo_full.png`)
- **Size:** 1584 × 672 pixels
- **Use:** Main branding, documentation headers, marketing materials
- **Background:** Works best on dark backgrounds

### 2. Icon Logo (`eden_logo_icon.png`)
- **Size:** 1024 × 1024 pixels (square)
- **Use:** App icons, favicons, system tray, social media profiles
- **Background:** Transparent

### 3. Horizontal Logo (`eden_logo_horizontal.png`)
- **Size:** 1584 × 672 pixels
- **Use:** Dashboard headers, sidebar branding, email signatures
- **Background:** Best on dark backgrounds

### 4. Dark Theme Logo (`eden_logo_dark.png`)
- **Size:** 1584 × 672 pixels
- **Use:** UI elements in dark theme mode
- **Background:** Optimized for dark backgrounds

## Intro Videos

### V2 - "The Golden Apple Game" (Current) ⭐
- **File:** `eden_intro_v2.mp4`
- **Duration:** 10 seconds
- **Resolution:** 1280 × 720 (HD)
- **File Size:** ~5.2 MB
- **Scenario:**
  1. Golden Eden tree above hockey rink (0-2s)
  2. Golden apple falls onto ice (2-3s)
  3. Three hockey players battle for the apple (3-5s)
  4. One player shoots powerful slapshot (5-7s)
  5. Money explosion from goal (7-9s)
  6. "EDEN ANALYTICS PRO" text appears (9-10s)
- **Features:** Dynamic hockey gameplay, multiple players, intense competition
- **Recommended:** Primary intro for application ✅

### V1 - Original (Alternative/Backup)
- **File:** `eden_intro_animation.mp4`
- **Duration:** 7 seconds
- **Resolution:** 1280 × 720 (HD)
- **File Size:** ~2.4 MB
- **Scenario:** Simple apple fall → single hockey hit → money transformation
- **Use:** Backup/alternative version, environments with bandwidth constraints

## Application Icons

### Windows Icon (`eden.ico`)
- **Sizes:** 16×16, 32×32, 48×48, 64×64, 128×128, 256×256
- **Use:** Windows application icon, taskbar, shortcuts

### macOS Icon (`eden.icns`)
- **Sizes:** 128×128 to 512×512
- **Use:** macOS application icon, Dock, Finder

## Color Palette

### Primary Colors
| Color | Hex | RGB | Usage |
|-------|-----|-----|-------|
| Primary Purple | `#6C63FF` | 108, 99, 255 | Primary buttons, accents |
| Secondary Cyan | `#00D4FF` | 0, 212, 255 | Secondary elements, links |
| Accent Pink | `#FF6B9D` | 255, 107, 157 | Highlights, notifications |

### Status Colors
| Color | Hex | RGB | Usage |
|-------|-----|-----|-------|
| Success Green | `#00E676` | 0, 230, 118 | Positive results, wins |
| Warning Yellow | `#FFD600` | 255, 214, 0 | Warnings, cautions |
| Error Red | `#FF5252` | 255, 82, 82 | Errors, losses |

### Dark Theme Background
| Color | Hex | RGB | Usage |
|-------|-----|-----|-------|
| Background | `#0F0F1A` | 15, 15, 26 | Main background |
| Surface | `#1A1A2E` | 26, 26, 46 | Cards, panels |
| Surface Light | `#252540` | 37, 37, 64 | Hover states |

### Light Theme Background
| Color | Hex | RGB | Usage |
|-------|-----|-----|-------|
| Background | `#F5F7FA` | 245, 247, 250 | Main background |
| Surface | `#FFFFFF` | 255, 255, 255 | Cards, panels |
| Surface Light | `#F0F2F5` | 240, 242, 245 | Hover states |

## Typography

### Primary Font Family
```
'Segoe UI', 'SF Pro Display', 'Roboto', sans-serif
```

### Monospace Font (for code/numbers)
```
'JetBrains Mono', 'Consolas', 'Monaco', monospace
```

### Font Sizes
| Element | Size |
|---------|------|
| H1 / Title | 28-32px |
| H2 / Section | 20-24px |
| H3 / Subsection | 16-18px |
| Body | 13-14px |
| Small / Caption | 11-12px |

## Logo Usage Guidelines

### Do's ✅
- Use on dark backgrounds for best visibility
- Maintain aspect ratio when scaling
- Use the appropriate variant for the context
- Allow adequate spacing around the logo

### Don'ts ❌
- Don't stretch or distort the logo
- Don't change the logo colors
- Don't place on busy backgrounds
- Don't crop or cut off parts of the logo

## File Locations

All branding assets are located in:
```
gui/assets/branding/
├── eden_intro_v2.mp4          # V2 intro (10s, primary) ⭐
├── eden_intro_animation.mp4   # V1 intro (7s, backup)
├── eden_logo_full.png
├── eden_logo_icon.png
├── eden_logo_horizontal.png
├── eden_logo_dark.png
├── eden.ico
└── eden.icns
```

## Integration

### Using Logos in Code
```python
from gui.themes.modern_theme import get_logo_path, get_branding_asset

# Get logo for current theme
logo_path = get_logo_path(theme='dark', style='horizontal')

# Get specific branding asset
video_path = get_branding_asset('intro_video')
icon_path = get_branding_asset('app_icon_ico')
```

### Theme-Aware Logo Selection
The application automatically selects the appropriate logo variant based on the current theme (dark/light).

---

© 2026 Eden Analytics Pro. All rights reserved.
