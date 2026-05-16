#!/usr/bin/env python3
"""Multimodal graph classification with SVM and XGBoost."""

import os

import numpy as np
import pandas as pd
import yaml
import networkx as nx

from sklearn.base import clone
from sklearn.metrics import (
    balanced_accuracy_score,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

CONFIG_PATH = "configs/default.yaml"
METRIC_NAMES = ["degree", "clustering", "path_length", "global_eff", "local_eff"]


def load_config(path: str = CONFIG_PATH) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_metadata(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"subject_id", "label"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"metadata.csv missing columns: {sorted(missing)}")
    df = df[df["label"].isin(["AD", "CN"])].copy()
    if df.empty:
        raise ValueError("metadata.csv has no AD or CN subjects")
    df["y"] = (df["label"] == "AD").astype(int)
    return df.reset_index(drop=True)


def load_metrics(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "subject_id" not in df.columns:
        raise ValueError("graph_metrics.csv missing subject_id")
    df = df.set_index("subject_id")
    expected = []
    for tag in ["mri", "pet", "fused"]:
        for name in METRIC_NAMES:
            expected.append(f"{tag}_{name}")
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"graph_metrics.csv missing columns: {missing}")
    return df


def adjacency_to_nx(A: np.ndarray, threshold_percentile: float) -> nx.Graph:
    n = A.shape[0]
    A_thr = A.copy()
    np.fill_diagonal(A_thr, 0)
    upper = A_thr[np.triu_indices(n, k=1)]
    if len(upper) == 0:
        return nx.Graph()
    thr = np.percentile(upper, threshold_percentile)
    A_thr[A_thr < thr] = 0
    return nx.from_numpy_array(A_thr)


def graph_metrics(A: np.ndarray, threshold_percentile: float) -> dict:
    G = adjacency_to_nx(A, threshold_percentile)
    if G.number_of_nodes() == 0:
        return {name: 0.0 for name in METRIC_NAMES}
    try:
        Gc = G.subgraph(max(nx.connected_components(G), key=len)).copy()
        return {
            "degree": float(np.mean([d for _, d in Gc.degree()])),
            "clustering": float(nx.average_clustering(Gc)),
            "path_length": float(
                nx.average_shortest_path_length(Gc) if nx.is_connected(Gc) else 0.0
            ),
            "global_eff": float(nx.global_efficiency(Gc)),
            "local_eff": float(nx.local_efficiency(Gc)),
        }
    except Exception:
        return {name: 0.0 for name in METRIC_NAMES}


def get_classifiers() -> dict:
    return {
        "svm": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    SVC(
                        kernel="rbf",
                        probability=True,
                        C=1.0,
                        gamma="scale",
                    ),
                ),
            ]
        ),
        "xgboost": XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            verbosity=0,
        ),
    }


def load_subject_cache(meta: pd.DataFrame, processed_dir: str) -> dict:
    node_stats = {}
    adj_mri = {}
    adj_pet = {}

    for sid in meta["subject_id"]:
        proc_dir = os.path.join(processed_dir, sid)
        node_path = os.path.join(proc_dir, f"{sid}_node_features.npy")
        mri_path = os.path.join(proc_dir, f"{sid}_A_mri.npy")
        pet_path = os.path.join(proc_dir, f"{sid}_A_pet.npy")

        if not os.path.isfile(node_path):
            raise FileNotFoundError(f"Missing node features: {node_path}")
        if not os.path.isfile(mri_path) or not os.path.isfile(pet_path):
            raise FileNotFoundError(f"Missing adjacency for {sid}")

        X_node = np.load(node_path)
        node_stats[sid] = np.concatenate(
            [X_node.mean(axis=0), X_node.std(axis=0)]
        ).astype(np.float32)

        adj_mri[sid] = np.load(mri_path).astype(np.float32)
        adj_pet[sid] = np.load(pet_path).astype(np.float32)

    return {"node_stats": node_stats, "adj_mri": adj_mri, "adj_pet": adj_pet}


