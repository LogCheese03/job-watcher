"""The title rule."""
import pytest

from watcher.titles import in_role


@pytest.mark.parametrize("title", [
    "Financial Analyst",
    "Senior Financial Analyst, FP&A",
    "FP&A Manager",
    "Analyst, Financial Planning & Analysis",
    "Corporate Finance Associate",
    "Credit Analyst II",
    "Treasury Analyst",
    "Investment Analyst - Fixed Income",
    "Finance Business Partner",
    "FINANCE ANALYST",
])
def test_in_role(title):
    assert in_role(title)


@pytest.mark.parametrize("title", [
    "Software Engineer",
    "Financial Analyst Intern",
    "Finance Systems Engineer",
    "Data Analyst",
    "Sales Associate",
    "Financial Advisor",
    "",
    None,
])
def test_not_in_role(title):
    assert not in_role(title)
