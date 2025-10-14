"""
Decision Contract for Rule-Based Predictor
Clean interface for predictor-owned entry/exit logic
"""

from dataclasses import dataclass, field
from typing import Optional, Literal, Dict

Action = Literal["enter_long", "hold_long", "exit_long", "do_nothing"]


@dataclass
class Decision:
    """
    Predictor-owned decision with exit policy
    
    The predictor, not the backtester, owns all exit logic:
    - Stop-loss levels
    - Take-profit targets
    - Trailing stops
    - Time horizons
    - Regime-specific exit conditions
    """
    action: Action
    
    # Predictor-owned exit policy (absolute prices)
    stop_loss: Optional[float] = None        # absolute price (e.g., 2400.0)
    take_profit: Optional[float] = None      # absolute price
    trail_stop: Optional[float] = None       # absolute price (if trailing)
    max_hold_bars: Optional[int] = None      # predictor-chosen horizon
    
    # Metadata
    reason: str = ""
    regime: str = ""  # "breakout", "mean_reversion", etc.
    meta: Dict = field(default_factory=dict)  # scores, signals, anything extra
    
    def __repr__(self):
        return (f"Decision(action={self.action}, "
                f"SL={self.stop_loss:.2f if self.stop_loss else None}, "
                f"TP={self.take_profit:.2f if self.take_profit else None}, "
                f"trail={self.trail_stop:.2f if self.trail_stop else None}, "
                f"max_hold={self.max_hold_bars}, "
                f"regime={self.regime})")
