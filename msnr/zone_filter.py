"""
MSNR Zone Filter v4

Changes from v3:
  - XAUUSD pip scale corrected from $0.10 to $0.50
    Previous value made 20-pip stops = $2.00, which is inside
    Gold's H4 noise range. $0.50/pip makes 20 pips = $10.00,
    proportional to Gold's typical H4 range.
"""

PIP_SCALE = {
    "EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01,
    "USDCAD": 0.0001, "AUDUSD": 0.0001,
    "XAUUSD": 0.50,    # $0.50/pip → 20-pip stop = $10.00 (Gold-vol appropriate)
}


def _pips_to_price(pair, pips):
    return pips * PIP_SCALE.get(pair, 0.0001)


def _cluster_score(count):
    """Reward 2-5 merges. Penalise saturation."""
    if count == 1:  return 2
    if count <= 4:  return 10
    if count <= 8:  return 8
    if count <= 15: return 6
    if count <= 25: return 4
    return 2


def _recency_score(index, total, half_life=100):
    """Exponential decay from 10 (age=0) toward 0."""
    age = total - 1 - index
    return max(0.0, 10.0 * (0.5 ** (age / half_life)))


def filter_by_proximity(zones, current_price, pair, max_pips=150, debug=False):
    """Keep only zones within max_pips of current price."""
    max_price = _pips_to_price(pair, max_pips)
    kept = [z for z in zones if abs(z['level'] - current_price) <= max_price]
    if debug:
        print(f"  [FILTER] Proximity (≤{max_pips} pips): {len(zones)} → {len(kept)}")
    return kept


def cluster_zones(zones, pair, tolerance_pips=8, debug=False):
    """Merge zones within tolerance_pips of each other into single levels."""
    if not zones:
        return []

    tolerance = _pips_to_price(pair, tolerance_pips)
    sorted_zones = sorted(zones, key=lambda z: z['level'])

    clusters, current = [], [sorted_zones[0]]
    for z in sorted_zones[1:]:
        if abs(z['level'] - current[-1]['level']) <= tolerance:
            current.append(z)
        else:
            clusters.append(current)
            current = [z]
    clusters.append(current)

    merged = []
    for cluster in clusters:
        patterns = set(z['pattern'] for z in cluster)
        latest = max(cluster, key=lambda z: z['index'])

        # Flip zone: contains both A and V patterns (RBS/SBR territory)
        if 'A' in patterns and 'V' in patterns:
            zone_type = 'flip'
        else:
            types = [z['type'] for z in cluster]
            zone_type = ('resistance' if types.count('resistance') > types.count('support')
                         else 'support')

        merged.append({
            'type': zone_type,
            'level': latest['level'],
            'index': latest['index'],
            'cluster_count': len(cluster),
            'patterns': sorted(patterns),
            'cluster_zones': cluster,
        })

    if debug:
        print(f"  [FILTER] Clustering (≤{tolerance_pips} pips): {len(zones)} → {len(merged)}")
    return merged


def score_and_rank(zones, total_candles, debug=False):
    """Score each zone on cluster strength + recency."""
    scored = []
    for z in zones:
        c_score = _cluster_score(z['cluster_count'])
        r_score = _recency_score(z['index'], total_candles)
        total_score = (c_score * 0.6) + (r_score * 0.4)
        scored.append({**z, 'score': round(total_score, 2)})

    scored.sort(key=lambda z: z['score'], reverse=True)
    if debug:
        print(f"  [FILTER] Scored {len(scored)} zones.")
    return scored


def filter_zones(raw_zones, candles, pair, debug=False):
    """Full filter pipeline: proximity → clustering → scoring."""
    if not raw_zones or not candles:
        return []

    current_price = candles[-1]['close']
    total = len(candles)

    prox = filter_by_proximity(raw_zones, current_price, pair, 150, debug)
    clust = cluster_zones(prox, pair, 8, debug)
    return score_and_rank(clust, total, debug)
