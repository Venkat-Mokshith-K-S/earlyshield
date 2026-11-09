"""
Synthetic behavioral dataset generator for EarlyShield.

WHY SYNTHETIC DATA:
Training on real ransomware requires executing live malware, which is
unsafe, illegal without a properly isolated sandbox/BSL, and out of scope
for an academic mini-project. Instead, we simulate the *behavioral
signatures* documented in the ransomware-detection literature (Hirano &
Kobayashi 2019; Urooj et al. 2022; Vehabovic et al. 2023 — see project
References): abnormal file modification bursts, entropy spikes from
encryption, high rename/extension-change rates, and elevated process I/O.

Each feature's benign vs. ransomware distribution is deliberately
overlapping (not perfectly separable) — real endpoint telemetry is noisy,
and a trivial threshold rule would defeat the point of using ML at all.
This is enforced with two sub-populations per class: legitimate "bursty"
software (backups, compilers, media transcoding) that superficially looks
busy like ransomware, and "stealthy" low-and-slow ransomware that throttles
itself to evade rate-based detection.

FEATURES (all computed over a fixed observation window, e.g. 10 seconds):
  file_modification_rate, file_rename_rate, file_deletion_rate,
  entropy_mean, entropy_delta, extension_change_ratio, unique_dirs_touched,
  avg_size_change_ratio, process_cpu_percent, io_write_rate_mb_s,
  read_write_ratio

LABEL: 0 = benign, 1 = ransomware-like
"""

import numpy as np
import pandas as pd

RANDOM_SEED = 42
N_PER_CLASS = 6000


def generate_benign(n, rng):
    n_normal = int(n * 0.80)
    n_bursty = n - n_normal

    normal = pd.DataFrame({
        "file_modification_rate": rng.gamma(1.5, 1.2, n_normal),
        "file_rename_rate": rng.gamma(0.8, 0.3, n_normal),
        "file_deletion_rate": rng.gamma(0.6, 0.25, n_normal),
        "entropy_mean": np.clip(rng.normal(4.2, 1.2, n_normal), 0, 8),
        "entropy_delta": rng.normal(0.15, 0.6, n_normal),
        "extension_change_ratio": rng.beta(1.2, 12, n_normal),
        "unique_dirs_touched": rng.poisson(1.8, n_normal),
        "avg_size_change_ratio": np.maximum(rng.normal(1.02, 0.10, n_normal), 0.5),
        "process_cpu_percent": np.clip(rng.gamma(2.0, 6.0, n_normal), 0, 100),
        "io_write_rate_mb_s": rng.gamma(1.2, 0.8, n_normal),
        "read_write_ratio": np.maximum(rng.normal(2.4, 1.2, n_normal), 0.1),
    })

    bursty = pd.DataFrame({
        "file_modification_rate": rng.gamma(4.5, 5.5, n_bursty),
        "file_rename_rate": rng.gamma(1.5, 1.2, n_bursty),
        "file_deletion_rate": rng.gamma(1.0, 0.8, n_bursty),
        "entropy_mean": np.clip(rng.normal(5.0, 1.3, n_bursty), 0, 8),
        "entropy_delta": rng.normal(0.6, 0.7, n_bursty),
        "extension_change_ratio": rng.beta(1.5, 10, n_bursty),
        "unique_dirs_touched": rng.poisson(4.5, n_bursty),
        "avg_size_change_ratio": np.maximum(rng.normal(1.08, 0.15, n_bursty), 0.5),
        "process_cpu_percent": np.clip(rng.gamma(5.0, 9.0, n_bursty), 0, 100),
        "io_write_rate_mb_s": rng.gamma(4.0, 3.0, n_bursty),
        "read_write_ratio": np.maximum(rng.normal(1.8, 0.9, n_bursty), 0.1),
    })

    return pd.concat([normal, bursty], ignore_index=True)


def generate_ransomware(n, rng):
    n_typical = int(n * 0.75)
    n_stealthy = n - n_typical

    typical = pd.DataFrame({
        "file_modification_rate": rng.gamma(6.0, 7.0, n_typical),
        "file_rename_rate": rng.gamma(5.0, 5.5, n_typical),
        "file_deletion_rate": rng.gamma(2.5, 2.0, n_typical),
        "entropy_mean": np.clip(rng.normal(7.5, 0.5, n_typical), 0, 8),
        "entropy_delta": rng.normal(2.8, 1.0, n_typical),
        "extension_change_ratio": rng.beta(8, 2.5, n_typical),
        "unique_dirs_touched": rng.poisson(8.5, n_typical),
        "avg_size_change_ratio": np.maximum(rng.normal(1.15, 0.22, n_typical), 0.5),
        "process_cpu_percent": np.clip(rng.gamma(6.0, 9.0, n_typical), 0, 100),
        "io_write_rate_mb_s": rng.gamma(5.0, 4.0, n_typical),
        "read_write_ratio": np.maximum(rng.normal(1.1, 0.5, n_typical), 0.05),
    })

    stealthy = pd.DataFrame({
        "file_modification_rate": rng.gamma(1.8, 1.8, n_stealthy),
        "file_rename_rate": rng.gamma(1.2, 0.9, n_stealthy),
        "file_deletion_rate": rng.gamma(0.7, 0.5, n_stealthy),
        "entropy_mean": np.clip(rng.normal(6.6, 0.9, n_stealthy), 0, 8),
        "entropy_delta": rng.normal(1.6, 0.8, n_stealthy),
        "extension_change_ratio": rng.beta(3.5, 4, n_stealthy),
        "unique_dirs_touched": rng.poisson(2.8, n_stealthy),
        "avg_size_change_ratio": np.maximum(rng.normal(1.10, 0.15, n_stealthy), 0.5),
        "process_cpu_percent": np.clip(rng.gamma(2.5, 6.5, n_stealthy), 0, 100),
        "io_write_rate_mb_s": rng.gamma(1.8, 1.3, n_stealthy),
        "read_write_ratio": np.maximum(rng.normal(1.6, 0.7, n_stealthy), 0.05),
    })

    return pd.concat([typical, stealthy], ignore_index=True)


def build_dataset(n_per_class=N_PER_CLASS, seed=RANDOM_SEED, label_noise=0.02):
    rng = np.random.default_rng(seed)
    benign = generate_benign(n_per_class, rng)
    benign["label"] = 0
    ransomware = generate_ransomware(n_per_class, rng)
    ransomware["label"] = 1

    df = pd.concat([benign, ransomware], ignore_index=True)

    feature_cols = [c for c in df.columns if c != "label"]
    for col in feature_cols:
        noise_scale = df[col].std() * 0.08
        df[col] = df[col] + rng.normal(0, noise_scale, size=len(df))
        if col != "entropy_delta":
            df[col] = df[col].clip(lower=0)

    n_flip = int(len(df) * label_noise)
    flip_idx = rng.choice(df.index, size=n_flip, replace=False)
    df.loc[flip_idx, "label"] = 1 - df.loc[flip_idx, "label"]

    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df


if __name__ == "__main__":
    df = build_dataset()
    df.to_csv("data/behavioral_dataset.csv", index=False)
    print(f"Generated {len(df)} samples -> data/behavioral_dataset.csv")
    print(df.groupby("label").size())
