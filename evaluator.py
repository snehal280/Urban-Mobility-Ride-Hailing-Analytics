"""
Model evaluator with rolling-origin time-series cross validation.
"""

from typing import Callable, Dict, List

import numpy as np
import pandas as pd
from loguru import logger

from src.utils.helpers import mae, rmse, mape


def time_series_cv(
    df: pd.DataFrame,
    target_col: str,
    time_col: str,
    train_fn: Callable,
    predict_fn: Callable,
    n_splits: int = 5,
    horizon: int = 24,
) -> pd.DataFrame:
    """
    Rolling-origin cross validation for time series.

    Args:
        df: DataFrame sorted by time_col
        target_col: name of the target column
        train_fn: callable(train_df) -> model
        predict_fn: callable(model, test_df) -> np.ndarray of predictions
        n_splits: number of CV folds
        horizon: number of periods (hours) to forecast per fold

    Returns:
        DataFrame with per-fold metrics
    """
    df = df.sort_values(time_col).reset_index(drop=True)
    n = len(df)
    min_train = n // (n_splits + 1)
    results = []

    for fold in range(n_splits):
        split_idx = min_train + fold * (horizon)
        train_df  = df.iloc[:split_idx]
        test_df   = df.iloc[split_idx: split_idx + horizon]

        if len(test_df) == 0:
            break

        model = train_fn(train_df)
        preds = predict_fn(model, test_df)
        actual = test_df[target_col].values

        results.append({
            "fold":    fold + 1,
            "n_train": len(train_df),
            "n_test":  len(test_df),
            "mae":     mae(actual, preds),
            "rmse":    rmse(actual, preds),
            "mape":    mape(actual, preds),
        })
        logger.info(
            f"Fold {fold+1}: MAE={results[-1]['mae']:.2f}  "
            f"RMSE={results[-1]['rmse']:.2f}  MAPE={results[-1]['mape']:.1f}%"
        )

    return pd.DataFrame(results)


def summarize_metrics(cv_results: pd.DataFrame) -> Dict[str, float]:
    """Return mean and std of metrics across CV folds."""
    return {
        "mae_mean":  cv_results["mae"].mean(),
        "mae_std":   cv_results["mae"].std(),
        "rmse_mean": cv_results["rmse"].mean(),
        "rmse_std":  cv_results["rmse"].std(),
        "mape_mean": cv_results["mape"].mean(),
        "mape_std":  cv_results["mape"].std(),
    }
