import plotly.graph_objects as go
from typing import Annotated

Budget = Annotated[dict[str, float], "The budget for the scenario."]

def make_radar_chart(initial_budget:Budget, optimized_budget:Budget) -> go.Figure:
    """Make a radar chart comparing the initial and optimized budgets"""
    
    #categories = [key for key in initial_budget.keys() if 'total' not in key.lower()]
    opt_categories = [key for key in optimized_budget.keys() if 'total' not in key.lower()]

    fig = go.Figure()
    
    initial_r = [initial_budget[cat.lower().replace(" ", "_")]/initial_budget['total_budget']*100 for cat in opt_categories]
    optimal_r = [optimized_budget[cat]/initial_budget['total_budget']*100 for cat in opt_categories]
    fig.add_trace(go.Scatterpolar(
        r=initial_r,
        theta=opt_categories,
        fill='toself',
        name='Initial Budget',
        hovertemplate="Category: %{theta}<br>Percentage: %{r:.1f}%"
    ))
    fig.add_trace(go.Scatterpolar(
        r=optimal_r,
        theta=opt_categories,
        fill='toself',
        name='Optimized Budget',
        hovertemplate="Category: %{theta}<br>Percentage: %{r:.1f}%"
    ))
    #fig.update_layout(hovermode='theta unified')
    fig.update_layout(
    polar=dict(
        radialaxis=dict(
        visible=True,
        range=[0, 1.2*max(initial_r+optimal_r)]
        )),
    showlegend=False,
   
    )

    return fig