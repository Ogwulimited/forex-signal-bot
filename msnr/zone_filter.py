"""
MSNR Zone Filter

Takes raw zones from zone_detector and reduces them to the
actionable subset:

  1. Proximity    — keep only zones within X pips of current price
  2. Clustering   — merge zones that sit within tolerance of each other
  3. Recentness   — down-rank (or drop) zones older than N candles

Zone ranking combines:
  - cluster size (how many raw zones merged)
  - recentness (index distance from end)
  - (optionally) HTF confluence, added in a later module

Output: list of filtered/merged zone dicts, each with a 'score' field.
"""


# Pip scale per pair. Values based on the instructor's stated defaults
# from the spec review (Q5). Used to convert pip-based tolerances
# into price offsets.
PIP_SCALE = {
    "EURUSD": 0.0001,
    "GBPUSD": 0.0001,
    "USDJPY": 0.01,
    "USDCAD": 0.0001,
    "AUDUSD": 0.0001,
}


def _pips_to_price(pair, pips):
    return pips * PIP_SCALE.get(pair, 0.0001)


def filter_by_proximity(zones, current_price, pair, max_pips=150, debug=False):
    """
    Keep only zones within max_pips of current price.
    """
    max_price = _pips_to_price(pair, max_pips)
    kept = [z for z in zones
            if abs(z['level'] - current_price) <= max_price]

    if debug:
        print(f"  [FILTER] Proximity (≤{max_pips} pips): "
              f"{len(zones)} → {len(kept)}")
    return kept


def cluster_zones(zones, pair, tolerance_pips=8, debug=False):
    """
    Merge zones that sit within tolerance_pips of each other.
    Each cluster becomes a single merged zone.

    Cluster attributes:
      - type: majority type of the merged zones
      - level: weighted avg by cluster size, or the level of the
               most-recent zone in the cluster
      - patterns: list of patterns contributing
      - count: number of raw zones merged
      - latest_index: most recent index in the cluster
    """
    if not zones:
        return []

    tolerance = _pips_to_price(pair, tolerance_pips)

    # Sort by level ascending
    sorted_zones = sorted(zones, key=lambda z: z['level'])

    clusters = []
    current = [sorted_zones[0]]

    for z in sorted_zones[1:]:
        if abs(z['level'] - current[-1]['level']) <= tolerance:
            current.append(z)
        else:
            clusters.append(current)
            current = [z]
    clusters.append(current)

    merged = []
    for cluster in clusters:
        # Majority type
        types = [z['type'] for z in cluster]
        dom_type = 'resistance' if types.count('resistance') >= types.count('support') else 'support'

        # Most recent zone in cluster drives the level & index
        latest = max(cluster, key=lambda z: z['index'])

        merged.append({
            'type': dom_type,
            'level': latest['level'],
            'index': latest['index'],
            'cluster_count': len(cluster),
            'patterns': sorted(set(z['pattern'] for z in cluster)),
            'cluster_zones': cluster,
        })

    if debug:
        print(f"  [FILTER] Clustering (≤{tolerance_pips} pips): "
              f"{len(zones)} → {len(merged)}")
    return merged


def score_and_rank(zones, total_candles, debug=False):
    """
    Score each zone on:
      - cluster size (more raw zones merged = stronger level)
      - recentness (closer to end = stronger)
    
    Score is additive; higher = stronger.
    """
    scored = []
    for z in zones:
        # Cluster contribution: capped so a huge cluster doesn't dominate
        cluster_score = min(z['cluster_count'], 5) * 2  # max 10

        # Recentness contribution: 0–10 based on how recent
        # (100% at index == total, 0% at index == 0)
        age = total_candles - 1 - z['index']
        # Score 10 at age 0, 0 at age 200, linear in between
        recency_score = max(0, 10 - (age / 20))

        total = cluster_score + recency_score
        scored.append({
            **z,
            'score': round(total, 2),
        })

    scored.sort(key=lambda z: z['score'], reverse=True)

    if debug:
        print(f"  [FILTER] Scored {len(scored)} zones. Top 3:")
        for z in scored[:3]:
            print(f"    {z['type']:>10} @ {z['level']:.5f} "
                  f"score={z['score']} cluster={z['cluster_count']} "
                  f"patterns={z['patterns']}")
    return scored


def filter_zones(raw_zones, candles, pair, debug=False):
    """
    Full filter pipeline. Returns a ranked list of merged/scored zones.
    """
    if not raw_zones or not candles:
        return []

    current_price = candles[-1]['close']
    total = len(candles)

    proximity = filter_by_proximity(raw_zones, current_price, pair,
                                    max_pips=150, debug=debug)
    clustered = cluster_zones(proximity, pair, tolerance_pips=8, debug=debug)
    ranked = score_and_rank(clustered, total, debug=debug)

    return ranked
