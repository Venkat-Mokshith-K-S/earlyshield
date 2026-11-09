# Auto-response threshold calibration

36 attack trials, 63 benign trials, 6 ambiguous trials (legit_encrypt: a user encrypting their own files, which no behavioural detector can distinguish from ransomware).

## Highest p(ransomware) per trial, by workload

| Workload | Kind | Trials | Lowest max p | Highest max p |
|---|---|---|---|---|
| legit_encrypt | ambiguous | 6 | 0.75 | 0.91 |
| burst | attack | 9 | 0.92 | 0.95 |
| throttled | attack | 9 | 0.92 | 0.94 |
| copy_delete | attack | 9 | 0.74 | 0.93 |
| slow_inplace | attack | 9 | 0.54 | 0.57 |
| gzip_compress | benign | 6 | 0.78 | 0.91 |
| bulk_rename | benign | 9 | 0.13 | 0.23 |
| zip_archive | benign | 9 | 0.11 | 0.19 |
| media_import | benign | 6 | 0.14 | 0.15 |
| software_install | benign | 6 | 0.14 | 0.14 |
| format_conversion | benign | 9 | 0.06 | 0.08 |
| edit_docs | benign | 9 | 0.02 | 0.06 |
| copy_folder | benign | 9 | 0.02 | 0.04 |

## Trade-off at each threshold

| Threshold | Attack trials that trigger recovery | Benign trials that wrongly trigger it | Ambiguous trials that trigger it |
|---|---|---|---|
| 0.50 | 36/36 | 6/63 | 6/6 |
| 0.55 | 30/36 | 6/63 | 6/6 |
| 0.60 | 27/36 | 6/63 | 6/6 |
| 0.65 | 27/36 | 6/63 | 6/6 |
| 0.70 | 27/36 | 6/63 | 6/6 |
| 0.75 | 26/36 | 6/63 | 6/6 |
| 0.80 | 26/36 | 5/63 | 5/6 |
| 0.85 | 25/36 | 5/63 | 5/6 |
| 0.90 | 19/36 | 2/63 | 4/6 |
