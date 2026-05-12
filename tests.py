from tax_engine import DeductionInput, IncomeInput, calculate_tax_plan, generate_recommendations


def test_new_regime_benefits_low_deduction_profile() -> None:
    income = IncomeInput(salary=900_000, freelance=0, business=0, other=0)
    deductions = DeductionInput(0, 0, 0, 0, 0, 0)
    summary = calculate_tax_plan(income, deductions)

    assert summary["best_regime"] == "New Regime"
    assert summary["best_tax"] >= 0


def test_old_regime_can_win_with_large_deductions() -> None:
    income = IncomeInput(salary=900_000, freelance=0, business=0, other=0)
    deductions = DeductionInput(150_000, 50_000, 25_000, 200_000, 0, 0)
    summary = calculate_tax_plan(income, deductions)

    assert summary["best_regime"] == "Old Regime"
    assert summary["eligible_deductions"] == 475_000


def test_recommendations_include_freelancer_expense_tracking() -> None:
    income = IncomeInput(salary=0, freelance=800_000, business=0, other=0)
    deductions = DeductionInput(20_000, 0, 0, 0, 0, 0)
    summary = calculate_tax_plan(income, deductions)

    recommendations = generate_recommendations(income, deductions, summary)

    assert any("professional expenses" in item for item in recommendations)


if __name__ == "__main__":
    test_new_regime_benefits_low_deduction_profile()
    test_old_regime_can_win_with_large_deductions()
    test_recommendations_include_freelancer_expense_tracking()
    print("All tests passed.")
