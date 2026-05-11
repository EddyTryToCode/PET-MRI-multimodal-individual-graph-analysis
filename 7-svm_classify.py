#!/usr/bin/env python3
"""
SVM Classification on Brain Connectivity Matrices
====================================================
Reproduces the EUSIPCO 2024 paper methodology: SVM with 5-fold stratified
cross-validation on flattened upper-triangular Wasserstein-based adjacency
matrices for Alzheimer's disease stage classification.

Input:
    ./Project_Data/sub-{id}/sub-{id}_Adjacency_Matrix.npy
    ./data.csv  (columns: Subject, Group)

Output:
    ./QC_SVM_Results/ROC_Curve_{TASK}.png
    ./QC_SVM_Results/Confusion_Matrix_{TASK}.png

Dependencies:
    pip install scikit-learn numpy pandas matplotlib seaborn

Usage:
    python svm_classify.py
"""

import os
import sys
import glob
import warnings

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    accuracy_score,
    recall_score,
    roc_auc_score,
    roc_curve,
    confusion_matrix,
    classification_report,
)

warnings.filterwarnings("ignore", category=FutureWarning)


# ══════════════════════════════════════════════════════════════
# Configuration — CHANGE THESE TO SWITCH TASKS
# ══════════════════════════════════════════════════════════════
PROJECT_DIR = "./Project_Data"
CSV_PATH = "./data_balanced.csv"
OUTPUT_DIR = "./QC_SVM_Results"

# Binary classification task: pick two groups
# Options: ("CN", "AD"), ("CN", "MCI"), ("MCI", "AD")
POSITIVE_CLASS = "AD"
NEGATIVE_CLASS = "CN"

TASK_NAME = f"{NEGATIVE_CLASS}_vs_{POSITIVE_CLASS}"

# Label encoding
LABEL_MAP = {NEGATIVE_CLASS: 0, POSITIVE_CLASS: 1}

# Cross-validation
N_SPLITS = 5
RANDOM_STATE = 42


# ══════════════════════════════════════════════════════════════
# Data loading
# ══════════════════════════════════════════════════════════════

def load_data():
    """
    Load adjacency matrices and labels for the selected binary task.

    Returns:
        X: np.ndarray [n_subjects, n_features]  (upper-triangular features)
        y: np.ndarray [n_subjects]               (binary labels)
        subjects: list of subject IDs
    """
    df = pd.read_csv(CSV_PATH)

    # Build subject → group mapping (deduplicate across PET/MRI rows)
    subj_group = {}
    for _, row in df.iterrows():
        subj = row["Subject"]
        group = row["Group"]
        if subj not in subj_group:
            subj_group[subj] = group

    # Filter to selected classes only
    valid_subjects = {s: g for s, g in subj_group.items() if g in LABEL_MAP}

    X_list = []
    y_list = []
    subjects = []

    sub_dirs = sorted(glob.glob(os.path.join(PROJECT_DIR, "sub-*")))

    for sub_dir in sub_dirs:
        sub_label = os.path.basename(sub_dir)           # sub-002_S_0685
        sub_id = sub_label.replace("sub-", "")           # 002_S_0685
        npy_path = os.path.join(sub_dir, f"{sub_label}_Adjacency_Matrix.npy")

        if sub_id not in valid_subjects:
            continue
        if not os.path.isfile(npy_path):
            print(f"  [WARN] Missing .npy for {sub_label}, skipping")
            continue

        try:
            A = np.load(npy_path)
            # Extract upper triangular (excluding diagonal) → 1D feature vector
            features = A[np.triu_indices_from(A, k=1)]

            X_list.append(features)
            y_list.append(LABEL_MAP[valid_subjects[sub_id]])
            subjects.append(sub_id)

        except Exception as e:
            print(f"  [WARN] Error loading {sub_label}: {e}")

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int64)

    return X, y, subjects


# ══════════════════════════════════════════════════════════════
# Evaluation
# ══════════════════════════════════════════════════════════════

