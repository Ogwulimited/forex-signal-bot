"""
MSNR Signal Builder

Assembles the final deliverable signal from all upstream modules:
  - Storyline direction
  - Valid setup (entry zone + obstacle)
  - H4 rejection
  - H1 confirmation

Also applies:
  - Stop-loss calculation (structural + numeric cap)
  - Target = obstacle (per Topic 30 / Module 9)
  - Risk classification (confirmation entry → 1% risk)
"""

from zone_filter import PIP_SCALE


# Stop-loss parameters for confirmation entries (Session 2 Topic 12)
DEFAULT_STOP_PIPS = 20
MIN_STOP_PIPS = 15             # never tighter than this — noise floor


def _pips_to_price(pair, pips):
    return pips * PIP_SCALE.get(pair, 0.0001)


def _price_to_pips(pair, price_diff):
    return abs(price_diff) / PIP_SCALE.get(pair, 0.0001)


def _compute_stop(pair, direction, entry_zone, current_price):
    """
    Compute the stop-loss level.

    For a SELL (resistance entry):
      Structural stop = above the entry zone level + buffer
      Fixed cap stop = entry + 20 pips
      Final = the WIDER of the two (safer)

    For a BUY (support entry):
      Structural stop = below the entry zone level - buffer
      Fixed cap stop = entry - 20 pips
      Final = the WIDER of the two
    """
    zone_level = entry_zone['level']
    cap_pips = DEFAULT_STOP_PIPS
    min_pips = MIN_STOP_PIPS

    # Structural buffer: stop placed just beyond the zone boundary
    # For a resistance zone, that's above the level
    # For a support zone, below the level
    # Buffer = 5 pips (small margin for noise)
    buffer_pips = 5
    buffer = _pips_to_price(pair, buffer_pips)
    cap = _pips_to_price(pair, cap_pips)
    min_floor = _pips_to_price(pair, min_pips)

    if direction == 'sell':
        structural_sl = zone_level + buffer
        cap_sl = zone_level + cap
        final_sl = max(structural_sl, cap_sl)
        # Enforce minimum distance
        if _price_to_pips(pair, final_sl - zone_level) < min_pips:
            final_sl = zone_level + min_floor
    else:  # buy
        structural_sl = zone_level - buffer
        cap_sl = zone_level - cap
        final_sl = min(structural_sl, cap_sl)
        if _price_to_pips(pair, zone_level - final_sl) < min_pips:
            final_sl = zone_level - min_floor

    return final_sl


def build_signal(pair, storyline_direction, setup, rejection, confirmation,
                 current_epoch, debug=False):
    """
    Assemble the final signal dict. Returns None if any required
    component is missing.
    """
    if not setup or not rejection or not confirmation:
        return None

    entry_zone = setup['entry']
    obstacle = setup['obstacle']

    if obstacle is None:
        if debug:
            print(f"  [SIGNAL] no obstacle — cannot compute target")
        return None

    direction = 'sell' if storyline_direction == 'bearish' else 'buy'

    # Entry = the entry zone level (where the rejection occurred)
    entry = entry_zone['level']

    # Target = obstacle level (Topic 30 / Module 9)
    tp = obstacle['level']

    # Stop
    sl = _compute_stop(pair, direction, entry_zone, None)

    # Compute RR
    risk = abs(entry - sl)
    reward = abs(entry - tp)
    rr = reward / risk if risk > 0 else 0

    # Risk classification — our bot only produces confirmation entries
    risk_class = 'low'
    risk_pct = 1.0

    signal = {
        'pair': pair,
        'direction': direction,
        'entry': round(entry, 5),
        'sl': round(sl, 5),
        'tp': round(tp, 5),
        'rr': round(rr, 2),
        'storyline': storyline_direction,
        'risk_class': risk_class,
        'risk_pct': risk_pct,
        'room_pips': setup.get('room_pips'),
        'stop_pips': round(_price_to_pips(pair, risk), 1),
        'target_pips': round(_price_to_pips(pair, reward), 1),
        'entry_zone': {
            'type': entry_zone['type'],
            'level': entry_zone['level'],
            'patterns': entry_zone.get('patterns', []),
            'cluster_count': entry_zone.get('cluster_count'),
        },
        'obstacle_zone': {
            'type': obstacle['type'],
            'level': obstacle['level'],
            'patterns': obstacle.get('patterns', []),
        },
        'rejection_candle_epoch': rejection['rejection_candle'].get('datetime'),
        'confirmation_method': confirmation['method'],
        'confirmation_candle_epoch': confirmation['break_candle'].get('datetime'),
        'timestamp': current_epoch,
    }

    if debug:
        print(f"  [SIGNAL] ✅ {direction.upper()} {pair} "
              f"entry={entry:.5f} SL={sl:.5f} TP={tp:.5f} "
              f"RR={rr:.2f} stop={signal['stop_pips']}p")

    return signal
