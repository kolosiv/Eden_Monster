"""Bankroll Profiles for Eden MVP.

Defines risk profiles with different stake percentages and risk tolerances.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any


class ProfileType(str, Enum):
    """Available profile types."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


@dataclass
class BankrollProfile:
    """Risk profile for bankroll management.
    
    Attributes:
        type: Profile type identifier
        name: Human-readable name
        description: Profile description
        base_stake_percent: Default stake as % of bankroll
        min_stake_percent: Minimum stake %
        max_stake_percent: Maximum stake %
        drawdown_stake_reduction_start: Drawdown % at which to start reducing stakes
        drawdown_stake_reduction_rate: How aggressively to reduce (multiplier)
        emergency_drawdown_threshold: Drawdown % to trigger emergency mode
        emergency_stake_reduction: Factor to reduce stakes in emergency
        profit_stake_increase_rate: How much to increase stakes on profit
        max_stake_increase: Maximum stake increase multiplier
        kelly_fraction: Kelly criterion multiplier (0.5 = half Kelly)
        max_risk_per_bet: Maximum risk per bet as % of bankroll
    """
    type: ProfileType
    name: str
    description: str
    base_stake_percent: float
    min_stake_percent: float
    max_stake_percent: float
    drawdown_stake_reduction_start: float  # %
    drawdown_stake_reduction_rate: float
    emergency_drawdown_threshold: float  # %
    emergency_stake_reduction: float
    profit_stake_increase_rate: float
    max_stake_increase: float
    kelly_fraction: float
    max_risk_per_bet: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'type': self.type.value,
            'name': self.name,
            'description': self.description,
            'base_stake_percent': self.base_stake_percent,
            'min_stake_percent': self.min_stake_percent,
            'max_stake_percent': self.max_stake_percent,
            'drawdown_stake_reduction_start': self.drawdown_stake_reduction_start,
            'drawdown_stake_reduction_rate': self.drawdown_stake_reduction_rate,
            'emergency_drawdown_threshold': self.emergency_drawdown_threshold,
            'emergency_stake_reduction': self.emergency_stake_reduction,
            'profit_stake_increase_rate': self.profit_stake_increase_rate,
            'max_stake_increase': self.max_stake_increase,
            'kelly_fraction': self.kelly_fraction,
            'max_risk_per_bet': self.max_risk_per_bet
        }


# Predefined profiles

CONSERVATIVE_PROFILE = BankrollProfile(
    type=ProfileType.CONSERVATIVE,
    name="Conservative",
    description="Low risk, slow growth. Ideal for beginners or risk-averse bettors.",
    base_stake_percent=0.02,  # 2%
    min_stake_percent=0.01,   # 1%
    max_stake_percent=0.04,   # 4%
    drawdown_stake_reduction_start=5.0,  # Start reducing at 5% drawdown
    drawdown_stake_reduction_rate=2.0,   # 2x reduction rate
    emergency_drawdown_threshold=15.0,   # Emergency at 15%
    emergency_stake_reduction=0.25,      # Reduce to 25% of normal
    profit_stake_increase_rate=0.3,      # 30% of profit growth
    max_stake_increase=0.2,              # Max 20% increase
    kelly_fraction=0.3,                  # 30% Kelly
    max_risk_per_bet=0.03                # 3% max risk
)

MODERATE_PROFILE = BankrollProfile(
    type=ProfileType.MODERATE,
    name="Moderate",
    description="Balanced risk/reward. Default profile for most users.",
    base_stake_percent=0.04,  # 4%
    min_stake_percent=0.02,   # 2%
    max_stake_percent=0.08,   # 8%
    drawdown_stake_reduction_start=8.0,  # Start reducing at 8% drawdown
    drawdown_stake_reduction_rate=1.5,   # 1.5x reduction rate
    emergency_drawdown_threshold=20.0,   # Emergency at 20%
    emergency_stake_reduction=0.35,      # Reduce to 35% of normal
    profit_stake_increase_rate=0.5,      # 50% of profit growth
    max_stake_increase=0.3,              # Max 30% increase
    kelly_fraction=0.5,                  # Half Kelly
    max_risk_per_bet=0.05                # 5% max risk
)