def fuse_adjacency(A_mri: np.ndarray, A_pet: np.ndarray, alpha: float) -> np.ndarray:
    if A_mri.shape != A_pet.shape:
        raise ValueError("Adjacency shapes do not match")
    return alpha * A_mri + (1.0 - alpha) * A_pet


def build_feature_matrix(
    sids: list,
    cache: dict,
    metrics_df: pd.DataFrame,
    feature_set: str,
    alpha: float,
    threshold_percentile: float,
) -> np.ndarray:
    use_graph_metrics = feature_set in ["graph_metrics", "all"]
    use_node_stats = feature_set in ["node_stats", "all"]
    use_flat_adj = feature_set in ["flat_adj", "all"]

    rows = []

    for sid in sids:
        parts = []
        A_fused = None

        if use_graph_metrics:
            row = metrics_df.loc[sid]
            # Read all precomputed metrics (mri, pet, fused) directly from CSV
            # 6e already computed fused metrics with the correct threshold.
            # Recalculating here would be inconsistent if alpha differs from 6d.
            all_metrics = []
            for tag in ["mri", "pet", "fused"]:
                for name in METRIC_NAMES:
                    all_metrics.append(float(row[f"{tag}_{name}"]))
            parts.append(np.array(all_metrics, dtype=np.float32))

        if use_node_stats:
            parts.append(cache["node_stats"][sid])

        if use_flat_adj:
            if A_fused is None:
                A_fused = fuse_adjacency(
                    cache["adj_mri"][sid], cache["adj_pet"][sid], alpha
                )
            n = A_fused.shape[0]
            flat = A_fused[np.triu_indices(n, k=1)].astype(np.float32)
            parts.append(flat)

        if not parts:
            raise ValueError(f"Unsupported feature_set: {feature_set}")

        rows.append(np.concatenate(parts))

    return np.stack(rows, axis=0)


def run_cv(
    X: np.ndarray,
    y: np.ndarray,
    n_folds: int,
    seed: int,
    classifiers: dict,
) -> dict:
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)

    results = {
        name: {"auc": [], "bacc": [], "sens": [], "spec": []}
        for name in classifiers
    }

    for train_idx, val_idx in skf.split(X, y):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]

        for name, clf in classifiers.items():
            model = clone(clf)
            model.fit(X_tr, y_tr)
            prob = model.predict_proba(X_val)[:, 1]
            pred = (prob >= 0.5).astype(int)

            tn, fp, fn, tp = confusion_matrix(
                y_val, pred, labels=[0, 1]
            ).ravel()

            auc = roc_auc_score(y_val, prob)
            bacc = balanced_accuracy_score(y_val, pred)
            sens = tp / (tp + fn + 1e-8)
            spec = tn / (tn + fp + 1e-8)

            results[name]["auc"].append(auc)
            results[name]["bacc"].append(bacc)
            results[name]["sens"].append(sens)
            results[name]["spec"].append(spec)

    summary = {}
    for name, metrics in results.items():
        summary[name] = {
            "auc": float(np.mean(metrics["auc"])),
            "bacc": float(np.mean(metrics["bacc"])),
            "sens": float(np.mean(metrics["sens"])),
            "spec": float(np.mean(metrics["spec"])),
        }

    return summary


def evaluate_test(
    X_dev: np.ndarray,
    y_dev: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    clf,
) -> dict:
    model = clone(clf)
    model.fit(X_dev, y_dev)
    prob = model.predict_proba(X_test)[:, 1]
    pred = (prob >= 0.5).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_test, pred, labels=[0, 1]).ravel()
    auc = roc_auc_score(y_test, prob)
    bacc = balanced_accuracy_score(y_test, pred)
    sens = tp / (tp + fn + 1e-8)
    spec = tn / (tn + fp + 1e-8)

    return {
        "auc": float(auc),
        "bacc": float(bacc),
        "sens": float(sens),
        "spec": float(spec),
        "y_prob": prob,
        "y_pred": pred,
    }


