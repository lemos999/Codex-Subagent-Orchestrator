# MTS-V1 Core5 Parity Report

- Profile: `15m/core5/symbol-RSM`
- Python JSONL: `runs\mtsv1_improve_core5_symbol_rsm_best5_nol3cap\trades.jsonl`

| Symbol | Status | TV CSV | TV rows | Py candidates | Entry matches | Exit time | Exit price <=0.15 | Exit price <=1.0 | Avg exit delta | Max exit delta |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BTC | partial_entry_match | `samples\tradingview_mtsv1_BTC_entry15_raw.csv` | 64 | 89 | 11 | 9 | 0 | 0 | 345.0004 | 1362.6042 |
| ETH | partial_entry_match | `samples\tradingview_mtsv1_ETH_raw.csv` | 32 | 97 | 3 | 0 | 0 | 0 | 17.6442 | 18.8663 |
| SOL | no_entry_matches | `samples\tradingview_mtsv1_SOL_raw.csv` | 27 | 99 | 0 | 0 | 0 | 0 |  |  |
| XRP | no_entry_matches | `samples\tradingview_mtsv1_XRP_raw.csv` | 27 | 91 | 0 | 0 | 0 | 0 |  |  |
| BNB | partial_entry_match | `samples\tradingview_mtsv1_BNB_raw.csv` | 28 | 133 | 2 | 0 | 0 | 1 | 2.1450 | 3.9800 |

## Criteria
- This batch report classifies current Core5 mismatches against one Python artifact.
- For BTC exact parity, run `btc_parity_diff.py` and `btc_parity_trace.py` against the exact BTC artifact.
- ETH/SOL/XRP/BNB rows classify current mismatches; they are not PASS claims.
- `missing_tv_csv` means no raw TradingView CSV was found for that symbol.
