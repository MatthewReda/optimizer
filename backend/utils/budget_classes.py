from enum import StrEnum
from typing import Set

from pydantic import BaseModel, Field, model_validator


class Unit(StrEnum):
    MILLION = "$MM"
    THOUSAND = "$K"

class BudgetRange(BaseModel):
    unit: Unit = Field(Unit.THOUSAND, description="The unit of the budget range.")
    initial_budget: float = Field(
        ..., description="The initial budget for this channel.", ge=0
    )
    lower_bound: float = Field(
        ..., description="The lower bound of the budget range for this channel.", ge=0
    )
    upper_bound: float = Field(
        ..., description="The upper bound of the budget range for this channel.", ge=0
    )

    @model_validator(mode='after')
    def check_bounds(self):
        if (self.lower_bound > self.upper_bound):
            raise ValueError("The lower bound must be less than or equal to the upper bound.")
        return self
    

class BudgetScenario(BaseModel):
    
    name: str = Field(
        ..., description="Please enter a descriptive name for this budget scenario"
    )
    olv: BudgetRange = Field(
        ...,
        alias="Online Video",
        description="Please enter the budget range for OLV."
    )
    paid_search: BudgetRange = Field(
        ...,
        alias="Paid Search",
        description="Please enter the budget range for Paid Search."
    )
    total_budget: BudgetRange = Field(
        ...,
        alias="Total Budget",
        description="Please enter the total budget."
    )

    timout: int = Field(60, description="The max time for the optimizer in minutes for complex optimization at least 60 min is recommended.")
    n_trials: int = Field(1000, description="The max number of trials for the optimizer.")
   
