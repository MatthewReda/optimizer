import plotly.graph_objects as go
import numpy as np
from typing import Annotated
from utils.study_helpers import Study, Trial

Budget = Annotated[dict[str, float], "The budget for the scenario."]


def make_radar_chart(initial_budget: Budget, optimized_budget: Budget) -> go.Figure:
    """Make a radar chart comparing the initial and optimized budgets"""

    # categories = [key for key in initial_budget.keys() if 'total' not in key.lower()]
    opt_categories = [
        key for key in optimized_budget.keys() if "total" not in key.lower()
    ]
    initial_total_budget = sum(initial_budget.values())
    fig = go.Figure()

    initial_r = [
        initial_budget[cat] / initial_total_budget * 100 for cat in opt_categories
    ]
    optimal_r = [
        optimized_budget[cat] / initial_total_budget * 100 for cat in opt_categories
    ]
    fig.add_trace(
        go.Scatterpolar(
            r=initial_r,
            theta=opt_categories,
            fill="toself",
            name="Initial Budget",
            hovertemplate="Channel: %{theta}<br>Percentage: %{r:.1f}%<br>Budget: $%{text}",
            text=[f"{budget*initial_total_budget/100:.2f}" for budget in initial_r],
            marker={"color": "#F3578E"},
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=optimal_r,
            theta=opt_categories,
            fill="toself",
            name="Optimized Budget",
            hovertemplate="Channel: %{theta}<br>Percentage: %{r:.1f}%<br>Budget: $%{text}",
            text=[f"{budget*initial_total_budget/100:.2f}" for budget in optimal_r],
            marker={"color": "#57F3BC"},
        )
    )
    # fig.update_layout(hovermode='theta unified')

    fig.update_layout(
        title="Initial vs Optimized Budget Allocation",
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1.2 * max(initial_r + optimal_r)])
        ),
        showlegend=True,
    )

    return fig


def make_trial_history_figure(revenue: list[float]) -> go.Figure:
    best_studys = []
    best_so_far = 0
    for trial in revenue:
        if trial > best_so_far:
            best_so_far = trial
        best_studys.append(best_so_far)

    index = np.arange(len(revenue))

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=index,
            y=revenue,
            mode="markers",
            hovertemplate="Predicted Revenue: $%{y:.0f}",
            name="Trial",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=index,
            y=best_studys,
            hovertemplate="Predicted Revenue: $%{y:.0f}",
            mode="lines",
            name="Best Value",
        )
    )
    fig.update_layout(
        title="Trial Progress",
        hovermode="x unified",
    )

    return fig

def make_parallel_coordinates_plot(study: Study) -> go.Figure:
    """Make a parallel coordinates plot of the study"""
    if len(study.trials) < 1:
        return go.Figure()

    categories = [key for key in study.trials[0].budget.keys() if "total" not in key.lower()]
    trials = [trial for trial in study.trials if trial.completed]
    if len(trials) < 1:
        return go.Figure()

    data = []
    for trial in trials:
        data.append([trial.budget[cat] for cat in categories] + trial.values)

    fig = go.Figure(
        data=[
            go.Parcoords(
                line=dict(
                    color=[trial.values[0] for trial in trials],
                    colorscale="blues",
                    showscale=True,),
                dimensions=[
                    dict(
                        label=cat,
                        values=[trial.budget[cat] for trial in trials],
                        range=[np.floor(min([trial.budget[cat] for trial in trials])), np.ceil(max([trial.budget[cat] for trial in trials]))],
                    )
                    for cat in categories
                ]
                + [
                    dict(
                        label="Revenue",
                        values=[trial.values[0] for trial in trials],
                        range=[np.floor(min([trial.values[0] for trial in trials])), np.ceil(max([trial.values[0] for trial in trials]))],
                    )
                ],
            )
        ],

    )

    fig.update_layout(
        title="Parallel Coordinates Plot",
        coloraxis_colorbar=dict(
            title=dict(text="Revenue"),
            thicknessmode="pixels", thickness=50,
            lenmode="pixels", len=200,
            yanchor="top", y=1,
            ticks="outside", tickprefix="$ ",
            dtick=5
        ),
        showlegend=True,
    )

    return fig


def color_to_hex(rgb):
    r = str(hex(rgb[0])).replace("0x", "")
    g = str(hex(rgb[1])).replace("0x", "")
    b = str(hex(rgb[2])).replace("0x", "")
    return f"#{r}{g}{b}"
