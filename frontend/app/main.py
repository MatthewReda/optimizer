# Frontend for budget optimization tool
from time import sleep
import asyncio
import json

import streamlit as st
import streamlit_pydantic as sp
import pandas as pd

from utils.budget_classes import BudgetScenario, ACCEPTED_CHANNELS, Budget
from utils.study_helpers import (
    get_study,
    list_studies,
    delete_study,
    create_budget_scenario,
    get_study_settings,
    get_prediction,
    Trial,
    Study
)
from utils.ui import make_radar_chart, make_trial_history_figure, make_parallel_coordinates_plot








st.set_page_config(layout="wide", page_title="Budget Scenario Optimizer")


def user_validator():
    return True


st.title("Budget Scenario Planner")

if "studies" not in st.session_state:
    st.session_state.studies = asyncio.run(list_studies())
    if st.session_state.studies is None:
        st.session_state.studies = []

if not user_validator():
    st.error("You are not authorized to use this app.")
    st.stop()


def wrap_delete_study(study_name):
    asyncio.run(delete_study(study_name))
    index = st.session_state.studies.index(study_name)
    st.session_state.studies.pop(index)

    st.toast(f"{study_name} deleted")
    sleep(5)


def refresh(study_name):
    st.session_state.studies = asyncio.run(list_studies())


def load_file():
    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
        try:
            return json.load(uploaded_file)
        except Exception as e:
            st.error("Error loading file")
            print("file", e)
            return None


@st.cache_data
def predict(budget) -> float:
    prediction = asyncio.run(get_prediction(Budget(**budget)))
    # print(prediction)
    if prediction is None:
        st.dialog("Could not predict")
        return -1
    return prediction["prediction"]


@st.cache_data
def convert_study(study):
    try:
        budget = [
            trial.budget | {"Revenue": trial.values[0]}
            for trial in study.trials
            if trial.completed
        ]

        df = pd.DataFrame(data=budget)
        return df.to_csv().encode("utf-8")
    except Exception:
        st.error("Error converting study to csv")
        # print("csv", e)
        return None

@st.cache_data
def cached_radar_chart(
    initial_budget: dict[str, float], 
    optimal_budget: dict[str, float]
):
    return make_radar_chart(initial_budget, optimal_budget)

@st.cache_data
def cached_trial_history_figure(revenue: list[float]):
    return make_trial_history_figure(revenue=revenue)

@st.cache_resource
def cached_parallel_coordinates_plot(study: Study):
    return make_parallel_coordinates_plot(study)

@st.cache_data
def trial_view(
    best_study: Trial | None,
    initial_budget: dict[str, float],
    prediction_with_zero_budget: float,
    prediction_with_initial_budget: float,
):
    """Initial Optimizer Overview"""
    try:
        ## Format Summary
        cols = st.columns(3)

        optimal_incremental_revenue = best_study.values[0] - prediction_with_zero_budget
        initial_incremental_revenue = (
            prediction_with_initial_budget - prediction_with_zero_budget
        )

        total_optimal_budget = sum(best_study.budget.values())
        total_initial_budget = sum(initial_budget.values())

        initial_roi = initial_incremental_revenue / total_initial_budget
        optimal_roi = optimal_incremental_revenue / total_optimal_budget

        cols[0].metric(
            label="Total Budget",
            value=f"${total_optimal_budget:0.2f}",
            delta=f"${total_optimal_budget-total_initial_budget:0.2f}",
            border=True,
        )

        cols[1].metric(
            label="Inc Revenue",
            value=f"${optimal_incremental_revenue:0.2f}",
            delta=f"${optimal_incremental_revenue-initial_incremental_revenue:0.2f}",
            border=True,
        )

        cols[2].metric(
            label="ROI",
            value=f"${optimal_roi:.2f}",
            delta=f"{optimal_roi/initial_roi-1: .1%}",
            border=True,
        )
    except TypeError:
        ...


