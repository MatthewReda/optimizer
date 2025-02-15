import plotly.graph_objects as go
from typing import Annotated

Budget = Annotated[dict[str, float], "The budget for the scenario."]

def make_radar_chart(initial_budget:Budget, optimized_budget:Budget) -> go.Figure:
    """Make a radar chart comparing the initial and optimized budgets"""
    
    categories = [key for key in initial_budget.keys() if 'total' not in key.lower()]
    
    fig = go.Figure()
    
    

    fig.add_trace(go.Scatterpolar(
        r=[initial_budget[cat]/initial_budget['total_budget']*100 for cat in categories],
        theta=categories,
        fill='toself',
        name='Initial Budget'
    ))
    fig.add_trace(go.Scatterpolar(
        r=[optimized_budget[cat]/initial_budget['total_budget']*100 for cat in categories],
        theta=categories,
        fill='toself',
        name='Optimized Budget'
    ))

    fig.update_layout(
    polar=dict(
        radialaxis=dict(
        visible=True,
        range=[0, 120]
        )),
    showlegend=False
    )
    
    return fig