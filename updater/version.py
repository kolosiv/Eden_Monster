"""Version management for Eden Analytics Pro."""

VERSION = "2.1.1"
VERSION_TUPLE = (2, 0, 0)

CHANGELOG = """
## Version 2.0.0 - Eden Analytics Pro

### New Features
- Complete UI redesign with modern dark/light themes
- Dashboard with real-time statistics
- ML Models management tab
- Interactive Plotly charts
- Multi-user Telegram bot support
- Export to CSV, Excel, PDF
- Multi-language support (EN/RU)
- System tray integration
- Backup and restore functionality
- Windows installer

### Improvements
- Better ML model training interface
- Enhanced bankroll management
- Improved arbitrage detection
- Performance optimizations

### Bug Fixes
- Fixed missing ML Models tab
- Various UI improvements
"""


def compare_versions(v1: str, v2: str) -> int:
    """Compare two version strings.
    
    Returns:
        -1 if v1 < v2
        0 if v1 == v2
        1 if v1 > v2
    """
    parts1 = [int(x) for x in v1.split('.')]
    parts2 = [int(x) for x in v2.split('.')]
    
    for p1, p2 in zip(parts1, parts2):
        if p1 < p2:
            return -1
        elif p1 > p2:
            return 1
    
    return 0


def is_update_available(current: str, latest: str) -> bool:
    """Check if an update is available."""
    return compare_versions(current, latest) < 0


__all__ = ['VERSION', 'VERSION_TUPLE', 'CHANGELOG', 'compare_versions', 'is_update_available']
