"""
tvm_tools.py
------------
Pure deterministic TVM calculations — no AI, no side effects.
Every function takes explicit keyword arguments and returns a dict
with the answer plus the formula used (for display in the UI).
Sign convention: cash inflows are POSITIVE, outflows are NEGATIVE.
"""

import math


# ── 1. PRESENT VALUE ──────────────────────────────────────────────────────────

def solve_pv(fv: float = 0, pmt: float = 0, i: float = 0, n: float = 0) -> dict:
    """
    PV of a lump sum and/or level annuity.
    i = periodic interest rate as a decimal (e.g. 0.05 for 5%)
    n = number of periods
    """
    if i == 0:
        pv = fv + pmt * n
    else:
        pv_lump = fv / (1 + i) ** n
        pv_annuity = pmt * (1 - (1 + i) ** -n) / i if pmt != 0 else 0
        pv = pv_lump + pv_annuity

    return {
        "result": round(pv, 6),
        "label": "PV",
        "formula": f"PV = FV/(1+i)^n + PMT×[1-(1+i)^-n]/i",
        "inputs": {"FV": fv, "PMT": pmt, "i": i, "n": n},
    }


# ── 2. FUTURE VALUE ───────────────────────────────────────────────────────────

def solve_fv(pv: float = 0, pmt: float = 0, i: float = 0, n: float = 0) -> dict:
    """
    FV of a lump sum and/or level annuity.
    """
    if i == 0:
        fv = pv + pmt * n
    else:
        fv_lump = pv * (1 + i) ** n
        fv_annuity = pmt * ((1 + i) ** n - 1) / i if pmt != 0 else 0
        fv = fv_lump + fv_annuity

    return {
        "result": round(fv, 6),
        "label": "FV",
        "formula": "FV = PV×(1+i)^n + PMT×[(1+i)^n - 1]/i",
        "inputs": {"PV": pv, "PMT": pmt, "i": i, "n": n},
    }


# ── 3. INTEREST RATE (lump-sum only) ─────────────────────────────────────────

def solve_rate(pv: float, fv: float, n: float) -> dict:
    """
    Solve for periodic rate given PV, FV, n (lump-sum, no PMT).
    PV and FV must have opposite signs.
    """
    if pv == 0:
        raise ValueError("PV cannot be zero when solving for rate.")
    if n <= 0:
        raise ValueError("n must be positive.")
    ratio = fv / pv
    if ratio <= 0:
        raise ValueError("FV/PV must be positive to solve for a real rate.")
    i = ratio ** (1 / n) - 1

    return {
        "result": round(i, 8),
        "label": "i (periodic rate)",
        "formula": "i = (FV/PV)^(1/n) - 1",
        "inputs": {"PV": pv, "FV": fv, "n": n},
    }


# ── 4. NUMBER OF PERIODS ──────────────────────────────────────────────────────

def solve_n(pv: float, fv: float, i: float) -> dict:
    """
    Solve for n given PV, FV, and periodic rate i (lump-sum).
    """
    if i <= 0:
        raise ValueError("i must be positive to solve for n.")
    if pv == 0 or fv == 0:
        raise ValueError("Neither PV nor FV can be zero.")
    ratio = fv / pv
    if ratio <= 0:
        raise ValueError("FV/PV must be positive to solve for n.")
    n = math.log(ratio) / math.log(1 + i)

    return {
        "result": round(n, 6),
        "label": "n (periods)",
        "formula": "n = ln(FV/PV) / ln(1+i)",
        "inputs": {"PV": pv, "FV": fv, "i": i},
    }


# ── 5. RATE CONVERSIONS ───────────────────────────────────────────────────────

def convert_rate(
    nominal_rate: float,
    from_compounding: int,
    to_compounding: int,
) -> dict:
    """
    Convert a nominal rate between compounding frequencies.
    from_compounding / to_compounding: number of periods per year
      e.g. 12 = monthly, 4 = quarterly, 2 = semi-annual, 1 = annual
    Use 0 to represent continuous compounding.
    nominal_rate: as a decimal (e.g. 0.12 for 12%)
    """
    # Step 1 — convert to effective annual rate
    if from_compounding == 0:
        ear = math.exp(nominal_rate) - 1          # continuous → EAR
    else:
        ear = (1 + nominal_rate / from_compounding) ** from_compounding - 1

    # Step 2 — convert EAR to target nominal rate
    if to_compounding == 0:
        result = math.log(1 + ear)                # EAR → continuous
        label = "Force of interest (δ)"
    else:
        result = to_compounding * ((1 + ear) ** (1 / to_compounding) - 1)
        label = f"Nominal rate compounded {to_compounding}×/year"

    return {
        "result": round(result, 8),
        "label": label,
        "ear": round(ear, 8),
        "formula": "EAR = (1 + r/m)^m - 1  →  r_new = m_new×[(1+EAR)^(1/m_new)-1]",
        "inputs": {
            "nominal_rate": nominal_rate,
            "from_compounding": from_compounding,
            "to_compounding": to_compounding,
        },
    }


# ── 6. FORCE OF INTEREST ─────────────────────────────────────────────────────

def force_of_interest(i_effective_annual: float) -> dict:
    """
    Compute the force of interest δ from the effective annual rate i.
    δ = ln(1 + i)
    """
    if i_effective_annual <= -1:
        raise ValueError("Effective annual rate must be greater than -1.")
    delta = math.log(1 + i_effective_annual)

    return {
        "result": round(delta, 8),
        "label": "Force of interest (δ)",
        "formula": "δ = ln(1 + i)",
        "inputs": {"i_effective_annual": i_effective_annual},
    }


def rate_from_force(delta: float) -> dict:
    """
    Recover the effective annual rate from force of interest δ.
    i = e^δ - 1
    """
    i = math.exp(delta) - 1

    return {
        "result": round(i, 8),
        "label": "Effective annual rate (i)",
        "formula": "i = e^δ - 1",
        "inputs": {"delta": delta},
    }


# ── 7. EQUATION OF VALUE ─────────────────────────────────────────────────────

def equation_of_value(
    cashflows: list[dict],
    i: float,
    valuation_time: float = 0,
) -> dict:
    """
    Move all cashflows to a common valuation date and sum them.
    cashflows: list of {"amount": float, "time": float}
      - positive = inflow, negative = outflow
    i: effective periodic rate
    valuation_time: the time point to accumulate/discount to (default 0 = PV)

    Returns the net value at valuation_time. If == 0, the equation of value balances.
    """
    net = 0.0
    detail = []
    for cf in cashflows:
        amt = cf["amount"]
        t = cf["time"]
        dt = valuation_time - t          # positive = accumulate, negative = discount
        factor = (1 + i) ** dt
        value_at_t0 = amt * factor
        net += value_at_t0
        detail.append({
            "amount": amt,
            "time": t,
            "factor": round(factor, 6),
            "value_at_valuation": round(value_at_t0, 6),
        })

    return {
        "result": round(net, 6),
        "label": f"Net value at t={valuation_time}",
        "formula": "Σ CF_t × (1+i)^(T-t)",
        "balanced": abs(net) < 1e-4,
        "detail": detail,
        "inputs": {"i": i, "valuation_time": valuation_time},
    }
