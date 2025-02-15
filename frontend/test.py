from enum import StrEnum
from typing import Set
from utils.budget_classes import BudgetScenario, ACCEPTED_CHANNELS, Budget
from utils.study_helpers import (
    get_study, list_studies, 
    delete_study, create_budget_scenario, 
    get_study_settings, get_prediction)
from utils.ui import make_radar_chart

import streamlit as st
from pydantic import BaseModel, Field, model_validator
import asyncio

from streamlit_autorefresh import st_autorefresh

import streamlit_pydantic as sp
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from time import sleep
import json


st.set_page_config(layout="wide")
def user_validator():
    return True

st.title("Budget Scenario Planner")

if "studies" not in st.session_state:
    st.session_state.studies = asyncio.run(list_studies())

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
    #print(prediction)
    if prediction is None:
        st.dialog("Could not predict")
        return -1
    return prediction["prediction"]

@st.cache_data
def convert_study(study):
    try:
        budget = [trial.budget|{"Revenue": trial.values[0]} for trial in study.trials if trial.completed]
        
        df = pd.DataFrame(data=budget)
        return df.to_csv().encode('utf-8')
    except Exception as e:
        st.error("Error converting study to csv")
        #print("csv", e)
        return None

@st.fragment(run_every=30)
def show_study(study_name):
    study = asyncio.run(get_study(study_name))
    if not study:
        sleep(5)
        st.rerun()
        return
    container = st.container(key=f"{study_name}_container", border=True, height=800)
    container.markdown(f"### {study_name}")
    columns = container.columns(5)
    study_settings = asyncio.run(get_study_settings(study_name))
    study_settings = study_settings if study_settings else {}
    if study_settings:
        initial_budget = {channel_setting['channel']: channel_setting['initial_budget'] for channel_setting in study_settings['channel_settings']}
        initial_prediction = predict(initial_budget)
        #print(initial_prediction)
        zero_prediction = predict({name: 0 for name in initial_budget.keys()})
        initial_budget = {name: initial_budget[name.lower().replace(" ","_")] for name in ACCEPTED_CHANNELS}
    
    columns[-1].button("", key=f"{study_name}_delete", type='primary', icon='🗑️', on_click=wrap_delete_study, args=(study_name,))
    columns[-2].button("Refresh", key=f"{study_name}_refresh", on_click=refresh, args=(study_name,), help="Refresh the study")
    best_study = study.best_trial
    best_study = best_study if best_study else "No best trial yet"
    if isinstance(best_study, str):
        container.markdown(f"**{best_study}**")
        return
        
    tabs = container.tabs(["Best Trial", "Trial History", "Settings"])
    with tabs[0]:
        try:
            cols = st.columns([2, 2, 2])
            opt_inc_rev = best_study.values[0] - zero_prediction
            initial_inc_rev = initial_prediction - zero_prediction
            optimal_total_budget = sum(best_study.budget.values())
            initial_total_budget = sum(initial_budget.values())
            initial_roi = initial_inc_rev/initial_total_budget
            optimal_roi = opt_inc_rev/optimal_total_budget
            cols[0].metric(
                label="Total Budget",
                value=f"${optimal_total_budget:0.2f}",
                delta=f"${optimal_total_budget-initial_total_budget:0.2f}",
                border=True
            )
            cols[1].metric(
                label="Inc Revenue", 
                value=f"${opt_inc_rev:0.2f}", 
                delta=f"${opt_inc_rev-initial_inc_rev:0.2f}",
                border=True
                )
            cols[2].metric(
                label="ROI",
                value=f"${optimal_roi:.2f}",
                delta=f"{optimal_roi/initial_roi-1: .1%}",
                border=True

            )
            # st.markdown(
            #     (
            #         f"### Revenue: ${best_study.values[0]:,.2f}\t"
            #         f"Total Budget: {sum(best_study.budget.values()):,.2f}"
            #     )
            # )
    
            if budget := best_study.budget:
                pyplot = make_radar_chart(initial_budget, budget)
                #fig, ax = plt.subplots(facecolor='none', figsize=(4, 4))
                #ax.pie(list(budget.values()), labels=list(budget.keys()), autopct='%1.1f%%', startangle=90)
                #ax.legend(ncols=2)
                st.plotly_chart(pyplot, use_container_width=True)

            columns[0].download_button('Download', convert_study(study), f'{study_name}_trials.csv', key=f"{study_name}_download", mime='text/csv')
        except Exception as e:
            st.error("Error processing best trial")

    with tabs[1]:
        try:
            revenue = [trial.values[0] for trial in study.trials if trial.completed]
            best_studys = []
            best_so_far = 0
            for trial in study.trials:
                if not trial.completed:
                    continue
                if trial.values[0] > best_so_far:
                    best_so_far = trial.values[0]
                best_studys.append(best_so_far)

            index = np.arange(len(revenue))
            fig, ax = plt.subplots(facecolor='gray', figsize=(4, 4),clear=True)
            ax.scatter(index, revenue, s=2)
            ax.plot(index, best_studys, color='red')
            ax.set_xlabel("Trials")
            ax.set_ylabel("Revenue")
            st.pyplot(fig, clear_figure=True)
        except Exception as e:
            st.error("Error processing trial history")
    with tabs[2]:
        
        try:
            initial_df = pd.DataFrame(data=initial_budget, index=["Initial Budget"])
            initial_df["Total"] = initial_df.sum(axis=1)
            optimal_df = pd.DataFrame(data=best_study.budget, index=["Optimal Budget"])
            optimal_df["Total"] = optimal_df.sum(axis=1)
            combined_df = pd.concat([initial_df, optimal_df]).T
            
            combined_df["Diff"] = (combined_df["Optimal Budget"]/combined_df['Initial Budget'] - 1)*100
            st.dataframe(combined_df, column_config = {
                "Initial Budget": st.column_config.NumberColumn("Initial Budget", format="$%.2f"),
                "Optimal Budget": st.column_config.NumberColumn("Optimal Budget", format="$%.2f"),
                "Diff": st.column_config.NumberColumn("% Difference", format="%.1f")
            })
        except Exception as e:
            st.error("Error processing settings")
       


@st.dialog("Create Budget Scenario")
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
    
