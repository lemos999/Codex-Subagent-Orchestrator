# MTS-V1 Core5 Parity Report

- Profile: `15m/core5/symbol-RSM`
- Timeframes: entry `15m`, execution `15m`, HTF `4h`
- Symbol RSM: `{'BTC': 6.3, 'ETH': 6.8, 'SOL': 5.5, 'XRP': 6.3, 'BNB': 2.5}`
- Python JSONL: per-symbol exact artifact

| Symbol | Status | Class | TV capture | TV CSV | Python artifact | Detail reports | TV rows | Common TV rows | Py entries | Py candidates | Entry matches | Exit time | Exit price <=0.15 | Exit price <=1.0 | Avg exit delta | Max exit delta |
|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BTC | exit_price_mismatch | semantic_replay_mismatch | entry15_raw | `samples\tradingview_mtsv1_BTC_entry15_raw.csv` | `runs\mtsv1_tv_btc_15m_binanceusdm_profile\trades.jsonl` | `parity_reports\btc_diff_entry15.md` / `parity_reports\btc_trace_entry15.md` | 64 | 64 | 107 | 64 | 64 | 64 | 62 | 64 | 0.0420 | 0.1794 |
| ETH | partial_entry_match | semantic_replay_mismatch | entry15_raw | `samples\tradingview_mtsv1_ETH_entry15_raw.csv` | `runs\mtsv1_tv_eth_15m_binanceusdm_profile\trades.jsonl` | `parity_reports\eth_diff_entry15.md` / `parity_reports\eth_trace_entry15.md` | 69 | 65 | 118 | 63 | 48 | 41 | 16 | 37 | 2.3231 | 18.5200 |
| SOL | partial_entry_match | semantic_replay_mismatch | entry15_raw | `samples\tradingview_mtsv1_SOL_entry15_raw.csv` | `runs\mtsv1_tv_sol_15m_binanceusdm_profile\trades.jsonl` | `parity_reports\sol_diff_entry15.md` / `parity_reports\sol_trace_entry15.md` | 71 | 69 | 121 | 67 | 40 | 27 | 33 | 40 | 0.0947 | 0.5500 |
| XRP | partial_entry_match | semantic_replay_mismatch | entry15_raw | `samples\tradingview_mtsv1_XRP_entry15_raw.csv` | `runs\mtsv1_tv_xrp_15m_binanceusdm_profile\trades.jsonl` | `parity_reports\xrp_diff_entry15.md` / `parity_reports\xrp_trace_entry15.md` | 58 | 52 | 127 | 63 | 24 | 13 | 24 | 24 | 0.0074 | 0.0214 |
| BNB | partial_entry_match | semantic_replay_mismatch | entry15_raw | `samples\tradingview_mtsv1_BNB_entry15_raw.csv` | `runs\mtsv1_tv_bnb_15m_binanceusdm_profile\trades.jsonl` | `parity_reports\bnb_diff_entry15.md` / `parity_reports\bnb_trace_entry15.md` | 85 | 77 | 130 | 67 | 38 | 25 | 1 | 27 | 1.0154 | 3.5800 |

## Coverage / Gate

| Symbol | TV rows | Common TV rows | TV before Python artifact | TV tail after Python artifact | Trade numbers contiguous | Python SHA256 | Gate | Gate failures |
|---|---:|---:|---:|---:|---|---|---|---|
| BTC | 64 | 64 | 0 | 0 | true | BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D | pass |  |
| ETH | 69 | 65 | 0 | 4 | true | 8DBA14C1F05FD6C4BD329173C7F767440B095773B71FFA1AFD37DFD9A4448734 | pass |  |
| SOL | 71 | 69 | 0 | 2 | true | EEC7A0BD5C1D8B61A78E66AB88DF9A66F802EB754A4AB625D28809922CCE1AF8 | pass |  |
| XRP | 58 | 52 | 0 | 6 | true | DBE98E62F95E2C68EC231381CC72C21CEA56CDA8D07EF001B2C308D3C1D0A49C | pass |  |
| BNB | 85 | 77 | 0 | 8 | true | 75A9E6464BA5E5A82C0695325E441F09763593819A301F2F7BDF9B73A33DDCBD | pass |  |

## Ranges

| Symbol | TV entry range | Python filled-entry range |
|---|---|---|
| BTC | 2026-03-07T03:15:00Z to 2026-04-24T14:45:00Z | 2026-01-25T11:00:00Z to 2026-04-24T14:45:00Z |
| ETH | 2026-03-06T21:30:00Z to 2026-04-24T21:30:00Z | 2026-01-24T09:15:00Z to 2026-04-24T02:45:00Z |
| SOL | 2026-03-06T08:15:00Z to 2026-04-25T11:15:00Z | 2026-01-24T06:30:00Z to 2026-04-23T17:00:00Z |
| XRP | 2026-03-06T08:30:00Z to 2026-04-25T09:15:00Z | 2026-01-24T14:00:00Z to 2026-04-23T13:30:00Z |
| BNB | 2026-03-06T21:30:00Z to 2026-04-26T13:15:00Z | 2026-01-24T07:30:00Z to 2026-04-23T08:15:00Z |

## Capture Inventory

| Symbol | TV capture | TV CSV mtime | Python artifact mtime | RSM | Entry TF | Execution TF | HTF |
|---|---|---|---|---:|---|---|---|
| BTC | entry15_raw | 2026-04-25T04:30:24.860382Z | 2026-04-26T05:36:20.692582Z | 6.3 | 15m | 15m | 4h |
| ETH | entry15_raw | 2026-04-26T14:34:43.951319Z | 2026-04-26T05:38:59.863680Z | 6.8 | 15m | 15m | 4h |
| SOL | entry15_raw | 2026-04-26T14:38:55.628834Z | 2026-04-27T05:34:24.925695Z | 5.5 | 15m | 15m | 4h |
| XRP | entry15_raw | 2026-04-26T14:41:08.261407Z | 2026-04-26T05:38:59.711518Z | 6.3 | 15m | 15m | 4h |
| BNB | entry15_raw | 2026-04-26T14:36:44.707775Z | 2026-04-26T05:39:00.074158Z | 2.5 | 15m | 15m | 4h |

## Criteria
- This batch report classifies current Core5 mismatches against per-symbol exact artifacts.
- Semantic match metrics use `Common TV rows` as the denominator; raw `TV rows` preserve the full capture inventory.
- TV rows outside the Python artifact filled-entry range are counted as before/tail coverage, not semantic replay failures.
- Detail reports are generated with the same diff/trace logic used for BTC parity.
- ETH/SOL/XRP/BNB rows classify current mismatches; they are not PASS claims.
- `missing_tv_csv` means no raw TradingView CSV was found for that symbol.
- `missing_exact_cache` means no per-symbol exact Python artifact was found.
- `data_window_mismatch` means the available TV/Python ranges or candidates are insufficient for semantic comparison.
- `profile_input_mismatch` means the TV capture is not the verified `*_entry15_raw.csv` export, so semantic replay debugging is deferred until capture refresh.
- `semantic_replay_mismatch` means comparable rows exist but entry/exit semantics still diverge.
