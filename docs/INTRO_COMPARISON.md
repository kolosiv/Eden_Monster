# Intro Video Comparison

This document compares the two intro video versions available for Eden Analytics Pro.

---

## V2 - "The Golden Apple Game" (Current) ⭐

**Status:** Primary intro video  
**File:** `gui/assets/branding/eden_intro_v2.mp4`  
**Duration:** 10 seconds  
**File Size:** ~5.2 MB  
**Resolution:** 1280 × 720 (HD)

### Scene Breakdown

| Time | Scene Description |
|------|-------------------|
| 0-2s | Golden Eden tree glowing above hockey rink |
| 2-3s | Golden apple falls onto the ice |
| 3-5s | **Three hockey players** battle for the apple |
| 5-7s | One player shoots powerful slapshot toward goal |
| 7-9s | Money explosion from the goal |
| 9-10s | "EDEN ANALYTICS PRO" text reveal |

### Advantages ✅

- **More Dynamic** - Features actual hockey gameplay
- **Multiple Players** - Three players competing creates excitement
- **Better Storytelling** - Enhanced narrative arc
- **Longer Duration** - 10 seconds allows better immersion
- **Action-Packed** - Battle sequence and slapshot add intensity
- **Theme Emphasis** - Clearly connects hockey and money/betting
- **Professional Quality** - Broadcast-quality visuals

### Best For

- Primary application launch
- Marketing materials
- Promotional content
- Full user experience

---

## V1 - Original (Alternative/Backup)

**Status:** Alternative/Backup  
**File:** `gui/assets/branding/eden_intro_animation.mp4`  
**Duration:** 7 seconds  
**File Size:** ~2.4 MB  
**Resolution:** 1280 × 720 (HD)

### Scene Breakdown

| Time | Scene Description |
|------|-------------------|
| 0-2s | Eden tree with golden money leaves |
| 2-3s | Apple falls from tree |
| 3-5s | Single hockey player hits the apple |
| 5-7s | Apple transforms into money |

### Advantages ✅

- **Shorter Duration** - Quick 7-second intro
- **Smaller File Size** - Only ~2.4 MB
- **Simpler Narrative** - Easy to understand
- **Lower Bandwidth** - Better for slow connections

### Best For

- Environments with bandwidth constraints
- Quick demo scenarios
- Backup when V2 unavailable
- Low-storage environments

---

## Comparison Table

| Feature | V2 (Current) | V1 (Backup) |
|---------|--------------|-------------|
| Duration | 10 seconds | 7 seconds |
| File Size | ~5.2 MB | ~2.4 MB |
| Players | 3 hockey players | 1 hockey player |
| Action Level | High (battle, slapshot) | Medium (single hit) |
| Money Reveal | Goal explosion | Direct transformation |
| Narrative Depth | Rich | Simple |
| Engagement | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Recommended | ✅ Primary | Backup only |

---

## Configuration

### Using V2 (Default)

In `gui/splash_screen.py`:
```python
self.video_path = Path(__file__).parent / "assets" / "branding" / "eden_intro_v2.mp4"
```

### Using V1 (Alternative)

In `gui/splash_screen.py`:
```python
self.video_path = Path(__file__).parent / "assets" / "branding" / "eden_intro_animation.mp4"
```

### In config.yaml

```yaml
gui:
  intro_video: "gui/assets/branding/eden_intro_v2.mp4"  # or eden_intro_animation.mp4
  intro_duration: 10  # or 7 for V1
  intro_skippable: true
  intro_fallback: "gui/assets/branding/eden_logo_full.png"
```

---

## Skipping the Intro

Both versions support skipping:
- **Keyboard:** Press any key
- **Mouse:** Click anywhere on the splash screen

---

© 2026 Eden Analytics Pro. All rights reserved.
