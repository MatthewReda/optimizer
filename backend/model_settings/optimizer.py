from budget_optimizer.utils.model_classes import BaseBudgetModel
from budget_optimizer.optimizer import OptunaBudgetOptimizer

from pathlib import Path


class BudgetModel(BaseBudgetModel):
    """
    Budget model class
    """

    ...


MODEL_PATH = Path(__file__).parent / "example_files/slow_model"

revenue_model = BudgetModel("Revenue Model", "Revenue", MODEL_PATH)


def create_optimizer(url: str, config_path: str) -> OptunaBudgetOptimizer:
    """Return an optimizer object"""
    optimizer = OptunaBudgetOptimizer(
        revenue_model,
        config_path=config_path,
        objective_name=revenue_model.model_kpi,
        storage=url,
        sampler_kwargs={},
    )
    return optimizer


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--OLV", type=float, default=0)
    parser.add_argument("--PaidSearch", type=float, default=0)
    args = parser.parse_args()
    budget = {"a": args.OLV, "b": args.PaidSearch}
    print(f"Total Revenue: ${revenue_model.predict(budget=budget).sum(...).item():.2f}")
