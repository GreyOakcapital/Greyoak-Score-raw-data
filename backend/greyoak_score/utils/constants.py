"""Constants used throughout the scoring engine.

All constants follow spec terminology exactly for traceability.
"""

# Division by zero prevention (Section 10 - Edge Cases)
TINY = 1e-8

# Scoring modes
MODE_TRADER = "Trader"
MODE_INVESTOR = "Investor"
VALID_MODES = [MODE_TRADER, MODE_INVESTOR]

# Bands (Section 6 - Banding)
BAND_STRONG_BUY = "Strong Buy"
BAND_BUY = "Buy"
BAND_HOLD = "Hold"
BAND_AVOID = "Avoid"
VALID_BANDS = [BAND_STRONG_BUY, BAND_BUY, BAND_HOLD, BAND_AVOID]

# Band ordering (for most conservative selection)
BAND_ORDER = {
    BAND_STRONG_BUY: 4,
    BAND_BUY: 3,
    BAND_HOLD: 2,
    BAND_AVOID: 1,
}

# Pillar names
PILLAR_F = "F"  # Fundamentals
PILLAR_T = "T"  # Technicals
PILLAR_R = "R"  # Relative Strength
PILLAR_O = "O"  # Ownership
PILLAR_Q = "Q"  # Quality
PILLAR_S = "S"  # Sector Momentum
PILLARS = [PILLAR_F, PILLAR_T, PILLAR_R, PILLAR_O, PILLAR_Q, PILLAR_S]

# Score bounds
SCORE_MIN = 0.0
SCORE_MAX = 100.0

# Risk penalty bounds (Section 7.1)
RP_MIN = 0.0
RP_MAX = 20.0

# Confidence bounds (Section 7.2)
CONFIDENCE_MIN = 0.0
CONFIDENCE_MAX = 1.0

# Normalization parameters (Section 4.1)
NORM_CENTER = 50.0  # Center point for z-score mapping
NORM_SCALE = 15.0   # Scale factor: points = 50 + 15*z

# Small sector threshold (Section 4.1)
SMALL_SECTOR_THRESHOLD = 6  # Use ECDF if n < 6
