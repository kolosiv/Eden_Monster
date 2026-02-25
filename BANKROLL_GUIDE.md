# 💰 Smart Bankroll Management Guide

This guide explains the bankroll management features in Eden MVP and how to use them effectively.

## Overview

Smart Bankroll Management helps you:
- **Protect your capital** during losing streaks
- **Grow your bankroll** optimally during winning periods
- **Understand risk** through Monte Carlo simulations
- **Adjust stakes automatically** based on your situation

## Understanding the Metrics

### Current Bankroll
Your current available funds for betting.

### Peak Bankroll
The highest your bankroll has reached. Used to calculate drawdown.

### Drawdown
The percentage drop from your peak bankroll.

```
Drawdown = (Peak - Current) / Peak × 100%
```

**Example:** If your peak was $1,200 and current is $1,000:
- Drawdown = ($1,200 - $1,000) / $1,200 = 16.7%

### Risk of Ruin (RoR)

The probability of losing a significant portion of your bankroll. We track:

- **RoR 50%**: Probability of losing half your bankroll
- **RoR 100%**: Probability of going completely bust

#### Risk Levels:
| RoR | Risk Level | Action |
|-----|------------|--------|
| < 10% | 🟢 Low | Normal betting |
| 10-25% | 🟡 Medium | Consider reducing stakes |
| 25-50% | 🟠 High | Reduce stakes significantly |
| > 50% | 🔴 Critical | Stop betting, reassess |

### Kelly Criterion

The mathematically optimal stake size to maximize long-term growth.

```
Kelly Fraction = (bp - q) / b
```

Where:
- `b` = odds - 1 (profit per unit)
- `p` = probability of winning
- `q` = probability of losing (1 - p)

**Important:** Full Kelly is very aggressive. We use "fractional Kelly" (50% by default).

### Expected Value (EV)

The average profit you can expect per bet.

```
EV = (Win Probability × Profit) - (Loss Probability × Loss)
```

Positive EV = profitable in the long run.

## Bankroll Profiles

### 🛡️ Conservative
**Best for:** Beginners, risk-averse bettors, small bankrolls

| Setting | Value |
|---------|-------|
| Base Stake | 2% |
| Min Stake | 1% |
| Max Stake | 4% |
| Emergency Threshold | 15% drawdown |

**Characteristics:**
- Slow, steady growth
- Very low risk of ruin
- Protects capital aggressively
- Stakes reduced early in drawdowns

### ⚖️ Moderate (Default)
**Best for:** Most users, balanced approach

| Setting | Value |
|---------|-------|
| Base Stake | 4% |
| Min Stake | 2% |
| Max Stake | 8% |
| Emergency Threshold | 20% drawdown |

**Characteristics:**
- Balanced risk/reward
- Reasonable growth rate
- Good protection
- Half Kelly criterion

### 🚀 Aggressive
**Best for:** Experienced bettors, high risk tolerance, large bankrolls

| Setting | Value |
|---------|-------|
| Base Stake | 6% |
| Min Stake | 3% |
| Max Stake | 12% |
| Emergency Threshold | 25% drawdown |

**Characteristics:**
- Faster growth potential
- Higher variance
- More aggressive recovery
- 70% Kelly criterion

### 🔧 Custom
Create your own profile with specific parameters.

## How Stake Adjustment Works

### Profit Mode
When your bankroll grows:
```
Stake Adjustment = Base + (Profit % × Increase Rate)
```

Example with Moderate profile:
- Bankroll up 20% → Stakes up 10% (0.20 × 0.50)

### Drawdown Mode
When experiencing drawdown:
```
Stake Adjustment = Base - (Drawdown % × Reduction Rate)
```

Example with Moderate profile:
- 10% drawdown → Stakes down 15% (0.10 × 1.5)

### Emergency Mode
Triggered when drawdown exceeds threshold:
- **All stakes reduced to 35%** of normal (Moderate profile)
- Warning displayed in UI
- Protects remaining capital

## Monte Carlo Simulation

### What It Does
Simulates thousands of possible futures based on your:
- Current bankroll
- Win rate
- Average win/loss amounts
- Stake size

### Interpreting Results

| Metric | Good Value | Warning |
|--------|------------|----------|
| Probability of Profit | > 70% | < 50% |
| Probability of 50% Loss | < 10% | > 25% |
| Median Final | > Initial | < Initial |

### Chart Interpretation

The histogram shows the distribution of possible outcomes:
- **Peak on the right** = likely to profit
- **Peak on the left** = likely to lose
- **Wide spread** = high variance
- **Narrow spread** = more predictable

## Best Practices

### 1. Start Conservative
If you're new:
- Use the Conservative profile
- Move to Moderate after 50+ successful bets
- Never go Aggressive until you understand variance

### 2. Never Chase Losses
- Let the system reduce stakes during drawdowns
- Don't override emergency protections
- Take breaks during bad runs

### 3. Set Realistic Goals
- Target 1-2% daily growth
- Expect drawdowns of 10-15%
- Plan for the long term (months, not days)

### 4. Review Regularly
- Check stats weekly
- Run simulations monthly
- Adjust profile if needed

### 5. Separate Bankrolls
- Don't use money you can't afford to lose
- Keep betting bankroll separate from life funds
- Have a stop-loss point (e.g., 40% of initial)

## Understanding Variance

Even with positive EV, you'll experience losing streaks.

### Example Probability Table
| Consecutive Losses | Probability (85% WR) |
|--------------------|----------------------|
| 2 in a row | 2.25% |
| 3 in a row | 0.34% |
| 4 in a row | 0.05% |
| 5 in a row | 0.0076% |

**Key insight:** With 100 bets, there's a ~10% chance of 3 consecutive losses.

## Warning Signs

🚨 **Stop and reassess if:**
- Drawdown exceeds 25%
- 5+ consecutive hole losses
- Risk of Ruin exceeds 50%
- You're tempted to increase stakes manually

## Recovery Strategy

After a significant drawdown:

1. **Don't increase stakes** to recover faster
2. **Trust the system** - it will recover naturally
3. **Review recent bets** - were filters too loose?
4. **Consider profile downgrade** temporarily
5. **Take a break** if emotionally affected

## FAQ

**Q: Why are my stakes so small?**
A: Proper risk management requires small stakes relative to bankroll. 2-4% is standard.

**Q: When should I switch profiles?**
A: After establishing a track record (50+ bets) with consistent profits.

**Q: Is full Kelly ever recommended?**
A: No. Full Kelly has ~50% drawdown probability. Always use fractional.

**Q: How often should I update my bankroll?**
A: After every bet result for accurate tracking.

**Q: Can I manually override stake recommendations?**
A: Yes, but not recommended. The system is designed to protect you.

## Technical Details

### Formulas Used

**Risk of Ruin:**
```
RoR = ((1 - edge) / (1 + edge)) ^ units_to_ruin
edge = (win_rate × avg_win) - (loss_rate × avg_loss)
```

**Monte Carlo Parameters:**
- Simulations: 1,000
- Bets per simulation: 100
- Uses actual win rate from history

**Smoothing Factor:**
- Stake changes are smoothed to prevent whiplash
- 70% new value, 30% previous value

## Support

For questions about bankroll management:
1. Check the logs in `logs/eden.log`
2. Review your stats in the Statistics tab
3. Run a Monte Carlo simulation
4. Open an issue on GitHub
