"""積立未来シミュレーターの計算ロジック。金額の単位は万円。"""

from __future__ import annotations

import math


def _validate(monthly: float, annual_rate: float) -> None:
    if monthly <= 0:
        raise ValueError("毎月の積立額は0より大きくしてください。")
    if not 0 <= annual_rate <= 50:
        raise ValueError("想定利回りは0〜50%で入力してください。")


def future_value(monthly: float, annual_rate: float, months: int) -> float:
    """月末積立・月次複利による将来価値を返す。"""
    _validate(monthly, annual_rate)
    if months < 0:
        raise ValueError("積立月数は0以上にしてください。")
    rate = annual_rate / 100 / 12
    if rate == 0:
        return monthly * months
    return monthly * math.expm1(months * math.log1p(rate)) / rate


def investment_summary(monthly: float, annual_rate: float, months: int) -> dict[str, float]:
    total = future_value(monthly, annual_rate, months)
    principal = monthly * months
    return {"principal": principal, "profit": total - principal, "total": total}


def months_to_target(monthly: float, annual_rate: float, target: float) -> int:
    """目標に初めて到達する月（端数切り上げ）を返す。"""
    _validate(monthly, annual_rate)
    if target <= 0:
        raise ValueError("目標金額は0より大きくしてください。")
    rate = annual_rate / 100 / 12
    if rate == 0:
        return math.ceil(target / monthly)
    raw = math.log1p(target * rate / monthly) / math.log1p(rate)
    months = max(1, math.ceil(raw - 1e-12))
    # 浮動小数点の境界でも「初めて到達する月」を保証する。
    while months > 1 and future_value(monthly, annual_rate, months - 1) >= target:
        months -= 1
    while future_value(monthly, annual_rate, months) < target:
        months += 1
    return months


def monthly_series(monthly: float, annual_rate: float, months: int) -> list[dict[str, float]]:
    """0か月目を含む月ごとの元本・運用益・合計を返す。"""
    _validate(monthly, annual_rate)
    return [
        {
            "month": month,
            "principal": monthly * month,
            "profit": future_value(monthly, annual_rate, month) - monthly * month,
            "total": future_value(monthly, annual_rate, month),
        }
        for month in range(months + 1)
    ]


def milestone_months(monthly: float, annual_rate: float) -> dict[int, int]:
    """500・1,000・2,000万円の到達月を返す。"""
    return {target: months_to_target(monthly, annual_rate, target) for target in (500, 1000, 2000)}