AGGRESSIVE_PROFILE = BankrollProfile(
    type=ProfileType.AGGRESSIVE,
    name="Aggressive",
    description="Higher risk, faster growth. For experienced bettors with high risk tolerance.",
    base_stake_percent=0.06,  # 6%
    min_stake_percent=0.03,   # 3%
    max_stake_percent=0.12,   # 12%
    drawdown_stake_reduction_start=12.0, # Start reducing at 12% drawdown
    drawdown_stake_reduction_rate=1.0,   # 1x reduction rate
    emergency_drawdown_threshold=25.0,   # Emergency at 25%
    emergency_stake_reduction=0.5,       # Reduce to 50% of normal
    profit_stake_increase_rate=0.7,      # 70% of profit growth
    max_stake_increase=0.5,              # Max 50% increase
    kelly_fraction=0.7,                  # 70% Kelly
    max_risk_per_bet=0.08                # 8% max risk
)


def get_profile(profile_type: ProfileType) -> BankrollProfile:
    """Get a predefined profile by type.
    
    Args:
        profile_type: The profile type to retrieve
        
    Returns:
        BankrollProfile instance
    """
    profiles = {
        ProfileType.CONSERVATIVE: CONSERVATIVE_PROFILE,
        ProfileType.MODERATE: MODERATE_PROFILE,
        ProfileType.AGGRESSIVE: AGGRESSIVE_PROFILE
    }
    
    return profiles.get(profile_type, MODERATE_PROFILE)


def create_custom_profile(
    base_stake_percent: float = 0.04,
    min_stake_percent: float = 0.02,
    max_stake_percent: float = 0.08,
    emergency_drawdown_threshold: float = 20.0,
    **kwargs
) -> BankrollProfile:
    """Create a custom profile with user-defined parameters.
    
    Args:
        base_stake_percent: Default stake %
        min_stake_percent: Minimum stake %
        max_stake_percent: Maximum stake %
        emergency_drawdown_threshold: Drawdown % for emergency mode
        **kwargs: Additional profile parameters
        
    Returns:
        Custom BankrollProfile
    """
    return BankrollProfile(
        type=ProfileType.CUSTOM,
        name="Custom",
        description="User-defined custom profile.",
        base_stake_percent=base_stake_percent,
        min_stake_percent=min_stake_percent,
        max_stake_percent=max_stake_percent,
        drawdown_stake_reduction_start=kwargs.get('drawdown_stake_reduction_start', 8.0),
        drawdown_stake_reduction_rate=kwargs.get('drawdown_stake_reduction_rate', 1.5),
        emergency_drawdown_threshold=emergency_drawdown_threshold,
        emergency_stake_reduction=kwargs.get('emergency_stake_reduction', 0.35),
        profit_stake_increase_rate=kwargs.get('profit_stake_increase_rate', 0.5),
        max_stake_increase=kwargs.get('max_stake_increase', 0.3),
        kelly_fraction=kwargs.get('kelly_fraction', 0.5),
        max_risk_per_bet=kwargs.get('max_risk_per_bet', 0.05)
    )


def get_all_profiles() -> Dict[ProfileType, BankrollProfile]:
    """Get all predefined profiles.
    
    Returns:
        Dict mapping ProfileType to BankrollProfile
    """
    return {
        ProfileType.CONSERVATIVE: CONSERVATIVE_PROFILE,
        ProfileType.MODERATE: MODERATE_PROFILE,
        ProfileType.AGGRESSIVE: AGGRESSIVE_PROFILE
    }


def describe_profiles() -> str:
    """Get human-readable descriptions of all profiles.
    
    Returns:
        Formatted string describing all profiles
    """
    output = "=== BANKROLL PROFILES ===\n\n"
    
    for profile_type, profile in get_all_profiles().items():
        output += f"📊 {profile.name.upper()}\n"
        output += f"   {profile.description}\n"
        output += f"   Stakes: {profile.min_stake_percent*100:.0f}% - {profile.max_stake_percent*100:.0f}%\n"
        output += f"   Default: {profile.base_stake_percent*100:.0f}%\n"
        output += f"   Emergency at: {profile.emergency_drawdown_threshold:.0f}% drawdown\n"
        output += "\n"
    
    return output
