from enum import StrEnum
from typing import Set

from pydantic import BaseModel, Field, model_validator


class Unit(StrEnum):
    MILLION = "$MM"
    THOUSAND = "$K"

class BudgetRange(BaseModel):
    unit: Unit = Field(Unit.THOUSAND, description="The unit of the budget range.")

    lower_bound: float = Field(
        ..., description="The lower bound of the budget range for this channel."
    )
    upper_bound: float = Field(
        ..., description="The upper bound of the budget range for this channel."
    )

    @model_validator(mode='after')
    def check_bounds(self):
        if (self.lower_bound > self.upper_bound):
            raise ValueError("The lower bound must be less than or equal to the upper bound.")
        return self
    

class BudgetScenario(BaseModel):
    
    name: str = Field(
        ..., description="Please enter a descriptive name for this budget scenario", min_length=1
    )
    olv: BudgetRange = Field(
        ...,
        alias="Online Video",
        description="Please enter the budget range for OLV."
    )
    paid_search: BudgetRange = Field(
        ...,
        alias="Paid Search",
        description="Please enter the budget range for OLV."
    )
    total_budget: BudgetRange = Field(
        ...,
        alias="Total Budget",
        description="Please enter the total budget."
    )

    timout: int = Field(60, description="The max time for the optimizer in seconds.")
    n_trials: int = Field(1000, description="The max number of trials for the optimizer.")
   
