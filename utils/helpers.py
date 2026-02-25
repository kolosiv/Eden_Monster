"""Helper Functions Module for Eden MVP.

Utility functions for odds conversion, validation, and formatting.
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any


# -------------------- ODDS CONVERSION --------------------

def decimal_to_american(decimal_odds: float) -> int:
    """Convert decimal odds to American odds.
    
    Args:
        decimal_odds: Decimal odds (e.g., 2.5)
        
    Returns:
        American odds (e.g., +150 or -200)
        
    Example:
        >>> decimal_to_american(2.5)
        150
        >>> decimal_to_american(1.5)
        -200
    """
    if decimal_odds <= 1:
        raise ValueError("Decimal odds must be greater than 1")
    
    if decimal_odds >= 2.0:
        return int(round((decimal_odds - 1) * 100))
    else:
        return int(round(-100 / (decimal_odds - 1)))


def american_to_decimal(american_odds: int) -> float:
    """Convert American odds to decimal odds.
    
    Args:
        american_odds: American odds (e.g., +150 or -200)
        
    Returns:
        Decimal odds (e.g., 2.5)
        
    Example:
        >>> american_to_decimal(150)
        2.5
        >>> american_to_decimal(-200)
        1.5
    """
    if american_odds == 0:
        raise ValueError("American odds cannot be zero")
    
    if american_odds > 0:
        return 1 + (american_odds / 100)
    else:
        return 1 + (100 / abs(american_odds))


def implied_probability(decimal_odds: float) -> float:
    """Calculate implied probability from decimal odds.
    
    Args:
        decimal_odds: Decimal odds
        
    Returns:
        Implied probability (0-1)
        
    Example:
        >>> implied_probability(2.0)
        0.5
    """
    if decimal_odds <= 1:
        raise ValueError("Decimal odds must be greater than 1")
    return 1 / decimal_odds


def odds_to_probability(decimal_odds: float) -> float:
    """Alias for implied_probability."""
    return implied_probability(decimal_odds)


def probability_to_odds(probability: float) -> float:
    """Convert probability to decimal odds.
    
    Args:
        probability: Probability (0-1)
        
    Returns:
        Decimal odds
    """
    if probability <= 0 or probability >= 1:
        raise ValueError("Probability must be between 0 and 1")
    return 1 / probability


def remove_vig(
    odds: Dict[str, float],
    method: str = "multiplicative"
) -> Dict[str, float]:
    """Remove bookmaker margin (vig) from odds.
    
    Normalizes implied probabilities to sum to 1.
    
    Args:
        odds: Dict mapping outcome to decimal odds
        method: Removal method ('multiplicative' or 'additive')
        
    Returns:
        Dict mapping outcome to fair probability
        
    Example:
        >>> remove_vig({'home': 2.1, 'away': 1.9})
        {'home': 0.4762..., 'away': 0.5238...}
    """
    # Calculate implied probabilities
    implied = {k: 1/v for k, v in odds.items() if v and v > 1}
    
    # Calculate total (overround)
    total = sum(implied.values())
    
    if total <= 0:
        return {k: 0.0 for k in odds}
    
    # Normalize
    if method == "multiplicative":
        return {k: v / total for k, v in implied.items()}
    else:  # additive
        margin = (total - 1) / len(implied)
        return {k: max(0, v - margin) for k, v in implied.items()}


def calculate_overround(odds: Dict[str, float]) -> float:
    """Calculate bookmaker overround (margin).
    
    Args:
        odds: Dict mapping outcome to decimal odds
        
    Returns:
        Overround percentage (e.g., 0.05 for 5%)
    """
    implied = sum(1/v for v in odds.values() if v and v > 1)
    return implied - 1


# -------------------- VALIDATION --------------------

def validate_odds(odds: float, min_odds: float = 1.01, max_odds: float = 100.0) -> bool:
    """Validate decimal odds value.
    
    Args:
        odds: Odds value to validate
        min_odds: Minimum acceptable odds
        max_odds: Maximum acceptable odds
        
    Returns:
        True if valid
    """
    return isinstance(odds, (int, float)) and min_odds <= odds <= max_odds


def validate_probability(prob: float) -> bool:
    """Validate probability value.
    
    Args:
        prob: Probability to validate
        
    Returns:
        True if valid (0 <= prob <= 1)
    """
    return isinstance(prob, (int, float)) and 0 <= prob <= 1


def validate_stake(stake: float, bankroll: float, max_percent: float = 0.2) -> bool:
    """Validate stake amount.
    
    Args:
        stake: Stake amount
        bankroll: Total bankroll
        max_percent: Maximum allowed percentage of bankroll
        
    Returns:
        True if valid
    """
    return 0 < stake <= bankroll * max_percent


# -------------------- FORMATTING --------------------

def format_currency(amount: float, currency: str = "USD", decimals: int = 2) -> str:
    """Format currency amount.
    
    Args:
        amount: Amount to format
        currency: Currency code
        decimals: Decimal places
        
    Returns:
        Formatted string (e.g., "$1,234.56")
    """
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "RUB": "₽"}
    symbol = symbols.get(currency, currency + " ")
    
    if amount >= 0:
        return f"{symbol}{amount:,.{decimals}f}"
    else:
        return f"-{symbol}{abs(amount):,.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format as percentage.
    
    Args:
        value: Value (as decimal, e.g., 0.05 for 5%)
        decimals: Decimal places
        
    Returns:
        Formatted string (e.g., "5.00%")
    """
    return f"{value * 100:.{decimals}f}%"


