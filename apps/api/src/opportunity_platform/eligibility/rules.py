"""Closed, typed rule language. Never interprets expressions or invokes an LLM."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FactKey = Literal[
    "age",
    "annual_personal_income",
    "annual_parental_income",
    "disability_percentage",
    "nationality",
    "domicile_state",
    "domicile_district",
    "residence_state",
    "residence_district",
    "education_level",
    "student_status",
    "employment_status",
    "has_bank_account",
    "auto_debit_consent",
    "has_income_certificate",
    "business_registered",
    "business_turnover",
    "has_registration_certificate",
    "has_disability_certificate",
    "has_udid_certificate",
]
Scalar = str | int | float | bool


class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    op: Literal["eq", "gte", "lte", "in", "document", "unknown"]
    fact: FactKey | None = None
    value: Scalar | list[Scalar] | None = None
    income_period: str | None = None
    income_definition: str | None = None
    as_of: date | None = None

    @model_validator(mode="after")
    def shape(self):
        if self.op != "unknown" and self.fact is None:
            raise ValueError("A condition needs a known fact key")
        if self.op in {"gte", "lte"} and (type(self.value) not in (int, float)):
            raise ValueError("Numeric comparison requires a number")
        if self.op == "in" and not isinstance(self.value, list):
            raise ValueError("Membership comparison requires a list")
        if (
            self.fact
            in {
                "annual_personal_income",
                "annual_parental_income",
                "business_turnover",
            }
            and self.op != "unknown"
            and (not self.income_period or not self.income_definition)
        ):
            raise ValueError("Income rules require a period and definition")
        if self.op == "document" and self.fact not in {
            "has_income_certificate",
            "has_registration_certificate",
            "has_disability_certificate",
            "has_udid_certificate",
        }:
            raise ValueError("Document rules require a supported evidence field")
        if self.fact in {
            "has_income_certificate",
            "has_registration_certificate",
            "has_disability_certificate",
            "has_udid_certificate",
        } and self.op not in {"document", "unknown"}:
            raise ValueError("Document possession must be evaluated as an evidence dependency")
        if self.op in {"eq", "in", "gte", "lte"}:
            values = self.value if self.op == "in" else [self.value]
            if not values or any(value is None for value in values):
                raise ValueError("Comparisons need explicit, nonempty values")
            for value in values:
                FactInput(key=self.fact, value=value)
            if self.op in {"gte", "lte"} and self.fact not in {
                "age",
                "annual_personal_income",
                "annual_parental_income",
                "disability_percentage",
                "business_turnover",
            }:
                raise ValueError("Only numeric facts support ordered comparisons")
        return self


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    op: Literal["all", "any", "condition"]
    condition: Condition | None = None
    children: list["Rule"] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def shape(self):
        if self.op == "condition":
            if self.condition is None or self.children:
                raise ValueError("A leaf needs only a condition")
        elif not self.children or self.condition is not None:
            raise ValueError("A group needs children only")

        def bounds(rule, depth=0):
            if depth > 8:
                raise ValueError("Rule nesting exceeds eight levels")
            return 1 + sum(bounds(child, depth + 1) for child in rule.children)

        if bounds(self) > 100:
            raise ValueError("Rule exceeds 100 nodes")
        return self


class FactInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    key: FactKey
    value: Scalar | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    income_period: str | None = None
    income_definition: str | None = None

    @model_validator(mode="after")
    def valid(self):
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("Invalid validity interval")
        if self.value is not None:
            if self.key in {
                "age",
                "annual_personal_income",
                "annual_parental_income",
                "disability_percentage",
                "business_turnover",
            }:
                if type(self.value) not in (int, float) or self.value < 0:
                    raise ValueError("A nonnegative number is required")
                if self.key == "age" and (type(self.value) is not int or self.value > 130):
                    raise ValueError("Age must be a whole number from 0 to 130")
                if self.key == "disability_percentage" and self.value > 100:
                    raise ValueError("Percentage must be at most 100")
            elif self.key.startswith("has_") or self.key in {
                "student_status",
                "auto_debit_consent",
                "business_registered",
            }:
                if type(self.value) is not bool:
                    raise ValueError("A boolean is required")
            elif not isinstance(self.value, str) or len(self.value) > 100:
                raise ValueError("A short text value is required")
        return self
