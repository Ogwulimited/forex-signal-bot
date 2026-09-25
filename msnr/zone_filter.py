"""
MSNR Zone Filter v2

Changes from v1:
  - Cluster score is non-linear: rewards 2-5 merges, penalises saturation (>20)
  - Recency uses exponential decay, clamped at 0
  - Introduces 'flip' zone type when A and V coexist in a cluster
  - Test output will show distance from current price
"""

PIP_SCALE = {
    "EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01,
    "USDCAD": 0.0001, "AUDUSD": 0.0001,
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
    return 2  # saturated band — likely range noise, not a clean level


def _recency_score(index, total, half_life=100):
    """Exponential decay from 10 (age=0) toward 0, clamped."""
    age = total - 1 - index
    return max(0.0, 10.0 * (0.5 ** (age / half_life)))


def filter_by_proximity(zones, current_price, pair, max_pips=150, debug=False):
    max_price = _pips_to_price(pair, max_pips)
    kept = [z for z in zones if abs(z['level'] - current_price) <= max_price]
    if debug:
        print(f"  [FILTER] Proximity (≤{max_pips} pips): {len(zones)} → {len(kept)}")
    return kept


def cluster_zones(zones, pair, tolerance_pips=8, debug=False):
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
            zone_type = 'resistance' if types.count('resistance') > types.count('support') else 'support'

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
    scored = []
    for z in zones:
        c_score = _cluster_score(z['cluster_count'])
        r_score = _recency_score(z['index'], total_candles)
        # Weight cluster higher (levels tested multiple times = stronger)
        total_score = (c_score * 0.6) + (r_score * 0.4)
        scored.append({**z, 'score': round(total_score, 2)})

    scored.sort(key=lambda z: z['score'], reverse=True)
    if debug:
        print(f"  [FILTER] Scored {len(scored)} zones.")
    return scored


def filter_zones(raw_zones, candles, pair, debug=False):
    if not raw_zones or not candles:
        return []
    current_price = candles[-1]['close']
    total = len(candles)
    prox = filter_by_proximity(raw_zones, current_price, pair, 150, debug)
    clust = cluster_zones(prox, pair, 8, debug)
    return score_and_rank(clust, total, debug)