def format_odds(decimal_odds: float, format_type: str = "decimal") -> str:
    """Format odds for display.
    
    Args:
        decimal_odds: Decimal odds value
        format_type: Output format ('decimal', 'american', 'probability')
        
    Returns:
        Formatted odds string
    """
    if format_type == "decimal":
        return f"{decimal_odds:.2f}"
    elif format_type == "american":
        american = decimal_to_american(decimal_odds)
        return f"+{american}" if american > 0 else str(american)
    elif format_type == "probability":
        prob = implied_probability(decimal_odds)
        return format_percentage(prob)
    return str(decimal_odds)


def format_roi(roi: float) -> str:
    """Format ROI with color indicator.
    
    Args:
        roi: Return on investment (decimal)
        
    Returns:
        Formatted ROI string
    """
    if roi > 0:
        return f"[green]+{roi:.2%}[/green]"
    elif roi < 0:
        return f"[red]{roi:.2%}[/red]"
    return f"{roi:.2%}"


# -------------------- DATE/TIME --------------------

def parse_datetime(dt_string: str) -> datetime:
    """Parse datetime string in various formats.
    
    Args:
        dt_string: Datetime string
        
    Returns:
        datetime object
    """
    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dt_string.replace("+00:00", "Z"), fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse datetime: {dt_string}")


def format_datetime(dt: datetime, format_type: str = "full") -> str:
    """Format datetime for display.
    
    Args:
        dt: datetime object
        format_type: 'full', 'date', 'time', 'relative'
        
    Returns:
        Formatted string
    """
    if format_type == "full":
        return dt.strftime("%Y-%m-%d %H:%M")
    elif format_type == "date":
        return dt.strftime("%Y-%m-%d")
    elif format_type == "time":
        return dt.strftime("%H:%M")
    elif format_type == "relative":
        now = datetime.now()
        diff = dt - now
        
        if diff.days > 0:
            return f"in {diff.days}d {diff.seconds // 3600}h"
        elif diff.total_seconds() > 0:
            hours = int(diff.total_seconds() // 3600)
            minutes = int((diff.total_seconds() % 3600) // 60)
            return f"in {hours}h {minutes}m"
        else:
            return "started"
    return str(dt)


def time_until_match(commence_time: datetime) -> timedelta:
    """Calculate time until match starts.
    
    Args:
        commence_time: Match start time
        
    Returns:
        timedelta until match
    """
    return commence_time - datetime.now()


# -------------------- STATISTICAL --------------------

def calculate_expected_value(
    probability: float,
    payout: float,
    stake: float = 1.0
) -> float:
    """Calculate expected value of a bet.
    
    EV = (P(win) × Profit) - (P(lose) × Stake)
    
    Args:
        probability: Win probability
        payout: Payout if win (decimal odds × stake)
        stake: Stake amount
        
    Returns:
        Expected value
    """
    profit = payout - stake
    return (probability * profit) - ((1 - probability) * stake)


def calculate_variance(
    probability: float,
    payout: float,
    stake: float = 1.0
) -> float:
    """Calculate variance of a bet.
    
    Args:
        probability: Win probability
        payout: Payout if win
        stake: Stake amount
        
    Returns:
        Variance
    """
    ev = calculate_expected_value(probability, payout, stake)
    profit = payout - stake
    
    var = probability * (profit - ev) ** 2 + (1 - probability) * (-stake - ev) ** 2
    return var


def calculate_sharpe_ratio(
    ev: float,
    variance: float,
    risk_free_rate: float = 0.0
) -> float:
    """Calculate Sharpe ratio for a bet.
    
    Args:
        ev: Expected value
        variance: Variance
        risk_free_rate: Risk-free rate
        
    Returns:
        Sharpe ratio
    """
    if variance <= 0:
        return 0.0
    std = math.sqrt(variance)
    return (ev - risk_free_rate) / std


# -------------------- DATA UTILITIES --------------------

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers.
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Value to return if denominator is zero
        
    Returns:
        Division result or default
    """
    return numerator / denominator if denominator != 0 else default


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range.
    
    Args:
        value: Value to clamp
        min_val: Minimum value
        max_val: Maximum value
        
    Returns:
        Clamped value
    """
    return max(min_val, min(value, max_val))


def round_to_decimal(value: float, decimals: int = 2) -> float:
    """Round to specified decimal places.
    
    Args:
        value: Value to round
        decimals: Number of decimal places
        
    Returns:
        Rounded value
    """
    factor = 10 ** decimals
    return round(value * factor) / factor
