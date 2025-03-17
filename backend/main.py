# from __future__ import annotations as _annotations
import os
from pathlib import Path
import traceback
import multiprocessing as mp
from typing import Annotated, List

import fastapi
from fastapi import HTTPException, Depends
from model_settings.optimizer import revenue_model, create_optimizer
import optuna
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel, create_engine, select, Relationship
from dotenv import load_dotenv

from utils.budget_classes import BudgetScenario, ACCEPTED_CHANNELS, Budget

load_dotenv()

origins = ["http://localhost:8000", "http://localhost:8080", "http://docker.host.internal:8000", "http://0.0.0.0:8000"]

if os.environ.get("ALLOWED_ORIGINS", ""):
    origins = os.environ.get("ALLOWED_ORIGINS").split(",")

app = fastapi.FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


SECONDS_IN_MINUTE = 60


def get_session():
    with Session(app.state.engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


class BudgetScenarioSettings(SQLModel, table=True):
    __tablename__ = "budgetscenariosettings"
    name: str = Field(primary_key=True)
    # total_budget: float = Field(default=Field(..., ge=0))
    budget: List["BudgetSettings"] = Relationship(
        back_populates="budget_scenario", cascade_delete=True
    )


class BudgetSettings(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    study_name: str = Field(index=True, foreign_key="budgetscenariosettings.name")
    channel: str = Field(index=True)
    initial_budget: float
    lower_bound: float
    upper_bound: float
    budget_scenario: BudgetScenarioSettings = Relationship(back_populates="budget")


class OptimizerProcess(mp.Process):
    def __init__(self, url: str, budget_scenario: BudgetScenario, *args, **kwargs):
        mp.Process.__init__(self, *args, **kwargs)
        self.daemon = True
        self.budget_scenario = budget_scenario
        self.timeout = budget_scenario.timeout
        self.n_trials = budget_scenario.n_trials
        self.url = url
        self._pconn, self._cconn = mp.Pipe()
        self._exception = None

    def run(self):
        try:
            print("Running...")
            self._cconn.send("running")
            _optimize(self.url, self.budget_scenario, self.timeout, self.n_trials)
            print("Done")
            self._cconn.send("done")

        except Exception as e:
            tb = traceback.format_exc()
            self._cconn.send((e, tb))

        # You can still rise this exception if you need to

    def terminate(self):
        print("Terminating...")
        super().terminate()

    def join(self):
        print("Joining...")
        super().join()

    @property
    def exception(self):
        if self._pconn.poll():
            self._exception = self._pconn.recv()
        return self._exception


def _optimize(
    url,
    budget_scenario: BudgetScenario,
    timeout: int,
    n_trials: int,
    load_if_exists: bool = False,
) -> None:
    config_path = Path(__file__).parent / "model_settings/example_files"
    optimizer = create_optimizer(url, config_path)
    bounds = {
        channel: (
            getattr(budget_scenario, channel.lower().replace(" ", "_")).lower_bound,
            getattr(budget_scenario, channel.lower().replace(" ", "_")).upper_bound,
        )
        for channel in ACCEPTED_CHANNELS
    }

    constraints = (
        budget_scenario.total_budget.lower_bound,
        budget_scenario.total_budget.upper_bound,
    )
    print(bounds, constraints)
    optimizer.optimize(
        bounds,
        constraints=constraints,
        study_name=budget_scenario.name,
        n_trials=n_trials,
        n_jobs=1,
        timeout=timeout * SECONDS_IN_MINUTE,
        load_if_exists=load_if_exists,
    )


@app.post("/budget_scenario")
async def create_budget_scenario(budget_scenario: BudgetScenario, session: SessionDep):
    """
    Create a budget scenario
    """
    try:
        print(budget_scenario)
        if budget_scenario.name in optuna.study.get_all_study_names(
            storage=app.state.database_url
        ):
            raise HTTPException(
                status_code=400, detail="Budget scenario already exists"
            )
        if budget_scenario.name in app.state.RUNNING_PROCESSES:
            raise HTTPException(
                status_code=400, detail="Budget scenario is already running"
            )

        app.state.RUNNING_PROCESSES[budget_scenario.name] = OptimizerProcess(
            app.state.database_url, budget_scenario
        )
        app.state.RUNNING_PROCESSES[budget_scenario.name].start()

        budget_scenario_setting = BudgetScenarioSettings(
            name=budget_scenario.name,
            budget=[
                BudgetSettings(
                    study_name=budget_scenario.name,
                    channel="total_budget",
                    initial_budget=budget_scenario.total_budget.initial_budget,
                    lower_bound=budget_scenario.total_budget.lower_bound,
                    upper_bound=budget_scenario.total_budget.upper_bound,
                )
            ]
            + [
                BudgetSettings(
                    study_name=budget_scenario.name,
                    channel=channel.lower().replace(" ", "_"),
                    initial_budget=getattr(
                        budget_scenario, channel.lower().replace(" ", "_")
                    ).initial_budget,
                    lower_bound=getattr(
                        budget_scenario, channel.lower().replace(" ", "_")
                    ).lower_bound,
                    upper_bound=getattr(
                        budget_scenario, channel.lower().replace(" ", "_")
                    ).upper_bound,
                )
                for channel in ACCEPTED_CHANNELS
            ],
        )

        session.add(budget_scenario_setting)
        session.commit()

        session.refresh(budget_scenario_setting)
    except Exception as e:
        return {"Error": str(e)}
    return {"Optimizer started": budget_scenario.name}


@app.get("/budget_scenario")
async def get_budget_scenarios():
    """
    Get all budget scenarios
    """
    try:
        return {
            "budget_scenarios": optuna.study.get_all_study_names(
                storage=app.state.database_url
            )
        }
    except Exception:
        return {"budget_scenarios": []}


@app.get("/budget_scenario/{name}")
async def get_budget_scenario(name: str):
    """
    Get a budget scenario by name
    """
    try:
        return {
            name: optuna.study.load_study(
                study_name=name, storage=app.state.database_url
            ).trials
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="Budget scenario not found")


@app.get("/budget_scenario/{name}/settings")
async def get_budget_scenario_settings(name: str, session: SessionDep):
    """
    Get the settings for a budget scenario
    """
    scenario = session.get(BudgetScenarioSettings, name, populate_existing=True)
    settings = session.exec(
        select(BudgetSettings).where(BudgetSettings.study_name == name)
    ).all()

    if scenario or settings:
        return {"scenario": scenario, "channel_settings": settings}
    raise HTTPException(status_code=404, detail="Budget scenario not found")


@app.get("/budget_scenario/{name}/best_trial")
async def get_best_trial(name: str):
    """
    Get the best trial for a budget scenario
    """
    return {
        name: optuna.study.load_study(name, storage=app.state.database_url).best_trial
    }


@app.delete("/budget_scenario/{name}")
async def delete_budget_scenario(name: str, session: SessionDep):
    """
    Delete a budget scenario
    """
    try:
        optuna.study.delete_study(study_name=name, storage=app.state.database_url)

        scenario = session.get(BudgetScenarioSettings, name)
        if scenario:
            session.delete(scenario)
            session.commit()
        return {"Deleted": name}
    except KeyError:
        raise HTTPException(status_code=404, detail="Budget scenario not found")


@app.post("/predict")
async def predict_budget(budget: Budget):
    budget_dict = {
        channel: getattr(budget, channel.lower().replace(" ", "_"))
        for channel in ACCEPTED_CHANNELS
    }

    prediction: float = revenue_model.predict(budget_dict).sum(...).item()

    return {"prediction": prediction}


def create_db_and_tables():
    SQLModel.metadata.create_all(app.state.engine, checkfirst=False, echo=True)


@app.on_event("startup")
async def startup():
    import os

    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "h!ggsb0s0n")
    db = os.environ.get("POSTGRES_DB", "optimizer")
    port = os.environ.get("POSTGRES_PORT", 5432)
    host = os.environ.get("POSTGRES_HOST", 'localhost')
    app.state.database_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"

    try:
        app.state.engine = create_engine(app.state.database_url)
    except:
        print("Error connecting to database")
        import psycopg2
        from psycopg2 import sql
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT  # <-- ADD THIS LINE

        con = psycopg2.connect(user=user, host=host, port=port, password=password)
        con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)  # <-- ADD THIS LINE

        cur = con.cursor()

        # Use the psycopg2.sql module instead of string concatenation
        # in order to avoid sql injection attacks.
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db)))
        cur.close()
        con.close()
        app.state.engine = create_engine(app.state.database_url)
    SQLModel.metadata.create_all(app.state.engine, checkfirst=True)
    app.state.RUNNING_PROCESSES = {}


@app.on_event("shutdown")
async def shutdown():
    for name, process in app.state.RUNNING_PROCESSES.items():
        process.terminate()
        process.join()
    app.state.RUNNING_PROCESSES = {}
    print("Shutdown")
