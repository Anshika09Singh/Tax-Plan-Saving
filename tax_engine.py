from __future__ import annotations

from dataclasses import dataclass


OLD_STANDARD_DEDUCTION = 50_000
NEW_STANDARD_DEDUCTION = 75_000


@dataclass(frozen=True)
class IncomeInput:
    salary: float
    freelance: float
    business: float
    other: float

    @property
    def total(self) -> float:
        return self.salary + self.freelance + self.business + self.other


@dataclass(frozen=True)
class DeductionInput:
    section_80c: float
    nps: float
    medical_insurance: float
    home_loan_interest: float
    education_loan_interest: float
    donations: float


@dataclass(frozen=True)
class TaxResult:
    regime: str
    taxable_income: float
    base_tax: float
    cess: float
    total_tax: float


def cap_deductions(deductions: DeductionInput) -> dict[str, float]:
    return {
        "80C": min(deductions.section_80c, 150_000),
        "NPS 80CCD(1B)": min(deductions.nps, 50_000),
        "Health Insurance 80D": min(deductions.medical_insurance, 25_000),
        "Home Loan Interest": min(deductions.home_loan_interest, 200_000),
        "Education Loan Interest": deductions.education_loan_interest,
        "Eligible Donations": min(deductions.donations, 100_000),
    }


def slab_tax(income: float, slabs: list[tuple[float, float, float]]) -> float:
    tax = 0.0
    for lower, upper, rate in slabs:
        if income > lower:
            taxable_slice = min(income, upper) - lower
            tax += taxable_slice * rate
    return max(tax, 0.0)


def calculate_old_regime_tax(taxable_income: float) -> TaxResult:
    if taxable_income <= 500_000:
        base_tax = 0.0
    else:
        slabs = [
            (250_000, 500_000, 0.05),
            (500_000, 1_000_000, 0.20),
            (1_000_000, float("inf"), 0.30),
        ]
        base_tax = slab_tax(taxable_income, slabs)
    cess = base_tax * 0.04
    return TaxResult("Old Regime", taxable_income, base_tax, cess, base_tax + cess)


def calculate_new_regime_tax(taxable_income: float) -> TaxResult:
    if taxable_income <= 1_200_000:
        base_tax = 0.0
    else:
        slabs = [
            (400_000, 800_000, 0.05),
            (800_000, 1_200_000, 0.10),
            (1_200_000, 1_600_000, 0.15),
            (1_600_000, 2_000_000, 0.20),
            (2_000_000, 2_400_000, 0.25),
            (2_400_000, float("inf"), 0.30),
        ]
        base_tax = slab_tax(taxable_income, slabs)
    cess = base_tax * 0.04
    return TaxResult("New Regime", taxable_income, base_tax, cess, base_tax + cess)


def calculate_tax_plan(income: IncomeInput, deductions: DeductionInput) -> dict:
    capped = cap_deductions(deductions)
    eligible_deductions = sum(capped.values()) + OLD_STANDARD_DEDUCTION
    old_taxable_income = max(income.total - eligible_deductions, 0.0)
    new_taxable_income = max(income.total - NEW_STANDARD_DEDUCTION, 0.0)

    old_result = calculate_old_regime_tax(old_taxable_income)
    new_result = calculate_new_regime_tax(new_taxable_income)
    best = old_result if old_result.total_tax <= new_result.total_tax else new_result
    other = new_result if best is old_result else old_result

    return {
        "gross_income": income.total,
        "eligible_deductions": eligible_deductions,
        "deduction_breakup": capped,
        "old_regime": old_result,
        "new_regime": new_result,
        "best_regime": best.regime,
        "best_tax": best.total_tax,
        "tax_savings": max(other.total_tax - best.total_tax, 0.0),
    }


def generate_recommendations(income: IncomeInput, deductions: DeductionInput, summary: dict) -> list[str]:
    recommendations: list[str] = []
    capped = summary["deduction_breakup"]

    remaining_80c = max(150_000 - capped["80C"], 0)
    if remaining_80c:
        recommendations.append(f"Invest up to Rs. {remaining_80c:,.0f} more in 80C options such as ELSS, PPF, EPF, or term insurance.")

    remaining_nps = max(50_000 - capped["NPS 80CCD(1B)"], 0)
    if remaining_nps:
        recommendations.append(f"Use additional NPS deduction capacity of Rs. {remaining_nps:,.0f} under 80CCD(1B).")

    if capped["Health Insurance 80D"] < 25_000:
        recommendations.append("Consider health insurance premium planning to use the 80D deduction limit.")

    if income.freelance + income.business > 0:
        recommendations.append("Track professional expenses carefully because eligible business costs can reduce taxable profit.")

    if summary["best_regime"] == "Old Regime":
        recommendations.append("The old regime appears better because deductions materially reduce taxable income.")
    else:
        recommendations.append("The new regime appears better based on the current deduction profile.")

    if not recommendations:
        recommendations.append("Your current inputs already use the major deduction categories well.")
    return recommendations


def generate_report_lines(summary: dict, ai_text: str | None = None) -> list[str]:
    old_regime: TaxResult = summary["old_regime"]
    new_regime: TaxResult = summary["new_regime"]
    lines = [
        "Tax Saving Assistant - Financial Summary",
        "",
        f"Gross income: Rs. {summary['gross_income']:,.0f}",
        f"Eligible deductions including standard deduction: Rs. {summary['eligible_deductions']:,.0f}",
        f"Old regime taxable income: Rs. {old_regime.taxable_income:,.0f}",
        f"Old regime estimated tax: Rs. {old_regime.total_tax:,.0f}",
        f"New regime taxable income: Rs. {new_regime.taxable_income:,.0f}",
        f"New regime estimated tax: Rs. {new_regime.total_tax:,.0f}",
        f"Recommended regime: {summary['best_regime']}",
        f"Estimated tax saving from selected regime: Rs. {summary['tax_savings']:,.0f}",
        "",
        "Deduction breakup:",
    ]
    for label, amount in summary["deduction_breakup"].items():
        lines.append(f"- {label}: Rs. {amount:,.0f}")

    if ai_text:
        lines.extend(["", "AI planning insights:", ai_text])
    return lines


def build_summary(summary: dict, ai_text: str | None = None) -> str:
    return "\n".join(generate_report_lines(summary, ai_text))
