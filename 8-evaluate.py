#!/usr/bin/env python3
"""Evaluation utilities for classification results."""

import os

import numpy as np
import pandas as pd
import yaml

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.metrics import (
    balanced_accuracy_score,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)

CONFIG_PATH = "configs/default.yaml"
PREDICTIONS_PATH = "outputs/results/test_predictions.csv"


def load_config(path: str = CONFIG_PATH) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def plot_roc(y_true: np.ndarray, y_prob: np.ndarray, out_path: str) -> None:
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    auc_val = roc_auc_score(y_true, y_prob)
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, lw=2, label=f"AUC = {auc_val:.3f}")
    plt.plot([0, 1], [0, 1], "k--", lw=1)
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def plot_confusion(
    y_true: np.ndarray, y_pred: np.ndarray, labels: list, out_path: str
) -> None:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    fig, ax = plt.subplots(figsize=(4, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    for i in range(2):
        for j in range(2):
            color = "white" if cm[i, j] > cm.max() / 2 else "black"
            ax.text(j, i, str(cm[i, j]), ha="center", va="center", color=color)
    fig.colorbar(im, ax=ax)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def plot_group_adjacency(
    meta_df: pd.DataFrame,
    proc_dir: str,
    out_path: str,
    graph_tag: str = "A_fused",
) -> None:
    cn_mats = []
    ad_mats = []
    for _, row in meta_df.iterrows():
        sid = row["subject_id"]
        path = os.path.join(proc_dir, sid, f"{sid}_{graph_tag}.npy")
        if not os.path.isfile(path):
            continue
        A = np.load(path)
        if row["label"] == "AD":
            ad_mats.append(A)
        else:
            cn_mats.append(A)

    if not cn_mats or not ad_mats:
        print("[SKIP] Not enough matrices for group adjacency")
        return

    cn_mean = np.mean(np.stack(cn_mats), axis=0)
    ad_mean = np.mean(np.stack(ad_mats), axis=0)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, mat, title in zip(axes, [cn_mean, ad_mean], ["CN mean", "AD mean"]):
        im = ax.imshow(mat, cmap="hot", vmin=0, vmax=1)
        ax.set_title(title)
        fig.colorbar(im, ax=ax)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def compute_roi_importance(
    meta_df: pd.DataFrame,
    labels_df: pd.DataFrame,
    proc_dir: str,
    out_path: str,
    graph_tag: str = "A_fused",
    top_k: int = 30,
) -> None:
    roi_ids = labels_df["roi_id"].tolist()
    roi_names = labels_df["roi_name"].tolist()

    cn_mats = []
    ad_mats = []
    for _, row in meta_df.iterrows():
        sid = row["subject_id"]
        path = os.path.join(proc_dir, sid, f"{sid}_{graph_tag}.npy")
        if not os.path.isfile(path):
            continue
        A = np.load(path)
        if row["label"] == "AD":
            ad_mats.append(A)
        else:
            cn_mats.append(A)

    if not cn_mats or not ad_mats:
        print("[SKIP] Not enough matrices for ROI importance")
        return

    cn_mean = np.mean(np.stack(cn_mats), axis=0)
    ad_mean = np.mean(np.stack(ad_mats), axis=0)
    diff = ad_mean - cn_mean

    n = diff.shape[0]
    tri = np.triu_indices(n, k=1)
    scores = np.abs(diff[tri])
    order = np.argsort(scores)[::-1][:top_k]

    rows = []
    for idx in order:
        i = int(tri[0][idx])
        j = int(tri[1][idx])
        rows.append(
            {
                "roi_i": roi_ids[i],
                "roi_j": roi_ids[j],
                "roi_i_name": roi_names[i],
                "roi_j_name": roi_names[j],
                "ad_mean": float(ad_mean[i, j]),
                "cn_mean": float(cn_mean[i, j]),
                "diff": float(diff[i, j]),
                "abs_diff": float(abs(diff[i, j])),
            }
        )

    pd.DataFrame(rows).to_csv(out_path, index=False)


def main() -> None:
    cfg = load_config()
    if not os.path.isfile(PREDICTIONS_PATH):
        raise FileNotFoundError(f"Missing predictions: {PREDICTIONS_PATH}")

    pred_df = pd.read_csv(PREDICTIONS_PATH)
    meta = pd.read_csv(cfg["data"]["metadata"])
    labels_df = pd.read_csv(cfg["data"]["atlas_labels"])

    y_true = pred_df["y_true"].to_numpy()
    y_prob = pred_df["y_prob"].to_numpy()
    y_pred = (y_prob >= 0.5).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    print("Final test metrics")
    print(f"AUC:      {roc_auc_score(y_true, y_prob):.4f}")
    print(f"Accuracy: {(tp + tn) / (tp + tn + fp + fn):.4f}")
    print(f"BACC:     {balanced_accuracy_score(y_true, y_pred):.4f}")
    print(f"Sensitivity: {tp / (tp + fn + 1e-8):.4f}")
    print(f"Specificity: {tn / (tn + fp + 1e-8):.4f}")
    print(f"F1:       {2 * tp / (2 * tp + fp + fn + 1e-8):.4f}")

    os.makedirs("outputs/figures", exist_ok=True)
    os.makedirs("outputs/results", exist_ok=True)

    plot_roc(y_true, y_prob, "outputs/figures/roc_curve.png")
    plot_confusion(
        y_true, y_pred, ["CN", "AD"], "outputs/figures/confusion_matrix.png"
    )

    plot_group_adjacency(
        meta,
        cfg["data"]["processed_dir"],
        "outputs/figures/group_adjacency.png",
    )

    compute_roi_importance(
        meta,
        labels_df,
        cfg["data"]["processed_dir"],
        "outputs/results/roi_importance.csv",
    )

    print("Saved: outputs/figures/roc_curve.png")
    print("Saved: outputs/figures/confusion_matrix.png")
    print("Saved: outputs/figures/group_adjacency.png")
    print("Saved: outputs/results/roi_importance.csv")


if __name__ == "__main__":
    main()
