# EarlyShield — Real-Time Evaluation Results

Generated 2026-10-25 07:58 UTC on win32, Python 3.12.10, PollingObserver · corpus of 100 files · auto-response threshold 0.50 · 3 trial(s) per attack configuration.

## Ransomware simulations

TTD = time from the attacker's first encrypted file to the model flagging a window. "Before detection" = files the attacker had already encrypted at that moment. "Lost" = corpus files not byte-identical to the original at the end of the trial, after automated recovery. "Responded" = the detection's confidence reached the auto-response threshold, so files were quarantined and restored; below it EarlyShield only raises an alert. "Confidence" = mean of each trial's highest flagged-window confidence. "Attribution" = share of flagged windows blamed on the attacker's PID.

| Attack | Window | Detected | Responded | Confidence | TTD (s) | Encrypted before detection | Encrypted total | Lost after recovery | Artifacts left | Attribution |
|---|---|---|---|---|---|---|---|---|---|---|
| burst | 2s | 3/3 | 3/3 | 0.94 | 7.4 ± 0.9 | 100.0 ± 0.0 | 100 ± 0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0% |
| burst | 5s | 3/3 | 3/3 | 0.94 | 6.1 ± 1.5 | 100.0 ± 0.0 | 100 ± 0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0% |
| burst | 10s | 3/3 | 3/3 | 0.92 | 6.5 ± 2.3 | 100.0 ± 0.0 | 100 ± 0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0% |
| throttled | 2s | 3/3 | 3/3 | 0.94 | 3.1 ± 3.2 | 31.7 ± 32.4 | 100 ± 0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0% |
| throttled | 5s | 3/3 | 3/3 | 0.94 | 3.5 ± 1.4 | 35.7 ± 13.5 | 100 ± 0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0% |
| throttled | 10s | 3/3 | 3/3 | 0.92 | 3.0 ± 3.3 | 30.3 ± 33.5 | 100 ± 0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0% |
| slow_inplace | 2s | 3/3 | 3/3 | 0.57 | 3.8 ± 1.8 | 8.0 ± 3.5 | 80 ± 0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0% |
| slow_inplace | 5s | 3/3 | 3/3 | 0.55 | 2.3 ± 1.2 | 5.0 ± 2.0 | 80 ± 0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0% |
| slow_inplace | 10s | 3/3 | 3/3 | 0.54 | 6.5 ± 2.3 | 13.7 ± 4.6 | 80 ± 0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0% |
| copy_delete | 2s | 3/3 | 3/3 | 0.85 | 5.9 ± 1.6 | 100.0 ± 0.0 | 100 ± 0 | 4.3 ± 7.5 | 5.3 ± 9.2 | 0% |
| copy_delete | 5s | 3/3 | 3/3 | 0.87 | 4.3 ± 2.6 | 100.0 ± 0.0 | 100 ± 0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0% |
| copy_delete | 10s | 3/3 | 3/3 | 0.89 | 5.4 ± 2.5 | 100.0 ± 0.0 | 100 ± 0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0% |

**Overall:** 36/36 attack trials detected; mean TTD 4.82 s; mean 60.4% of the corpus encrypted before detection; mean 0.4% lost after recovery; mean automated response time 1467 ms.

## Benign workloads (false positives)

A false positive here also triggers the automated response, so "Collateral actions" counts the quarantine/restore actions EarlyShield took on legitimate activity (all reversible: quarantined files are moved into the vault, not deleted).

| Workload | Window | Flagged trials | Flagged windows | Max confidence | Collateral actions |
|---|---|---|---|---|---|
| gzip_compress | 2s | 2/2 | 2/2 | 0.59 | 80 |
| gzip_compress | 5s | 2/2 | 2/3 | 0.65 | 80 |
| gzip_compress | 10s | 2/2 | 2/2 | 0.62 | 80 |
| legit_encrypt (expected alarm) | 2s | 2/2 | 2/2 | 0.89 | 120 |
| legit_encrypt (expected alarm) | 5s | 2/2 | 2/2 | 0.91 | 120 |
| legit_encrypt (expected alarm) | 10s | 2/2 | 2/2 | 0.91 | 120 |

**Overall:** 6/6 benign trials produced at least one false alarm (6/7 windows).
User-initiated encryption (`legit_encrypt`) raised an alarm in 6/6 trials, as expected: it is behaviourally identical to ransomware.

## Charts

![Time to detection](ttd_by_attack.png)

![Damage](damage_by_attack.png)
