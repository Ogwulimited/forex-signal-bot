"""
MSNR Zone Classifier v2

Changes from v1:
  - Entries must be on the CORRECT side of current price
    (bearish: entry above price; bullish: entry below)
  - Minimum entry distance from price (avoid entries we're
    effectively already at)
  - Maximum entry distance from price (intraday reachability)
  - Minimum room-to-obstacle filter (RR floor)
"""

from zone_filter import PIP_SCALE


MIN_ENTRY_DISTANCE_PIPS = 5      # entry must be at least this far from price
MAX_ENTRY_DISTANCE_PIPS = 100    # avoid entries too far to reach intraday
MIN_ROOM_PIPS = 40               # ~2R at 20-pip stop


def _pips(a, b, pair):
    return abs(a - b) / PIP_SCALE.get(pair, 0.0001)


def classify_zones(storyline_direction, zones, current_price, pair,
                   min_entry_pips=MIN_ENTRY_DISTANCE_PIPS,
                   max_entry_pips=MAX_ENTRY_DISTANCE_PIPS,
                   min_room_pips=MIN_ROOM_PIPS,
                   debug=False):
    """
    Split zones into entries + obstacles, apply filters, and pair each
    surviving entry with its nearest obstacle in the trade path.

    Returns a dict with:
      - entry_zones: filtered valid entries
      - obstacles: all obstacles (unfiltered, for downstream use)
      - setups: entry → obstacle pairings that pass all filters
      - rejected_setups: (optional debug) setups that failed a filter
    """
    if storyline_direction not in ('bullish', 'bearish'):
        return None

    entries = []
    obstacles = []

    # Step 1: split by type and by position relative to price
    for z in zones:
        ztype = z['type']
        zlevel = z['level']
        dist = _pips(zlevel, current_price, pair)

        if storyline_direction == 'bearish':
            if ztype == 'resistance':
                entries.append(z)
            elif ztype == 'support':
                obstacles.append(z)
            elif ztype == 'flip':
                if zlevel > current_price:
                    entries.append(z)
                else:
                    obstacles.append(z)

        else:  # bullish
            if ztype == 'support':
                entries.append(z)
            elif ztype == 'resistance':
                obstacles.append(z)
            elif ztype == 'flip':
                if zlevel < current_price:
                    entries.append(z)
                else:
                    obstacles.append(z)

    # Step 2: filter entries by directional position + distance
    filtered_entries = []
    for e in entries:
        lvl = e['level']
        dist = _pips(lvl, current_price, pair)

        # Directional check
        if storyline_direction == 'bearish' and lvl <= current_price:
            continue
        if storyline_direction == 'bullish' and lvl >= current_price:
            continue

        # Distance check
        if dist < min_entry_pips or dist > max_entry_pips:
            continue

        filtered_entries.append(e)

    if debug:
        print(f"  [CLASS] storyline={storyline_direction} | "
              f"raw entries={len(entries)} → filtered={len(filtered_entries)} | "
              f"obstacles={len(obstacles)}")

    # Step 3: pair each entry with nearest obstacle in path
    setups = []
    rejected = []
    for entry in filtered_entries:
        e_lvl = entry['level']
        nearest = None

        if storyline_direction == 'bearish':
            candidates = [o for o in obstacles if o['level'] < e_lvl]
            if candidates:
                nearest = max(candidates, key=lambda o: o['level'])
        else:
            candidates = [o for o in obstacles if o['level'] > e_lvl]
            if candidates:
                nearest = min(candidates, key=lambda o: o['level'])

        room = _pips(e_lvl, nearest['level'], pair) if nearest else None

        setup = {
            'entry': entry,
            'obstacle': nearest,
            'room_pips': round(room, 1) if room is not None else None,
        }

        if room is not None and room >= min_room_pips:
            setups.append(setup)
        else:
            rejected.append(setup)

    # Sort by proximity to current price (closest first)
    setups.sort(key=lambda s: abs(s['entry']['level'] - current_price))
    rejected.sort(key=lambda s: abs(s['entry']['level'] - current_price))

    if debug:
        print(f"  [CLASS] Valid setups: {len(setups)} | "
              f"Rejected (room < {min_room_pips}p): {len(rejected)}")
        for s in setups:
            e = s['entry']; o = s['obstacle']
            print(f"    ✅ {e['type']:>10} @ {e['level']:.5f} "
                  f"→ {o['type']} @ {o['level']:.5f} | room={s['room_pips']}p")
        for s in rejected:
            e = s['entry']; o = s['obstacle']
            o_str = (f"{o['type']} @ {o['level']:.5f}" if o else "none")
            print(f"    ✗  {e['type']:>10} @ {e['level']:.5f} "
                  f"→ {o_str} | room={s['room_pips']}p (too small)")

    return {
        'storyline': storyline_direction,
        'entry_zones': filtered_entries,
        'obstacles': obstacles,
        'setups': setups,
        'rejected_setups': rejected,
          }
