import httpx
from dataclasses import dataclass
import numpy as np
#from dotenv import load_dotenv
from utils.budget_classes import BudgetScenario, Budget
import os
from typing import TypedDict


class PredictionResponse(TypedDict):
    prediction: float


#load_dotenv()

BASE_URL = os.environ.get("POSTGRES_CONNECTION", "http://localhost:8000")
BUDGET_URL = f"{BASE_URL}/budget_scenario"
PREDICTION_URL = f"{BASE_URL}/predict"


@dataclass
class Trial:
    budget: dict[str, float]
    values: list[float]
    completed: bool


@dataclass
class Study:
    name: str
    trials: list[Trial]

    @property
    def best_trial(self):
        if len(self.trials) < 1:
            return None
        return sorted(
            self.trials, key=lambda x: x.values[0] if x.completed else -np.inf
        )[-1]


def process_study(study: dict[str, list[dict[str, any]]]) -> Study:
    """Process the response from the API to a study object"""

    assert len(study.keys()) == 1, "Only one study is allowed"
    name = list(study.keys())[0]
    trial_objects = []
    try:
        for trial in study[name]:
            trial_objects.append(
                Trial(
                    budget=trial["_user_attrs"]["budget"],
                    values=trial["_values"],
                    completed=trial["state"] == 1,
                )
            )
    except KeyError:
        print("Error processing study")
        return Study(name=name, trials=[Trial(budget={}, values=[], completed=False)])
    return Study(name=name, trials=trial_objects)


async def get_study(study_name: str, url: str = BUDGET_URL) -> Study:
    formated_url = f"{url}/{study_name}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(formated_url)
        response.raise_for_status()
    except httpx.RequestError as exc:
        print(f"A request error occurred: {exc}")
        return None
    except httpx.TimeoutException as exc:
        print(f"A timeout error occurred: {exc}")
        return None
    except httpx.HTTPStatusError as exc:
        print(f"A HTTP status error occurred: {exc}")
        if exc.response.status_code == 404:
            print(f"Study {study_name} not found")
        return None
    except httpx.HTTPError as exc:
        print(f"An error occurred: {exc}")
        return None

    return process_study(response.json())


async def get_study_settings(study_name: str, url: str = BUDGET_URL):
    formated_url = f"{url}/{study_name}/settings"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(formated_url)
        response.raise_for_status()
    except httpx.RequestError as exc:
        print(f"A request error occurred: {exc}")
        return None
    except httpx.TimeoutException as exc:
        print(f"A timeout error occurred: {exc}")
        return None
    except httpx.HTTPStatusError as exc:
        print(f"A HTTP status error occurred: {exc}")
        if exc.response.status_code == 404:
            print(f"Study {study_name} not found")
        return None
    except httpx.HTTPError as exc:
        print(f"An error occurred: {exc}")
        return None

    return response.json()


async def list_studies(url: str = BUDGET_URL) -> list[str]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
        response.raise_for_status()
    except httpx.RequestError as exc:
        print(f"A request error occurred: {exc}")
        return None
    except httpx.TimeoutException as exc:
        print(f"A timeout error occurred: {exc}")
        return None
    except httpx.HTTPStatusError as exc:
        print(f"A HTTP status error occurred: {exc}")
        return None
    except httpx.HTTPError as exc:
        print(f"An error occurred: {exc}")
        return None

    return response.json()["budget_scenarios"]


async def delete_study(study_name: str, url: str = BUDGET_URL) -> None:
    formated_url = f"{url}/{study_name}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(formated_url)
        response.raise_for_status()
    except httpx.RequestError as exc:
        print(f"A request error occurred: {exc}")
        return None
    except httpx.TimeoutException as exc:
        print(f"A timeout error occurred: {exc}")
        return None
    except httpx.HTTPStatusError as exc:
        print(f"A HTTP status error occurred: {exc}")
        if exc.response.status_code == 404:
            print(f"Study {study_name} not found")
        return None
    except httpx.HTTPError as exc:
        print(f"An error occurred: {exc}")
        return None


async def create_budget_scenario(data: BudgetScenario, url: str = BUDGET_URL) -> None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data.model_dump(by_alias=True))
        response.raise_for_status()
    except httpx.RequestError as exc:
        print(f"A request error occurred: {exc}")
        return None
    except httpx.TimeoutException as exc:
        print(f"A timeout error occurred: {exc}")
        return None
    except httpx.HTTPStatusError as exc:
        print(f"A HTTP status error occurred: {exc}")
        return None
    except httpx.HTTPError as exc:
        print(f"An error occurred: {exc}")
        return None


async def get_prediction(
    budget: Budget, url: str = PREDICTION_URL
) -> PredictionResponse | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=budget.model_dump(by_alias=True))
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as exc:
        print(f"A request error occurred: {exc}")
        return None
    except httpx.TimeoutException as exc:
        print(f"A timeout error occurred: {exc}")
        return None
    except httpx.HTTPStatusError as exc:
        print(f"A HTTP status error occurred: {exc}")
        return None
    except httpx.HTTPError as exc:
        print(f"An error occurred: {exc}")
        return None
