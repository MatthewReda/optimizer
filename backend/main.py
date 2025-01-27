from __future__ import annotations as _annotations

import fastapi
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
import asyncpg
from utils.budget_classes import BudgetScenario
from model_settings.optimizer import revenue_model, create_optimizer
import multiprocessing as mp
import optuna
from pathlib import Path
import traceback



app = fastapi.FastAPI()

SECONDS_IN_MINUTE = 60

class OptimizerProcess(mp.Process):
    def __init__(self, url: str, budget_scenario: BudgetScenario, *args, **kwargs):
        mp.Process.__init__(self, *args, **kwargs)
        self.daemon = True
        self.budget_scenario = budget_scenario
        self.timeout = budget_scenario.timout
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
    
    

def _optimize(url, budget_scenario: BudgetScenario, timeout: int, n_trials:int, load_if_exists: bool = False) -> None:
    config_path = Path(__file__).parent/"model_settings/example_files"
    optimizer = create_optimizer(url, config_path)
    bounds = {
        "a": (budget_scenario.olv.lower_bound, budget_scenario.olv.upper_bound), 
        "b": (budget_scenario.paid_search.lower_bound, budget_scenario.paid_search.upper_bound)}
    constraints = (budget_scenario.total_budget.lower_bound, budget_scenario.total_budget.upper_bound)
    optimizer.optimize(
        bounds, constraints=constraints, 
        study_name=budget_scenario.name,
         n_trials=n_trials, n_jobs=1, 
         timeout=timeout*SECONDS_IN_MINUTE,
         load_if_exists=load_if_exists)

@app.post("/budget_scenario")
async def create_budget_scenario(budget_scenario: BudgetScenario):
    """
    Create a budget scenario
    """
    try:
        if budget_scenario.name in optuna.study.get_all_study_names(storage=app.state.database_url):
            raise HTTPException(status_code=400, detail="Budget scenario already exists")
        if budget_scenario.name in app.state.RUNNING_PROCESSES:
            raise HTTPException(status_code=400, detail="Budget scenario is already running")
        
        app.state.RUNNING_PROCESSES[budget_scenario.name] = OptimizerProcess(app.state.database_url, budget_scenario)
        app.state.RUNNING_PROCESSES[budget_scenario.name].start()

    except Exception as e:
        return {"Error": str(e)}
    return {"Optimizer started": budget_scenario.name}



@app.get("/budget_scenario")
async def get_budget_scenarios():
    """
    Get all budget scenarios
    """
    return {"budget_scenarios": optuna.study.get_all_study_names(storage=app.state.database_url)}

@app.get("/budget_scenario/{name}")
async def get_budget_scenario(name: str):
    """
    Get a budget scenario by name
    """
    try:
        return {name: optuna.study.load_study(study_name=name, storage=app.state.database_url).trials}
    except KeyError:
        raise HTTPException(status_code=404, detail="Budget scenario not found")

@app.get("/budget_scenario/{name}/best_trial")
async def get_best_trial(name: str):
    """
    Get the best trial for a budget scenario
    """
    return {name: optuna.study.load_study(name, storage=app.state.database_url).best_trial}

@app.delete("/budget_scenario/{name}")
async def delete_budget_scenario(name: str):
    """
    Delete a budget scenario
    """
    try:
        optuna.study.delete_study(name, storage=app.state.database_url)
        return {"Deleted": name}
    except KeyError:
        raise HTTPException(status_code=404, detail="Budget scenario not found")


@app.on_event("startup")
async def startup():
    import os
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    db = os.environ.get("POSTGRES_DB")
    port = os.environ.get("POSTGRES_PORT")
    host = os.environ.get("POSTGRES_HOST")
    app.state.database_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    app.state.RUNNING_PROCESSES = {}

@app.on_event("shutdown")
async def shutdown():
    for name, process in app.state.RUNNING_PROCESSES.items():
        process.terminate()
        process.join()
    app.state.RUNNING_PROCESSES = {}
    print("Shutdown")