from enum import StrEnum

from pydantic import BaseModel, Field, model_validator, create_model


ACCEPTED_CHANNELS = ["OLV", "Paid Search", "Print", "Radio"]


class Unit(StrEnum):
    MILLION = "$MM"
    THOUSAND = "$K"


class ChannelBudget(BaseModel):
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

    @model_validator(mode="after")
    def check_bounds(self):
        if self.lower_bound > self.upper_bound:
            raise ValueError(
                "The lower bound must be less than or equal to the upper bound."
            )
        return self


Budget = create_model(
    "Budget",
    **{
        channel.lower().replace(" ", "_"): (
            float,
            Field(..., description="Spend for this channel", ge=0),
        )
        for channel in ACCEPTED_CHANNELS
    },
)

BUDGET_FIELDS = (
    {
        "name": (
            str,
            Field(
                ...,
                description="Please enter a descriptive name for this budget scenario",
                min_length=1,
            ),
        ),
    }
    | {
        channel.lower().replace(" ", "_"): (
            ChannelBudget,
            Field(
                ...,
                description=f"Please enter the budget range for {channel}.",
                alias=channel,
            ),
        )
        for channel in ACCEPTED_CHANNELS + ["Total Budget"]
    }
    | {
        "timeout": (
            int,
            Field(60, description="The max time for the optimizer in seconds."),
        ),
        "n_trials": (
            int,
            Field(1000, description="The max number of trials for the optimizer."),
        ),
    }
)

BudgetScenario = create_model("BudgetScenario", **BUDGET_FIELDS)

# class BudgetScenario(BaseModel):

#     name: str = Field(
#         ..., description="Please enter a descriptive name for this budget scenario", min_length=1
#     )

#     channel_budgets: List[ChannelBudget] = Field(
#         ..., description="The budget ranges for each channel.",
#         min_length=3, max_length=3
#     )

#     timout: int = Field(60, description="The max time for the optimizer in seconds.")
#     n_trials: int = Field(1000, description="The max number of trials for the optimizer.")
