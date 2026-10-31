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


if __name__ == "__main__":
    # hand example: x = [1, 2, 3], y = [1, 2, 2]
    x = np.array([1.0, 2.0, 3.0])
    y = np.array([1.0, 2.0, 2.0])
    b0, b1 = fit_line(x, y)
    stats = fit_stats(y, b0 + b1 * x)
    r = stats["residuals"]

    # p/z example: G should be 100 Bcf
    gp = np.array([0, 10, 20, 30, 40])
    p_z = np.array([5000, 4500, 4000, 3500, 3000])
    pz_b0, pz_b1 = fit_line(gp, p_z)
    pz_stats = fit_stats(p_z, pz_b0 + pz_b1 * gp)

    # noisy data, checked against numpy's own fitter
    x_noisy = np.array([1, 2, 3, 4, 5])
    y_noisy = np.array([2.1, 3.9, 6.2, 7.8, 10.1])
    np_slope, np_intercept = np.polyfit(x_noisy, y_noisy, 1)

    # each case: (label, result, expected)
    cases = [
        ("hand intercept", b0, 2 / 3),
        ("hand slope", b1, 0.5),
        ("hand R2", stats["r2"], 0.75),
        ("hand L1", stats["l1"], 2 / 3),
        ("hand L2", stats["l2"], np.sqrt(1 / 6)),
        ("hand RMSE", stats["rmse"], np.sqrt(1 / 18)),
        ("residuals sum to 0", np.sum(r), 0.0),
        ("residuals perpendicular to x", np.sum(x * r), 0.0),
        ("origin slope", fit_origin(x, y), 11 / 14),
        ("p/z intercept", pz_b0, 5000.0),
        ("p/z slope", pz_b1, -50.0),
        ("p/z G", -pz_b0 / pz_b1, 100.0),
        ("p/z R2", pz_stats["r2"], 1.0),
        (
            "noisy vs polyfit",
            fit_line(x_noisy, y_noisy),
            (np_intercept, np_slope),
        ),
    ]

    print("--- fits ---")
    for label, got, expected in cases:
        if np.allclose(got, expected):
            print(f"PASS  {label}")
        else:
            print(f"FAIL  {label}: got {got}, expected {expected}")

    # each case should raise ValueError
    bad_cases = [
        ("singular (all x equal)", fit_line, [3, 3, 3], [1, 2, 3]),
        ("length mismatch", fit_line, [1, 2], [1, 2, 3]),
        ("too few points", fit_origin, [], []),
        ("2-D x", fit_line, [[1, 2], [3, 4]], [1, 2]),
    ]

    print("--- expected errors ---")
    for label, func, x_bad, y_bad in bad_cases:
        try:
            func(x_bad, y_bad)
            print(f"FAIL  {label}: no error raised")
        except ValueError as err:
            print(f"PASS  {label}: {err}")

    print("--- R2 edge case ---")
    flat = fit_stats([2, 2, 2], [2, 2, 2])
    print(f"all y identical -> r2 = {flat['r2']}")