def run_cross_validation(X, y):
    """
    5-fold stratified CV with linear SVM.

    Returns per-fold metrics and data for plotting.
    """
    skf = StratifiedKFold(
        n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE
    )

    pipeline = make_pipeline(
        StandardScaler(),
        SVC(kernel="linear", probability=True, class_weight="balanced",
            random_state=RANDOM_STATE),
    )

    # Storage
    fold_acc = []
    fold_sens = []
    fold_spec = []
    fold_auc = []
    tprs = []
    mean_fpr = np.linspace(0, 1, 100)
    all_y_true = []
    all_y_pred = []

    print(f"\n{'='*60}")
    print(f"  {N_SPLITS}-Fold Stratified CV  —  {TASK_NAME}")
    print(f"{'='*60}\n")

    for fold, (train_idx, test_idx) in enumerate(skf.split(X, y), start=1):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        pipeline.fit(X_train, y_train)

        y_pred = pipeline.predict(X_test)
        y_prob = pipeline.predict_proba(X_test)[:, 1]

        # Metrics
        acc = accuracy_score(y_test, y_pred)
        sens = recall_score(y_test, y_pred, pos_label=1)     # Sensitivity
        spec = recall_score(y_test, y_pred, pos_label=0)     # Specificity
        auc = roc_auc_score(y_test, y_prob)

        fold_acc.append(acc)
        fold_sens.append(sens)
        fold_spec.append(spec)
        fold_auc.append(auc)

        # ROC interpolation for mean curve
        fpr, tpr, _ = roc_curve(y_test, y_prob)
        interp_tpr = np.interp(mean_fpr, fpr, tpr)
        interp_tpr[0] = 0.0
        tprs.append(interp_tpr)

        # Accumulate predictions for aggregate confusion matrix
        all_y_true.extend(y_test)
        all_y_pred.extend(y_pred)

        print(
            f"  Fold {fold}: "
            f"Acc={acc:.3f}  Sens={sens:.3f}  Spec={spec:.3f}  AUC={auc:.3f}"
        )

    # Aggregate metrics
    results = {
        "accuracy": (np.mean(fold_acc), np.std(fold_acc)),
        "sensitivity": (np.mean(fold_sens), np.std(fold_sens)),
        "specificity": (np.mean(fold_spec), np.std(fold_spec)),
        "auc": (np.mean(fold_auc), np.std(fold_auc)),
    }

    print(f"\n{'─'*60}")
    print(f"  Mean results across {N_SPLITS} folds:")
    for metric, (mean, std) in results.items():
        print(f"    {metric.capitalize():>12s}: {mean:.4f} ± {std:.4f}")
    print(f"{'─'*60}")

    return results, tprs, mean_fpr, all_y_true, all_y_pred


# ══════════════════════════════════════════════════════════════
# Visualization
# ══════════════════════════════════════════════════════════════

def plot_roc_curve(tprs, mean_fpr, results, output_path):
    """Plot mean ROC curve with ±1 std confidence band."""
    fig, ax = plt.subplots(figsize=(7, 6))

    # Individual fold curves (light)
    mean_tpr = np.mean(tprs, axis=0)
    std_tpr = np.std(tprs, axis=0)
    mean_tpr[-1] = 1.0

    mean_auc, std_auc = results["auc"]

    # Confidence band
    tpr_upper = np.minimum(mean_tpr + std_tpr, 1)
    tpr_lower = np.maximum(mean_tpr - std_tpr, 0)
    ax.fill_between(mean_fpr, tpr_lower, tpr_upper, alpha=0.2, color="royalblue")

    # Mean ROC
    ax.plot(
        mean_fpr, mean_tpr, color="royalblue", lw=2,
        label=f"Mean ROC (AUC = {mean_auc:.3f} ± {std_auc:.3f})"
    )

    # Diagonal
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5, label="Chance")

    ax.set_xlim([-0.02, 1.02])
    ax.set_ylim([-0.02, 1.02])
    ax.set_xlabel("False Positive Rate", fontsize=12)
    ax.set_ylabel("True Positive Rate", fontsize=12)
    ax.set_title(f"ROC Curve — {TASK_NAME}  ({N_SPLITS}-Fold CV)", fontsize=13)
    ax.legend(loc="lower right", fontsize=10)
    ax.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    print(f"\n  [SAVED] {output_path}")


def plot_confusion_matrix(y_true, y_pred, output_path):
    """Plot aggregate confusion matrix from all folds."""
    cm = confusion_matrix(y_true, y_pred)
    labels = [NEGATIVE_CLASS, POSITIVE_CLASS]

    fig, ax = plt.subplots(figsize=(5, 4.5))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=labels, yticklabels=labels,
        ax=ax, square=True,
        cbar_kws={"label": "Count"},
        annot_kws={"size": 16},
    )
    ax.set_xlabel("Predicted", fontsize=12)
    ax.set_ylabel("Actual", fontsize=12)
    ax.set_title(f"Confusion Matrix — {TASK_NAME}  ({N_SPLITS}-Fold CV)", fontsize=13)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    print(f"  [SAVED] {output_path}")


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load data
    print(f"[INFO] Task: {TASK_NAME}")
    print(f"[INFO] Loading adjacency matrices ...")
    X, y, subjects = load_data()

    n_neg = np.sum(y == 0)
    n_pos = np.sum(y == 1)
    print(f"[INFO] Loaded {len(y)} subjects  "
          f"({NEGATIVE_CLASS}: {n_neg}, {POSITIVE_CLASS}: {n_pos})")
    print(f"[INFO] Feature vector length: {X.shape[1]} "
          f"(upper triangle of {int(np.sqrt(X.shape[1]*2))}×{int(np.sqrt(X.shape[1]*2))} matrix)")

    if len(y) < N_SPLITS:
        print("[ERROR] Not enough samples for cross-validation")
        sys.exit(1)

    # Run 5-fold CV
    results, tprs, mean_fpr, y_true, y_pred = run_cross_validation(X, y)

    # Plots
    roc_path = os.path.join(OUTPUT_DIR, f"ROC_Curve_{TASK_NAME}.png")
    cm_path = os.path.join(OUTPUT_DIR, f"Confusion_Matrix_{TASK_NAME}.png")

    plot_roc_curve(tprs, mean_fpr, results, roc_path)
    plot_confusion_matrix(y_true, y_pred, cm_path)

    # Full classification report
    print(f"\n  Classification Report (aggregated):")
    print(classification_report(
        y_true, y_pred,
        target_names=[NEGATIVE_CLASS, POSITIVE_CLASS],
        digits=4,
    ))


if __name__ == "__main__":
    main()
