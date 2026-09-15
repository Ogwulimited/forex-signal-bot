# Backtest Funnel Report

Generated: 2026-09-15T20:34:09.529420+00:00  
History window: last 3 months  
Pairs tested: 15  
Scan cadence: every 5th 5M candle (~every 25 min)

## Aggregate Funnel

| Stage | Count | % of scan points |
|-------|------:|-----------------:|
| HTF not aligned | 819 | 62.76% |
| Outside London/NY session | 97 | 7.43% |
| Chop filter rejected | 7 | 0.54% |
| No swing breakout | 282 | 21.61% |
| No real retest | 41 | 3.14% |
| No rejection candle | 34 | 2.61% |
| No liquidity sweep | 24 | 1.84% |
| RR below minimum | 0 | 0.00% |
| SIGNAL (all stages passed) | 1 | 0.08% |
| **Total scan points** | **1305** | 100% |

**Signal rate:** 1 signals over 3 months = **0.33 signals / month** across 15 pairs

## Per-Pair Funnel

| Pair | HTF | Outside | Chop | No | No | No | No | RR | SIGNAL |
|---|---|---|---|---|---|---|---|---|---|
| AUDJPY | 85 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 |
| AUDUSD | 47 | 0 | 0 | 33 | 3 | 2 | 2 | 0 | 0 |
| CADJPY | 87 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CHFJPY | 87 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| EURAUD | 82 | 0 | 0 | 4 | 0 | 1 | 0 | 0 | 0 |
| EURCHF | 75 | 0 | 0 | 4 | 3 | 2 | 3 | 0 | 0 |
| EURGBP | 35 | 24 | 2 | 20 | 1 | 1 | 4 | 0 | 0 |
| EURJPY | 87 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| EURUSD | 43 | 11 | 1 | 25 | 4 | 1 | 2 | 0 | 0 |
| GBPJPY | 34 | 15 | 0 | 27 | 4 | 4 | 3 | 0 | 0 |
| GBPUSD | 45 | 7 | 0 | 28 | 4 | 2 | 1 | 0 | 0 |
| NZDUSD | 16 | 19 | 0 | 41 | 5 | 4 | 2 | 0 | 0 |
| USDCAD | 29 | 11 | 4 | 31 | 6 | 4 | 2 | 0 | 0 |
| USDCHF | 46 | 1 | 0 | 27 | 6 | 5 | 2 | 0 | 0 |
| USDJPY | 21 | 9 | 0 | 41 | 5 | 7 | 3 | 0 | 1 |

## Bottleneck Analysis

Aligned candidates entering the pipeline: **486**

| Filter | Rejections | % of candidates |
|--------|-----------:|----------------:|
| Breakout | 282 | 58.0% |
| Session filter | 97 | 20.0% |
| Retest | 41 | 8.4% |
| Rejection | 34 | 7.0% |
| Sweep | 24 | 4.9% |
| Chop filter | 7 | 1.4% |
| RR filter | 0 | 0.0% |

**Primary bottleneck: Breakout** — rejected 282 of 486 candidates (58.0%).

## Interpretation Guide

- **HTF not aligned dominates:** watchlist thresholds may be too strict, or pairs are not trending in this window.
- **Session dominates:** most setups happen outside London/NY hours.
- **Breakout dominates:** swing definition is too strict, or price genuinely does not break structure as often as assumed.
- **Retest dominates:** tolerance or max bars may be too tight.
- **Rejection dominates:** wick-ratio threshold may be miscalibrated.
- **Sweep dominates:** sweep definition may not match real price behavior.
- **RR dominates:** TP structure may create poor RR on most setups.
- **Signal count healthy (>1/month):** parameters are calibrated.