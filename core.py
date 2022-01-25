from attrs import exceptions
import pandas as pd
import requests
import datetime
import threading
from io import StringIO
from os import listdir, remove as remove_file
from os.path import isfile
from utils import format_date
import streamlit as st
import plotly.express as px

file_folder = './files/'
url = 'https://covid.ourworldindata.org/data/owid-covid-data.csv'
today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)

file_name = f'data-covid-{today.strftime("%Y-%m-%d")}.csv'
current_file = file_folder +  file_name
th = None


def get_file():
    rq = requests.get(url)
    if rq.status_code != 200:
        raise Exception('Não foi possível acessar o arquivo')
    df = pd.read_csv(StringIO(rq.text))
    df.reset_index(inplace=True, drop=True)
    df = df[df['location'] != 'World']
    df = df[~df['continent'].isna()]
    df['date'] = pd.to_datetime(df.date, format='%Y-%m-%d')
    df.drop(columns=['new_deaths_smoothed', 'total_cases_per_million',
       'new_cases_per_million', 'new_cases_smoothed_per_million',
       'total_deaths_per_million', 'new_deaths_per_million',
       'new_deaths_smoothed_per_million', 'reproduction_rate', 'icu_patients',
       'icu_patients_per_million', 'hosp_patients',
       'hosp_patients_per_million', 'weekly_icu_admissions',
       'weekly_icu_admissions_per_million', 'weekly_hosp_admissions',
       'weekly_hosp_admissions_per_million', 'new_tests', 'total_tests',
       'total_tests_per_thousand', 'new_tests_per_thousand',
       'new_tests_smoothed', 'new_tests_smoothed_per_thousand',
       'positive_rate', 'tests_per_case', 'tests_units', 'total_vaccinations',
       'people_vaccinated', 'people_fully_vaccinated', 'total_boosters',
       'new_vaccinations', 'new_vaccinations_smoothed',
       'total_vaccinations_per_hundred', 'people_vaccinated_per_hundred',
       'people_fully_vaccinated_per_hundred', 'total_boosters_per_hundred',
       'new_vaccinations_smoothed_per_million',
       'new_people_vaccinated_smoothed',
       'new_people_vaccinated_smoothed_per_hundred', 'stringency_index',
       'population', 'population_density', 'median_age', 'aged_65_older',
       'aged_70_older', 'gdp_per_capita', 'extreme_poverty',
       'cardiovasc_death_rate', 'diabetes_prevalence', 'female_smokers',
       'male_smokers', 'handwashing_facilities', 'hospital_beds_per_thousand',
       'life_expectancy', 'human_development_index',
       'excess_mortality_cumulative_absolute', 'excess_mortality_cumulative',
       'excess_mortality', 'excess_mortality_cumulative_per_million'], inplace=True)
    df_country_pt = pd.read_csv('Countries_pt.csv')
    df_country_pt.set_index('country', inplace=True)


    df['country_pt'] = df['location'].apply(lambda value : df_country_pt.loc[value].name_pt)
    df.to_csv(file_folder+file_name, index=False)
    files = [_ for _ in listdir(path=file_folder) if not file_name in _]
    if len(files) > 1:
        for file in files:
            remove_file(f'{file_folder}{file}')
def add_date_picker(df:pd.DataFrame):
    st.markdown("""---""")
    dates = [pd.to_datetime(_).date().strftime('%Y-%m-%d') for _ in df['date'].unique()]
    min_value=df.iloc[0]['date'].strftime('%Y-%m-%d')
    max_value=df.iloc[-1]['date'].strftime('%Y-%m-%d')
    init_date, end_date = st.select_slider("Selecione", options=dates, value=(min_value, max_value))
    return df[(df['date'] >= pd.to_datetime(init_date, format='%Y-%m-%d')) & (df['date'] <= pd.to_datetime(end_date, format='%Y-%m-%d'))]

