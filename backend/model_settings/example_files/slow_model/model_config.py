import xarray as xr
from pathlib import Path
import numpy as np
from budget_optimizer.utils.model_helpers import AbstractModel, BudgetType, load_yaml
from time import sleep

INITIAL_BUDGET: BudgetType = load_yaml(Path(__file__).parent.parent / "optimizer_config.yaml")["initial_budget"]

class SimpleModel(AbstractModel):
  """
  Simple model that just adds the two variables a and b.
  This can be as complex as you want as long as it has a predict method
  that takes an xarray Dataset and returns an xarray DataArray and 
  a contributions method that takes an xarray Dataset and returns an xarray Dataset.
  
  Ideally, the model should also have data that defines the initial data that the
  model was trained on. You can wrap cutom models or functions in a class like this.
  """
  def __init__(self, data: xr.Dataset = None):
    self.data = data
    
  def predict(self, x: xr.Dataset) -> xr.DataArray:
    x = x.copy()
    sleep(2) # Simulate a long computation
    x["prediction"] = np.exp(
      1 
      + .2*(x["OLV"]**2/(x["OLV"]**2 + np.exp(1)**2)) 
      + .25*(x["Paid Search"]**4/(x["Paid Search"]**4 + np.exp(2)**4))
      + .15*(x["Print"]**3/(x["Print"]**3 + np.exp(3)**3))
      + .1*(x["Radio"]**2/(x["Radio"]**2 + np.exp(4)**2))
      )

    return x["prediction"]
  
  def contributions(self, x: xr.Dataset) -> xr.Dataset:
    return x

def budget_to_data(budget: BudgetType, model: AbstractModel) -> xr.Dataset:
    data = model.data.copy()
    for key, value in budget.items():
        data[key] = value/INITIAL_BUDGET[key]*data[key]
    return data
  
def model_loader(path: Path) -> AbstractModel:
    rng = np.random.default_rng(42)
    data_olv = xr.DataArray(np.exp(1+rng.normal(0, .4, size=156)), dims='time', coords={"time": np.arange(1, 157)})
    data_paid_search = xr.DataArray(np.exp(2+rng.normal(0, .2, size=156)), dims='time', coords={"time": np.arange(1, 157)})
    data_print = xr.DataArray(np.exp(1+rng.normal(0, .3, size=156)), dims='time', coords={"time": np.arange(1, 157)})
    data_radio = xr.DataArray(np.exp(1+rng.normal(0, .4, size=156)), dims='time', coords={"time": np.arange(1, 157)})
    return SimpleModel(data = xr.Dataset({"OLV": data_olv, "Paid Search": data_paid_search, "Print": data_print, "Radio": data_radio}))

