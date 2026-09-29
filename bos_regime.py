"""
BOS Regime Classifier

Combines 4H structure + 1H structure into a trading regime.

Strict mode rules (no counter-trend):
  4H bullish + 1H bullish → 'bullish_active'    → BUY allowed
  4H bullish + 1H bearish → 'bullish_transition' → WAIT
  4H bullish + 1H ranging → 'bullish_neutral'    → WAIT
  4H bearish + 1H bearish → 'bearish_active'    → SELL allowed
  4H bearish + 1H bullish → 'bearish_transition' → WAIT
  4H bearish + 1H ranging → 'bearish_neutral'    → WAIT
  4H ranging              → 'ranging'            → WAIT

Cascade override:
  Even when 4H and 1H both say bullish, if a FRESH bearish CHoCH
  just fired on 1H, we downgrade to transition. Same in reverse.
  This is Stage 1 of the cascade — the first crack before the HTF
  confirms the flip.
"""

from bos_structure import analyze as analyze_structure, detect_choch


# How many candles after a CHoCH we still treat it as "fresh"
CHoCH_OVERRIDE_FRESHNESS = 5


def get_regime(candles_4h, candles_1h, debug=False):
    """
    Returns regime dict:
    {
        'regime': str,
        'trade_direction': 'buy' | 'sell' | None,
        'structure_4h': {...},
        'structure_1h': {...},
        'choch_1h': {...} or None,
        'override_applied': bool,
    }
    """
    s4 = analyze_structure(candles_4h, debug=debug)
    s1 = analyze_structure(candles_1h, debug=debug)
    choch_1h = detect_choch(candles_1h, s1)

    state_4h = s4.get('state', 'unknown')
    state_1h = s1.get('state', 'unknown')

    if debug:
        print(f"  [REGIME] 4H={state_4h} | 1H={state_1h} | "
              f"CHoCH={choch_1h['type'] if choch_1h else 'none'}")

    # ─── Base classification ───
    regime = 'unknown'
    direction = None

    if state_4h == 'bullish':
        if state_1h == 'bullish':
            regime = 'bullish_active'
            direction = 'buy'
        elif state_1h == 'bearish':
            regime = 'bullish_transition'
        elif state_1h == 'ranging':
            regime = 'bullish_neutral'
    elif state_4h == 'bearish':
        if state_1h == 'bearish':
            regime = 'bearish_active'
            direction = 'sell'
        elif state_1h == 'bullish':
            regime = 'bearish_transition'
        elif state_1h == 'ranging':
            regime = 'bearish_neutral'
    elif state_4h == 'ranging':
        regime = 'ranging'

    # ─── Cascade override: fresh CHoCH against the HTF bias ───
    override_applied = False
    if choch_1h and choch_1h['candles_since'] <= CHoCH_OVERRIDE_FRESHNESS:
        if regime == 'bullish_active' and choch_1h['type'] == 'bearish_choch':
            regime = 'bullish_transition'
            direction = None
            override_applied = True
        elif regime == 'bearish_active' and choch_1h['type'] == 'bullish_choch':
            regime = 'bearish_transition'
            direction = None
            override_applied = True

    if debug and override_applied:
        print(f"  [REGIME] ⚠️ CHoCH override applied → {regime}")

    return {
        'regime': regime,
        'trade_direction': direction,
        'structure_4h': s4,
        'structure_1h': s1,
        'choch_1h': choch_1h,
        'override_applied': override_applied,
    }
