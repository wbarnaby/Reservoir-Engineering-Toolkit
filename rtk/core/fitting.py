"""Least-squares fitting used throughout the toolkit.

One general solver, leaste_squares(), handles any design matrix A.
Thin wrappers build A for the common cases:
    fit_line()      y = b0 + b1*x   (p/z, semilog well test)
    fit_origin()    y = b*x         (Havlena-Odeh, F = N*Eo)
fit_stats() reports fit quality for any model's predictions
"""

import numpy as np


def design_matrix(x, intercept=True):
    # Build the design matrix A from 1-D x values.
    x = np.asarray(x, dtype=float)
    if x.ndim != 1:
        raise ValueError(f"x must be 1-D, got {x.ndim}-D")

    n = len(x)
    if intercept:
        A = np.ones((n, 2))
        A[:, 1] = x
    else:
        A = x[:, None]

    return A


def least_squares(A, y):
    # Solve the normal equations (A.T @ A) beta = A.T @ y.
    A = np.asarray(A, dtype=float)
    y = np.asarray(y, dtype=float)

    if A.ndim != 2:
        raise ValueError(f"A must be 2-D, got {A.ndim}-D")
    if y.ndim != 1:
        raise ValueError(f"y must be 1-D, got {y.ndim}-D")
    if A.shape[0] != y.shape[0]:
        raise ValueError(
            "Number of points does not match: "
            f"A has {A.shape[0]}, y has {y.shape[0]}"
        )
    if A.shape[0] < A.shape[1]:
        raise ValueError(
            f"Fewer points ({A.shape[0]}) than unknowns ({A.shape[1]})"
        )

    at_a = A.T @ A
    at_y = A.T @ y

    try:
        beta = np.linalg.solve(at_a, at_y)
    except np.linalg.LinAlgError:
        raise ValueError(
            "Singular matrix: columns of A are linearly dependent "
            "(e.g. all x values identical)"
        ) from None

    return beta


def fit_line(x, y):
    # Fit y = b*x through the origin. Returns slope as a float.
    A = design_matrix(x)
    beta = least_squares(A, y)

    intercept, slope = beta
    return float(intercept), float(slope)


def fit_origin(x, y):
    # Fit y = b*x through the origin. Returns slope as a float.
    A = design_matrix(x, False)
    beta = least_squares(A, y)

    return float(beta[0])


def fit_stats(y, y_pred):
    # Return fit-quality statistics as a dict.
    y = np.asarray(y, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    if y.shape != y_pred.shape:
        raise ValueError(
            f"y and y_pred shapes differ: {y.shape} vs {y_pred.shape}"
        )

    r = y - y_pred
    ss_res = np.sum(r**2)
    ss_tot = np.sum((y - y.mean()) ** 2)

    if np.ptp(y) == 0:
        r2 = float("nan")
    else:
        r2 = 1 - ss_res / ss_tot

    return {
        "residuals": r,
        "l1": np.sum(np.abs(r)),
        "l2": np.sqrt(ss_res),
        "rmse": np.sqrt(ss_res / len(y)),
        "r2": r2,
    }
