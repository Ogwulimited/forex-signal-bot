# Backtest Report — Funnel + Expectancy

Generated: 2026-09-15T22:23:09.490846+00:00  
History window: last 12 months  
Pairs tested: 15  
Scan cadence: every 5th 5M candle (~every 25 min)  
Sweep mode: **force**  
Cooldown between signals: 48 bars (~4.0h)

## Aggregate Funnel

| Stage | Count | % of scan points |
|-------|------:|-----------------:|
| HTF not aligned | 850 | 69.90% |
| Outside London/NY session | 100 | 8.22% |
| Chop filter rejected | 5 | 0.41% |
| No swing breakout | 181 | 14.88% |
| No real retest | 30 | 2.47% |
| No rejection candle | 31 | 2.55% |
| No liquidity sweep | 0 | 0.00% |
| RR below minimum | 0 | 0.00% |
| SIGNAL (all stages passed) | 19 | 1.56% |
| **Total scan points** | **1216** | 100% |

## Expectancy Summary

- Total signals: **19**
- Signals per month: **1.58** across 15 pairs
- Wins: **8**  |  Losses: **11**  |  Expired: **0**
- Win rate: **42.1%**
- Average R per trade: **0.27R**
- Total R over 12 months: **5.09R**
- Average hold time: **4.0 bars** (~0.3h)

**Monthly expectancy (R): 0.42R**

## Per-Pair Results

| Pair | Signals | Wins | Losses | Win% | Total R |
|------|--------:|-----:|-------:|-----:|--------:|
| AUDJPY | 0 | 0 | 0 | 0.0% | 0.0R |
| AUDUSD | 1 | 0 | 1 | 0.0% | -1.0R |
| CADJPY | 0 | 0 | 0 | 0.0% | 0.0R |
| CHFJPY | 0 | 0 | 0 | 0.0% | 0.0R |
| EURAUD | 0 | 0 | 0 | 0.0% | 0.0R |
| EURCHF | 1 | 0 | 1 | 0.0% | -1.0R |
| EURGBP | 3 | 1 | 2 | 33.3% | 0.0R |
| EURJPY | 0 | 0 | 0 | 0.0% | 0.0R |
| EURUSD | 1 | 0 | 1 | 0.0% | -1.0R |
| GBPJPY | 2 | 1 | 1 | 50.0% | 1.0R |
| GBPUSD | 2 | 1 | 1 | 50.0% | 1.0R |
| NZDUSD | 2 | 2 | 0 | 100.0% | 4.0R |
| USDCAD | 2 | 1 | 1 | 50.0% | 1.0R |
| USDCHF | 2 | 1 | 1 | 50.0% | 1.09R |
| USDJPY | 3 | 1 | 2 | 33.3% | 0.0R |

## All Signals (Chronological)

| Date | Pair | Dir | Entry | SL | TP | RR | Outcome | Bars | R |
|------|------|-----|------:|----:|----:|----:|---------|-----:|---:|
| 2026-09-14 08:20 | GBPUSD | sell | 1.34838 | 1.34866 | 1.34782 | 2.00 | win | 11 | +2.00 |
| 2026-09-14 08:20 | EURGBP | sell | 0.85562 | 0.85598 | 0.85490 | 2.00 | loss | 11 | -1.00 |
| 2026-09-14 09:35 | AUDUSD | sell | 0.71248 | 0.71263 | 0.71218 | 2.00 | loss | 1 | -1.00 |
| 2026-09-14 12:45 | EURGBP | sell | 0.85549 | 0.85570 | 0.85507 | 2.00 | loss | 1 | -1.00 |
| 2026-09-14 12:55 | USDCHF | buy | 0.81784 | 0.81762 | 0.81830 | 2.09 | win | 10 | +2.09 |
| 2026-09-14 13:20 | USDCAD | buy | 1.39191 | 1.39151 | 1.39271 | 2.00 | win | 4 | +2.00 |
| 2026-09-14 14:10 | EURUSD | sell | 1.15238 | 1.15264 | 1.15186 | 2.00 | loss | 1 | -1.00 |
| 2026-09-14 14:10 | USDJPY | buy | 154.98200 | 154.91300 | 155.12000 | 2.00 | loss | 1 | -1.00 |
| 2026-09-14 17:35 | EURGBP | sell | 0.85572 | 0.85583 | 0.85550 | 2.00 | win | 4 | +2.00 |
| 2026-09-14 19:35 | NZDUSD | sell | 0.57815 | 0.57823 | 0.57799 | 2.00 | win | 3 | +2.00 |
| 2026-09-14 19:50 | USDJPY | buy | 154.27400 | 154.24100 | 154.34000 | 2.00 | win | 1 | +2.00 |
| 2026-09-15 08:05 | GBPJPY | buy | 208.79300 | 208.68600 | 209.00700 | 2.00 | win | 1 | +2.00 |
| 2026-09-15 12:05 | NZDUSD | sell | 0.57597 | 0.57619 | 0.57553 | 2.00 | win | 4 | +2.00 |
| 2026-09-15 12:15 | EURCHF | buy | 0.94455 | 0.94432 | 0.94501 | 2.00 | loss | 1 | -1.00 |
| 2026-09-15 12:30 | GBPUSD | sell | 1.34800 | 1.34818 | 1.34764 | 2.00 | loss | 1 | -1.00 |
| 2026-09-15 12:55 | USDCAD | buy | 1.39293 | 1.39253 | 1.39373 | 2.00 | loss | 1 | -1.00 |
| 2026-09-15 14:35 | USDCHF | buy | 0.81931 | 0.81896 | 0.82001 | 2.00 | loss | 6 | -1.00 |
| 2026-09-15 15:15 | USDJPY | buy | 155.08300 | 155.01800 | 155.21300 | 2.00 | loss | 8 | -1.00 |
| 2026-09-15 17:05 | GBPJPY | buy | 209.07100 | 209.02000 | 209.17300 | 2.00 | loss | 3 | -1.00 |

## Bottleneck Analysis

Aligned candidates: **366**

| Filter | Rejections | % of candidates |
|--------|-----------:|----------------:|
| Session | 100 | 27.3% |
| Chop | 5 | 1.4% |
| Breakout | 181 | 49.5% |
| Retest | 30 | 8.2% |
| Rejection | 31 | 8.5% |
| Sweep | 0 | 0.0% |
| RR | 0 | 0.0% |
