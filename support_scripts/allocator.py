"""
heuristic_allocator.py

Fast heuristic allocator for concave saturation objectives.

Problem:
    Maximize sum_i w_i * B * (x0_i + x_i) / (B + x0_i + x_i)
    subject to:
        x_i >= 0
        sum_i x_i = M

This allocator:
    - avoids sorting
    - avoids iterative active-set refinement
    - uses a global lambda approximation
    - runs in one pass over inputs (O(n))

This is NOT exact.
It is designed for large-n settings where exact KKT handling is too expensive.
"""

import math


# ============================================================
# HEURISTIC ALLOCATOR
# ============================================================
def heuristic_alloc(initiatives, M, B):
    import math

    # Trivial case
    n = len(initiatives)
    if n == 0 or M <= 0:
        return [], [0.0] * n, [0.0] * n, 0.0

    # Extract data
    names   = [n for (n, w, x0) in initiatives]
    weights = [w for (n, w, x0) in initiatives]
    x0s     = [x0 for (n, w, x0) in initiatives]

# Relevant mod section

    # --- Global averages ---
    # This is just O(n) to compute
    avg_sqrt_w = sum(math.sqrt(w) for w in weights) / n
    avg_shift  = sum(B + x0 for x0 in x0s) / n

    # Just a constant calculation to get lambda
    lam = (B * avg_sqrt_w / (M / n + avg_shift)) ** 2

    # O(n) we do a constant math operation per initiative
    x_raw = [0.0] * n
    for i in range(n):
        xi = B * math.sqrt(weights[i] / lam) - B - x0s[i]
        x_raw[i] = max(0.0, xi)

    # constant time
    # sum of raw allocations
    S = sum(x_raw)

    # --- Enforce budget ---
    # if S > 0, scale down/up proportionally to meet budget M
    if S > 0:
        scale = M / S
        x = [xi * scale for xi in x_raw]
    # if S == 0, everyone gets zero
    else:
        x = [0.0] * n

# / Relevant mod section

    # Compute value === the mod code won't do this here since we'll only compute total value in the initiative code ===
    values = [
        (x0s[i] + x[i]) * B / (B + x0s[i] + x[i])
        for i in range(n)
    ]

    return names, x, values, sum(values)

# ============================================================
# TESTS
# ============================================================

def print_case(title, initiatives, M, B):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    print(f"Total budget M = {M}")
    print(f"Saturation B  = {B}\n")

    print(f"{'Initiative':<15} {'Weight':>8} {'Baseline':>10}")
    print("-" * 70)
    for n, w, x0 in initiatives:
        print(f"{n:<15} {w:>8.2f} {x0:>10.2f}")

    names, x, values, total = heuristic_alloc(initiatives, M, B)

    print("\nResults:")
    print(f"{'Initiative':<15} {'Alloc':>10} {'Total x':>10} {'Value':>12}")
    print("-" * 70)
    for i in range(len(names)):
        total_x = initiatives[i][2] + x[i]
        print(f"{names[i]:<15} {x[i]:>10.2f} {total_x:>10.2f} {values[i]:>12.2f}")

    print("-" * 70)
    print(f"{'TOTAL VALUE':<15} {total:>34.2f}")

def reasonableness_tests():
    # 1. Simple weight dominance
    print_case(
        "CASE 1: Higher weight should receive more",
        initiatives=[
            ("Agriculture", 100, 0),
            ("Industry",     80, 0),
            ("Culture",      20, 0),
            ("Hobby",         5, 0),
        ],
        M=1000,
        B=500
    )

    # 2. Baseline suppression
    print_case(
        "CASE 2: Heavy baseline reduces marginal allocation",
        initiatives=[
            ("Health",   100, 0),
            ("Defense",  100, 1200),
            ("Education",100, 0),
        ],
        M=600,
        B=400
    )

    # 3. Small budget stress test
    print_case(
        "CASE 3: Small budget concentrates funding",
        initiatives=[
            ("Core", 200, 0),
            ("Side",  50, 0),
            ("Nice",  10, 0),
        ],
        M=100,
        B=500
    )

    # 4. Many similar initiatives
    print_case(
        "CASE 4: Large-n, near-uniform system",
        initiatives=[
            (f"I{i}", 10 + (i % 3), i % 30)
            for i in range(12)
        ],
        M=2000,
        B=800
    )

def test_basic_behavior():
    initiatives = [
        ("A", 100, 0),
        ("B",  90, 0),
        ("C",  10, 0),
        ("D",   1, 0),
    ]

    M = 1000
    B = 500

    _, x, _, _ = heuristic_alloc(initiatives, M, B)

    assert x[0] >= x[1] >= x[2] >= x[3], "Higher weight should not get less funding"


def test_baseline_suppression():
    initiatives = [
        ("A", 100, 0),
        ("B", 100, 1000),  # already heavily funded
        ("C", 100, 0),
    ]

    M = 500
    B = 300

    _, x, _, _ = heuristic_alloc(initiatives, M, B)

    assert x[1] <= x[0] and x[1] <= x[2], "Baseline-heavy initiative should be penalized"


def test_zero_budget():
    initiatives = [
        ("A", 10, 0),
        ("B", 20, 0),
    ]

    names, x, values, total = heuristic_alloc(initiatives, 0, 100)

    assert sum(x) == 0
    assert total == sum(values)


def test_large_n_stability():
    initiatives = [
        (f"I{i}", 1 + (i % 5), i % 20)
        for i in range(1000)
    ]

    M = 10_000
    B = 1_000

    names, x, values, total = heuristic_alloc(initiatives, M, B)

    assert len(x) == 1000
    assert total > 0


# ============================================================
# RUN TESTS
# ============================================================

if __name__ == "__main__":
    reasonableness_tests()
    test_basic_behavior()
    test_baseline_suppression()
    test_zero_budget()
    test_large_n_stability()
    print("All heuristic allocator tests passed.")
