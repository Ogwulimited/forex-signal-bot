"""
MSNR Zone Classifier

Given the active storyline direction and the filtered working-timeframe
zones, split zones into:

  - Entry zones: aligned with storyline direction (where we'd enter)
  - Obstacles: opposing zones in the path of the trade

For each entry zone, identify the NEAREST obstacle in the trade path.
That obstacle becomes the natural target (per Topic 30 / Module 9).

Storyline = bearish → selling:
  - resistance zones → entries
  - support zones → obstacles
  - flip zones → entry if above price, obstacle if below

Storyline = bullish → buying:
  - support zones → entries
  - resistance zones → obstacles
  - flip zones → entry if below price, obstacle if above
"""

from zone_filter import PIP_SCALE


def _pips(a, b, pair):
    return abs(a - b) / PIP_SCALE.get(pair, 0.0001)


def classify_zones(storyline_direction, zones, current_price, pair, debug=False):
    """
    Split zones into entries + obstacles, and pair each entry with its
    nearest obstacle in the trade path.

    Parameters:
    - storyline_direction: 'bullish' | 'bearish'
    - zones: list of filtered zones (from zone_filter.filter_zones)
    - current_price: latest close price (float)
    - pair: pair name (for pip conversion)
    - debug: print classification reasoning

    Returns:
    - dict:
      {
        'storyline': storyline_direction,
        'entry_zones': [...],
        'obstacles': [...],
        'setups': [   # one per entry zone
          {
            'entry': {...},
            'obstacle': {...} or None,
            'room_pips': float,
          },
          ...
        ]
      }
    """
    if storyline_direction not in ('bullish', 'bearish'):
        return None

    entries = []
    obstacles = []

    for z in zones:
        ztype = z['type']
        zlevel = z['level']

        if storyline_direction == 'bearish':
            # SELL: resistance = entry, support = obstacle
            if ztype == 'resistance':
                entries.append(z)
            elif ztype == 'support':
                obstacles.append(z)
            elif ztype == 'flip':
                # Above price = resistance-like (entry for sell)
                # Below price = support-like (obstacle)
                if zlevel > current_price:
                    entries.append(z)
                else:
                    obstacles.append(z)

        else:  # bullish
            # BUY: support = entry, resistance = obstacle
            if ztype == 'support':
                entries.append(z)
            elif ztype == 'resistance':
                obstacles.append(z)
            elif ztype == 'flip':
                # Below price = support-like (entry for buy)
                # Above price = resistance-like (obstacle)
                if zlevel < current_price:
                    entries.append(z)
                else:
                    obstacles.append(z)

    if debug:
        print(f"  [CLASS] storyline={storyline_direction} | "
              f"entries={len(entries)} | obstacles={len(obstacles)}")

    # Pair each entry with its nearest obstacle in the trade path
    setups = []
    for entry in entries:
        e_lvl = entry['level']
        nearest = None

        if storyline_direction == 'bearish':
            # Sell: obstacle is nearest support BELOW entry level
            candidates = [o for o in obstacles if o['level'] < e_lvl]
            if candidates:
                nearest = max(candidates, key=lambda o: o['level'])
        else:
            # Buy: obstacle is nearest resistance ABOVE entry level
            candidates = [o for o in obstacles if o['level'] > e_lvl]
            if candidates:
                nearest = min(candidates, key=lambda o: o['level'])

        room = _pips(e_lvl, nearest['level'], pair) if nearest else None

        setups.append({
            'entry': entry,
            'obstacle': nearest,
            'room_pips': round(room, 1) if room is not None else None,
        })

    # Sort setups: entries closest to current price first
    setups.sort(key=lambda s: abs(s['entry']['level'] - current_price))

    if debug:
        print(f"  [CLASS] Setup pairings (entry → obstacle):")
        for s in setups:
            e = s['entry']
            o = s['obstacle']
            obs_str = (f"{o['type']} @ {o['level']:.5f}" if o
                       else "none in path")
            room_str = (f"{s['room_pips']}p" if s['room_pips'] is not None
                        else "—")
            print(f"    entry {e['type']:>10} @ {e['level']:.5f} "
                  f"→ obstacle {obs_str} | room={room_str}")

    return {
        'storyline': storyline_direction,
        'entry_zones': entries,
        'obstacles': obstacles,
        'setups': setups,
      }
