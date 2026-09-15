# Backtest Report — Funnel + Expectancy

Generated: 2026-09-15T21:32:18.478922+00:00  
History window: last 3 months  
Pairs tested: 15  
Scan cadence: every 5th 5M candle (~every 25 min)  
Sweep mode: **strict**  
Cooldown between signals: 48 bars (~4.0h)

## Aggregate Funnel

| Stage | Count | % of scan points |
|-------|------:|-----------------:|
| HTF not aligned | 856 | 63.83% |
| Outside London/NY session | 102 | 7.61% |
| Chop filter rejected | 7 | 0.52% |
| No swing breakout | 278 | 20.73% |
| No real retest | 40 | 2.98% |
| No rejection candle | 33 | 2.46% |
| No liquidity sweep | 24 | 1.79% |
| RR below minimum | 0 | 0.00% |
| SIGNAL (all stages passed) | 1 | 0.07% |
| **Total scan points** | **1341** | 100% |

## Expectancy Summary

- Total signals: **1**
- Signals per month: **0.33** across 15 pairs
- Wins: **0**  |  Losses: **0**  |  Expired: **1**
- Win rate: **0.0%**
- Average R per trade: **0.14R**
- Total R over 3 months: **0.14R**
- Average hold time: **53.0 bars** (~4.4h)

**Monthly expectancy (R): 0.05R**

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
| USDJPY | 1 | 0 | 0 | 0.0% | 0.14R |

## All Signals (Chronological)

| Date | Pair | Dir | Entry | SL | TP | RR | Outcome | Bars | R |
|------|------|-----|------:|----:|----:|----:|---------|-----:|---:|
| 2026-09-15 17:15 | USDJPY | buy | 155.12700 | 155.03400 | 155.31300 | 2.00 | expired | 53 | +0.00 |

## Bottleneck Analysis

Aligned candidates: **485**

| Filter | Rejections | % of candidates |
|--------|-----------:|----------------:|
| Session | 102 | 21.0% |
| Chop | 7 | 1.4% |
| Breakout | 278 | 57.3% |
| Retest | 40 | 8.2% |
| Rejection | 33 | 6.8% |
| Sweep | 24 | 4.9% |
| RR | 0 | 0.0% |
