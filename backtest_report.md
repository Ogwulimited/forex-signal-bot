# Backtest Report — Funnel + Expectancy

Generated: 2026-09-15T21:17:57.722403+00:00  
History window: last 3 months  
Pairs tested: 15  
Scan cadence: every 5th 5M candle (~every 25 min)  
Sweep mode: **strict**  
Cooldown between signals: 48 bars (~4.0h)

## Aggregate Funnel

| Stage | Count | % of scan points |
|-------|------:|-----------------:|
| HTF not aligned | 845 | 63.68% |
| Outside London/NY session | 99 | 7.46% |
| Chop filter rejected | 7 | 0.53% |
| No swing breakout | 278 | 20.95% |
| No real retest | 40 | 3.01% |
| No rejection candle | 33 | 2.49% |
| No liquidity sweep | 24 | 1.81% |
| RR below minimum | 0 | 0.00% |
| SIGNAL (all stages passed) | 1 | 0.08% |
| **Total scan points** | **1327** | 100% |

## Expectancy Summary

- Total signals: **1**
- Signals per month: **0.33** across 15 pairs
- Wins: **0**  |  Losses: **0**  |  Expired: **1**
- Win rate: **0.0%**
- Average R per trade: **0.12R**
- Total R over 3 months: **0.12R**
- Average hold time: **50.0 bars** (~4.2h)

**Monthly expectancy (R): 0.04R**

## Per-Pair Results

| Pair | Signals | Wins | Losses | Win% | Total R |
|------|--------:|-----:|-------:|-----:|--------:|
| AUDJPY | 0 | 0 | 0 | 0.0% | 0.0R |
| AUDUSD | 0 | 0 | 0 | 0.0% | 0.0R |
| CADJPY | 0 | 0 | 0 | 0.0% | 0.0R |
| CHFJPY | 0 | 0 | 0 | 0.0% | 0.0R |
| EURAUD | 0 | 0 | 0 | 0.0% | 0.0R |
| EURCHF | 0 | 0 | 0 | 0.0% | 0.0R |
| EURGBP | 0 | 0 | 0 | 0.0% | 0.0R |
| EURJPY | 0 | 0 | 0 | 0.0% | 0.0R |
| EURUSD | 0 | 0 | 0 | 0.0% | 0.0R |
| GBPJPY | 0 | 0 | 0 | 0.0% | 0.0R |
| GBPUSD | 0 | 0 | 0 | 0.0% | 0.0R |
| NZDUSD | 0 | 0 | 0 | 0.0% | 0.0R |
| USDCAD | 0 | 0 | 0 | 0.0% | 0.0R |
| USDCHF | 0 | 0 | 0 | 0.0% | 0.0R |
| USDJPY | 1 | 0 | 0 | 0.0% | 0.12R |

## All Signals (Chronological)

| Date | Pair | Dir | Entry | SL | TP | RR | Outcome | Bars | R |
|------|------|-----|------:|----:|----:|----:|---------|-----:|---:|
| 2026-09-15 17:15 | USDJPY | buy | 155.12700 | 155.03400 | 155.31300 | 2.00 | expired | 50 | +0.00 |

## Bottleneck Analysis

Aligned candidates: **482**

| Filter | Rejections | % of candidates |
|--------|-----------:|----------------:|
| Session | 99 | 20.5% |
| Chop | 7 | 1.5% |
| Breakout | 278 | 57.7% |
| Retest | 40 | 8.3% |
| Rejection | 33 | 6.8% |
| Sweep | 24 | 5.0% |
| RR | 0 | 0.0% |