@st.fragment(run_every=30)
def show_study(study_name):
    study = asyncio.run(get_study(study_name))
    if not study:
        sleep(5)
        st.rerun()
        return
    container = st.container(key=f"{study_name}_container", border=True, height=800)
    container.markdown(f"### {study_name}")

    ## Handle study initial settings
    study_settings = asyncio.run(get_study_settings(study_name))
    study_settings = study_settings if study_settings else {}
    if study_settings:
        initial_budget = {
            channel_setting["channel"]: channel_setting["initial_budget"]
            for channel_setting in study_settings["channel_settings"]
        }

        ## Predict revenue produced by original budget
        initial_prediction = predict(initial_budget)

        ## Predict base revenue
        zero_prediction = predict({name: 0 for name in initial_budget.keys()})

        ## Reformat budget to use human friendly names
        initial_budget = {
            name: initial_budget[name.lower().replace(" ", "_")]
            for name in ACCEPTED_CHANNELS
        }

    ## Handle best trial
    best_study = study.best_trial
    best_study = best_study if best_study else "No best trial yet"
    if isinstance(best_study, str):
        container.markdown(f"**{best_study}**")
        return

    ## Display trial metrics TOTAL_BUDGET INC_REVENUE ROIS
    with container:
        trial_view(
            best_study,
            initial_budget=initial_budget,
            prediction_with_initial_budget=initial_prediction,
            prediction_with_zero_budget=zero_prediction,
        )

    ## Button row
    columns = container.columns(5)
    columns[-1].button(
        "Delete",
        key=f"{study_name}_delete",
        type="primary",
        on_click=wrap_delete_study,
        args=(study_name,),
    )
    columns[-2].button(
        "Refresh",
        key=f"{study_name}_refresh",
        on_click=refresh,
        args=(study_name,),
        help="Refresh the study",
    )

    ## Additional study information
    tabs = container.tabs(["Best Trial", "Budget Trials", "Trial History", "Settings"])
    with tabs[0]:
        ## Display radar chart to compare budget allocations
        try:
            if budget := best_study.budget:
                pyplot = cached_radar_chart(initial_budget, budget)
                st.plotly_chart(pyplot, use_container_width=True)

            columns[0].download_button(
                "Download",
                convert_study(study),
                f"{study_name}_trials.csv",
                key=f"{study_name}_download",
                mime="text/csv",
            )
        except Exception:
            st.error("Error processing best trial")
    with tabs[1]:

        try:
            ## Display parallel coordinates plot to compare budget allocations
            fig = cached_parallel_coordinates_plot(study)
            st.plotly_chart(fig, use_container_width=False, theme=None)

        except ValueError:
            st.error("Error processing budget trials")

    with tabs[2]:
        ## Optimizer history for
        try:
            revenue = [trial.values[0] for trial in study.trials if trial.completed]
            fig = cached_trial_history_figure(revenue=revenue)
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Error processing trial history {e}")
    with tabs[3]:
        try:
            initial_df = pd.DataFrame(data=initial_budget, index=["Initial Budget"])
            initial_df["Total"] = initial_df.sum(axis=1)
            optimal_df = pd.DataFrame(data=best_study.budget, index=["Optimal Budget"])
            optimal_df["Total"] = optimal_df.sum(axis=1)
            combined_df = pd.concat([initial_df, optimal_df]).T

            combined_df["Diff"] = (
                combined_df["Optimal Budget"] / combined_df["Initial Budget"] - 1
            ) * 100
            st.dataframe(
                combined_df,
                column_config={
                    "Initial Budget": st.column_config.NumberColumn(
                        "Initial Budget", format="$%.2f"
                    ),
                    "Optimal Budget": st.column_config.NumberColumn(
                        "Optimal Budget", format="$%.2f"
                    ),
                    "Diff": st.column_config.NumberColumn(
                        "% Difference", format="%.1f"
                    ),
                },
            )
        except Exception:
            st.error("Error processing settings")


@st.dialog("Create Budget Scenario", width="large")
def _create_budget_scenario():
    file = load_file()
    data = sp.pydantic_form(key="Budget Scenario", model=BudgetScenario)
    if data or file:
        if file:
            data = BudgetScenario(**file)
        asyncio.run(create_budget_scenario(data))
        st.session_state.studies.append(data.name)
        st.toast(f"{data.name} created")
        sleep(1)
        st.rerun()


if st.button("Create Budget Scenario"):
    _create_budget_scenario()


columns = st.columns(2)
if st.session_state.studies:
    for i, study_name in enumerate(st.session_state.studies):
        with columns[i % 2]:
            show_study(study_name)
