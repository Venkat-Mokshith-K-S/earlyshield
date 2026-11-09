# EarlyShield — Real-Time Evaluation Results

Generated 2026-10-25 06:04 UTC on win32, Python 3.12.10, PollingObserver · corpus of 100 files · auto-response threshold 0.75 · 0 trial(s) per attack configuration.

## Ransomware simulations

TTD = time from the attacker's first encrypted file to the model flagging a window. "Before detection" = files the attacker had already encrypted at that moment. "Lost" = corpus files not byte-identical to the original at the end of the trial, after automated recovery. "Responded" = the detection's confidence reached the auto-response threshold, so files were quarantined and restored; below it EarlyShield only raises an alert. "Confidence" = mean of each trial's highest flagged-window confidence. "Attribution" = share of flagged windows blamed on the attacker's PID.

| Attack | Window | Detected | Responded | Confidence | TTD (s) | Encrypted before detection | Encrypted total | Lost after recovery | Artifacts left | Attribution |
|---|---|---|---|---|---|---|---|---|---|---|

## Benign workloads (false positives)

A false positive here also triggers the automated response, so "Collateral actions" counts the quarantine/restore actions EarlyShield took on legitimate activity (all reversible: quarantined files are moved into the vault, not deleted).

| Workload | Window | Flagged trials | Flagged windows | Max confidence | Collateral actions |
|---|---|---|---|---|---|
| edit_docs | 2s | 0/2 | 0/12 | — | 0 |
| edit_docs | 5s | 0/2 | 0/7 | — | 0 |
| edit_docs | 10s | 0/2 | 0/5 | — | 0 |
| bulk_rename | 2s | 0/2 | 0/2 | — | 0 |
| bulk_rename | 5s | 0/2 | 0/3 | — | 0 |
| bulk_rename | 10s | 0/2 | 0/2 | — | 0 |
| zip_archive | 2s | 0/2 | 0/2 | — | 0 |
| zip_archive | 5s | 0/2 | 0/2 | — | 0 |
| zip_archive | 10s | 0/2 | 0/2 | — | 0 |
| copy_folder | 2s | 0/2 | 0/2 | — | 0 |
| copy_folder | 5s | 0/2 | 0/2 | — | 0 |
| copy_folder | 10s | 0/2 | 0/2 | — | 0 |
| format_conversion | 2s | 0/2 | 0/2 | — | 0 |
| format_conversion | 5s | 0/2 | 0/3 | — | 0 |
| format_conversion | 10s | 0/2 | 0/2 | — | 0 |
| software_install | 2s | 0/2 | 0/2 | — | 0 |
| software_install | 5s | 0/2 | 0/2 | — | 0 |
| software_install | 10s | 0/2 | 0/2 | — | 0 |
| media_import | 2s | 0/2 | 0/2 | — | 0 |
| media_import | 5s | 0/2 | 0/4 | — | 0 |
| media_import | 10s | 0/2 | 0/2 | — | 0 |
| gzip_compress | 2s | 2/2 | 2/2 | 0.90 | 80 |
| gzip_compress | 5s | 2/2 | 2/2 | 0.89 | 80 |
| gzip_compress | 10s | 2/2 | 2/2 | 0.91 | 80 |
| legit_encrypt | 2s | 2/2 | 2/2 | 0.89 | 120 |
| legit_encrypt | 5s | 2/2 | 2/2 | 0.90 | 120 |
| legit_encrypt | 10s | 2/2 | 2/2 | 0.91 | 120 |

**Overall:** 12/54 benign trials produced at least one false alarm (12/76 windows).

## Charts

![Time to detection](ttd_by_attack.png)

![Damage](damage_by_attack.png)