def get_dataframe():
    global th
    if not isfile(current_file):
        th = threading.Thread(target=get_file, name='Downloader')
        th.start()
    n_files = len(listdir(path=file_folder))
    files = [_ for _ in listdir(path=file_folder) if not file_name in _]
    if n_files == 0:
        return False
    elif n_files > 1:
        for file in files:
            remove_file(f'{file_folder}{file}')
    if len(listdir(path=file_folder)) > 0:
        file = file_folder + listdir(path=file_folder)[0]
    else:
        return False
    df = pd.read_csv(file)
    df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
    df.sort_values(by=['date'], inplace=True, ascending=True)
    return df

def populate_metrics(df : pd.DataFrame):
    date = df.iloc[-1]['date']
    cases, deaths = get_totals(df, date)
    new_cases, new_deaths = get_new(df, date)
    
    st.title(f'Dados Covid - Atualizado em {date.strftime("%d/%m/%Y")}')
    st.header(f'Consolidado')
    c_new_cases, c_new_deaths = st.columns(2)
    st.markdown("""---""")
    c_total_cases, c_total_deaths = st.columns(2)
    c_total_cases.metric("Total de casos", f'{int(cases):,d}'.replace(',','.'), '')
    c_total_deaths.metric("Total de mortos", f'{int(deaths):,d}'.replace(',','.'), '')
    
    c_new_cases.metric('Novos casos', f'{int(new_cases):,d}'.replace(',','.'),'')
    c_new_deaths.metric('Novas mortes', f'{int(new_deaths):,d}'.replace(',','.'),'')

def populate_graphics(df : pd.DataFrame, mean: int):
    if isinstance(mean, int):
        try:
            mean = int(mean)
        except Exception as e:
            mean = 7
    deaths_df = df.groupby(["date"], as_index=False)['new_deaths'].sum()
    deaths_df.set_index('date', inplace=True)
    deaths_df.rename({'new_deaths':'Mortes'}, axis=1, inplace=True)
    deaths_df['media'] = deaths_df.rolling(mean, min_periods=1).mean().round(0)
    fig_deaths = px.line(
        x=deaths_df.index, 
        y=deaths_df[f'media'], 
        color=px.Constant(f'{mean} dias'), 
        labels=dict(y='Total de Mortes', x='Dia', color='Média')
        )
    fig_deaths.add_bar(
        x=deaths_df.index,
        y=deaths_df['Mortes'],
        name='Mortes dia'
    )
    
    fig_deaths.update_layout(autosize=True, legend=dict(orientation='h'))
    st.markdown("""---""")
    st.header('Evolução de mortes por dia')
    st.plotly_chart(fig_deaths, use_container_width=True)
    
    cases_df = df.groupby(["date"], as_index=False)['new_cases'].sum()
    cases_df.set_index('date', inplace=True)
    cases_df.rename({'new_cases':'Casos'}, axis=1, inplace=True)
    cases_df['media'] = cases_df.rolling(mean, min_periods=1).mean().round(0)
    fig_cases = px.line(
        x=cases_df.index, 
        y=cases_df[f'media'], 
        color=px.Constant(f'{mean} dias'), 
        labels=dict(y='Total de Casos', x='Dia', color='Média')
        )
    fig_cases.add_bar(
        x=cases_df.index,
        y=cases_df['Casos'],
        name='Casos dia'
    )
    fig_cases.update_layout(autosize=True, legend=dict(orientation='h'))
    st.markdown("""---""")
    st.header('Evolução de casos por dia')
    st.plotly_chart(fig_cases, use_container_width=True)

def get_totals(df : pd.DataFrame, date):
    df = df.sort_values(by='date', ascending=False)
    total_deaths = df[df['date'] == date]['total_deaths'].sum()
    total_cases = df[df['date'] == date]['total_cases'].sum()
    return [total_cases, total_deaths]

def get_new(df : pd.DataFrame, date):
    df = df.sort_values(by='date', ascending=False)
    new_deaths = df[df['date'] == date]['new_deaths'].sum()
    new_cases = df[df['date'] == date]['new_cases'].sum()
    return [new_cases, new_deaths]