def main() -> None:
    cfg = load_config()
    meta = load_metadata(cfg["data"]["metadata"])
    metrics_df = load_metrics(cfg["data"]["graph_metrics_csv"])

    processed_dir = cfg["data"]["processed_dir"]
    feature_set = cfg["classification"]["feature_set"]
    n_folds = int(cfg["classification"]["n_folds"])
    seed = int(cfg["classification"]["seed"])
    test_size = float(cfg["classification"]["test_size"])
    threshold = float(cfg["graph_metrics"]["threshold_percentile"])

    sids = meta["subject_id"].tolist()
    y = meta["y"].to_numpy()

    cache = load_subject_cache(meta, processed_dir)

    classifiers_all = get_classifiers()
    selected = set(cfg["classification"]["classifiers"])
    classifiers = {k: v for k, v in classifiers_all.items() if k in selected}
    if not classifiers:
        raise ValueError("No valid classifiers selected")

    alpha_candidates = cfg["classification"].get("alpha_search")
    if not alpha_candidates:
        alpha_candidates = [cfg["fusion"]["alpha"]]

    indices = np.arange(len(sids))
    train_idx, test_idx = train_test_split(
        indices, test_size=test_size, stratify=y, random_state=seed
    )

    best_alpha = {name: None for name in classifiers}
    best_auc = {name: -1.0 for name in classifiers}

    for alpha in alpha_candidates:
        X = build_feature_matrix(
            sids, cache, metrics_df, feature_set, float(alpha), threshold
        )
        X_dev, y_dev = X[train_idx], y[train_idx]
        cv_summary = run_cv(X_dev, y_dev, n_folds, seed, classifiers)

        for name, scores in cv_summary.items():
            if scores["auc"] > best_auc[name]:
                best_auc[name] = scores["auc"]
                best_alpha[name] = float(alpha)

            print(
                f"CV alpha={alpha} {name} AUC={scores['auc']:.3f} "
                f"BACC={scores['bacc']:.3f}"
            )

    summary_rows = []
    best_classifier = None
    best_classifier_auc = -1.0
    best_test_output = None

    for name, clf in classifiers.items():
        alpha = best_alpha[name]
        X = build_feature_matrix(
            sids, cache, metrics_df, feature_set, alpha, threshold
        )
        X_dev, y_dev = X[train_idx], y[train_idx]
        X_test, y_test = X[test_idx], y[test_idx]

        test_result = evaluate_test(X_dev, y_dev, X_test, y_test, clf)

        summary_rows.append(
            {
                "classifier": name,
                "alpha": alpha,
                "cv_auc": best_auc[name],
                "test_auc": test_result["auc"],
                "test_bacc": test_result["bacc"],
                "test_sens": test_result["sens"],
                "test_spec": test_result["spec"],
            }
        )

        if best_auc[name] > best_classifier_auc:
            best_classifier_auc = best_auc[name]
            best_classifier = name
            best_test_output = {
                "alpha": alpha,
                "y_prob": test_result["y_prob"],
                "y_pred": test_result["y_pred"],
                "y_true": y_test,
                "sids": [sids[i] for i in test_idx],
            }

    os.makedirs("outputs/results", exist_ok=True)
    pd.DataFrame(summary_rows).to_csv(
        "outputs/results/classification_summary.csv", index=False
    )

    if best_test_output is not None:
        pred_df = pd.DataFrame(
            {
                "subject_id": best_test_output["sids"],
                "y_true": best_test_output["y_true"],
                "y_pred": best_test_output["y_pred"],
                "y_prob": best_test_output["y_prob"],
                "classifier": best_classifier,
                "alpha": best_test_output["alpha"],
            }
        )
        pred_df.to_csv("outputs/results/test_predictions.csv", index=False)

    print("Saved: outputs/results/classification_summary.csv")
    print("Saved: outputs/results/test_predictions.csv")


if __name__ == "__main__":
    main()
