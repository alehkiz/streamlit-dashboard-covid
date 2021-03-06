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
    df = df.sort_values(by='date', ascending=True)
    if df[df['date'] == df.iloc[-1]['date']]['total_deaths'].sum() == 0 or df[df['date'] == df.iloc[-1]['date']]['total_cases'].sum() == 0:
        df = df[df['date'] != df.iloc[-1]['date']]
    df.drop(columns=[
        'new_deaths_smoothed', 
        # 'total_cases_per_million','new_cases_per_million', 
        'new_cases_smoothed_per_million',
    #    'total_deaths_per_million', 'new_deaths_per_million',
       'new_deaths_smoothed_per_million', 'reproduction_rate', 'icu_patients',
       'icu_patients_per_million', 'hosp_patients',
       'hosp_patients_per_million', 'weekly_icu_admissions',
       'weekly_icu_admissions_per_million', 'weekly_hosp_admissions',
       'weekly_hosp_admissions_per_million', 'new_tests', 'total_tests',
       'total_tests_per_thousand', 'new_tests_per_thousand',
       'new_tests_smoothed', 'new_tests_smoothed_per_thousand',
       'positive_rate', 'tests_per_case', 'tests_units',
       'people_vaccinated', 'people_fully_vaccinated', 'total_boosters',
       'new_vaccinations_smoothed',
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
    _format_date ='%d/%m/%Y'
    dates = [pd.to_datetime(_).date().strftime(_format_date) for _ in df['date'].unique()]
    min_value=df.iloc[0]['date'].strftime(_format_date)
    max_value=df.iloc[-1]['date'].strftime(_format_date)
    init_date, end_date = st.sidebar.select_slider("Selecione o período", options=dates, value=(min_value, max_value))
    return df[(df['date'] >= pd.to_datetime(init_date, format=_format_date)) & (df['date'] <= pd.to_datetime(end_date, format=_format_date))]

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
    # get totals in three variabless
    cases, deaths, vaccines = get_totals(df, date)
    # get news in three variables
    new_cases, new_deaths, new_vaccines = get_new(df, date)
    # get news of yeaterday from last date from df
    yesterday_cases, yesterday_deaths, yesterday_vaccines = get_new(df, date - datetime.timedelta(days=1))
    st.title(f'Consolidado')
    c_new_cases, c_new_deaths, c_new_vaccines = st.columns(3)
    st.markdown("""---""")
    c_total_cases, c_total_deaths, c_total_vaccines = st.columns(3)
    c_total_cases.metric("Total de casos", f'{int(cases):,d}'.replace(',','.'), '')
    c_total_deaths.metric("Total de mortos", f'{int(deaths):,d}'.replace(',','.'), '')
    _perc_new_cases = round(((new_cases / yesterday_cases) - 1) * 100 if yesterday_cases > 0 else new_cases * 100) 
    c_new_cases.metric('Novos casos', f'{int(new_cases):,d}'.replace(',','.'),f'{_perc_new_cases}%')
    _perc_new_deaths = round(((new_deaths / yesterday_deaths) - 1) * 100 if yesterday_deaths > 0 else new_deaths * 100)
    c_new_deaths.metric('Novas mortes', f'{int(new_deaths):,d}'.replace(',','.'),f'{_perc_new_deaths}%')
    _perc_new_vaccines = round(((new_vaccines / yesterday_vaccines) - 1) * 100 if yesterday_vaccines > 0 else new_vaccines * 100)
    c_new_vaccines.metric('Novas vacinas', f'{int(new_vaccines):,d}'.replace(',','.'),f'{_perc_new_vaccines}%')
    c_total_vaccines.metric('Total vacinas', f'{int(vaccines):,d}'.replace(',','.'),f'')

    head_countries_total_deaths = df.groupby(['country_pt'], as_index=False)['new_deaths'].sum().sort_values(by=['new_deaths'], ascending=False).head(20)
    head_countries_total_deaths['new_deaths'] = head_countries_total_deaths['new_deaths'].fillna(0.0).astype(int)
    head_countries_total_deaths.rename({'country_pt': 'Pais', 'new_deaths': 'Total mortes'}, axis=1, inplace=True)
    head_countries_total_deaths.reset_index(drop=True, inplace=True)

    head_countries_new_deaths = df[df['date'] == date][['country_pt', 'new_deaths']].sort_values(by=['new_deaths'], ascending=False).head(20)
    head_countries_new_deaths['new_deaths'] = head_countries_new_deaths['new_deaths'].fillna(0.0).astype(int)
    head_countries_new_deaths.rename({'country_pt': 'Pais', 'new_deaths': 'Total mortes'}, axis=1, inplace=True)
    head_countries_new_deaths.reset_index(drop=True, inplace=True)
    
    head_countries_total_cases = df.groupby(['country_pt'], as_index=False)['new_cases'].sum().sort_values(by=['new_cases'], ascending=False).head(20)
    head_countries_total_cases['new_cases'] = head_countries_total_cases['new_cases'].fillna(0.0).astype(int)
    head_countries_total_cases.rename({'country_pt': 'Pais', 'new_cases': 'Total de casos'}, axis=1, inplace=True)
    head_countries_total_cases.reset_index(drop=True, inplace=True)
    
    head_countries_new_cases = df[df['date'] == date][['country_pt', 'new_cases']].sort_values(by=['new_cases'], ascending=False).head(20)
    head_countries_new_cases['new_cases'] = head_countries_new_cases['new_cases'].fillna(0.0).astype(int)
    head_countries_new_cases.rename({'country_pt': 'Pais', 'new_cases': 'Novos casos'}, axis=1, inplace=True)
    head_countries_new_cases.reset_index(drop=True, inplace=True)
    
    head_deaths_total_table, head_new_deaths_table = st.columns(2)

    head_cases_total_table, head_cases_new_table = st.columns(2)

    head_deaths_total_table.write('Paises com maior número total de mortos')
    head_deaths_total_table.table(head_countries_total_deaths)

    head_new_deaths_table.write(f'Paises com o maior número de mortes em {date.strftime("%d/%m/%Y")}')
    head_new_deaths_table.table(head_countries_new_deaths)

    head_cases_total_table.write('Paises com o maior número de casos')
    head_cases_total_table.table(head_countries_total_cases)

    head_cases_new_table.write(f'Paises com o maiaor número de casos em {date.strftime("%d/%m/%Y")}')
    head_cases_new_table.table(head_countries_new_cases)
def populate_diary_evolution(df : pd.DataFrame):
    st.title(f'Evolução diária')
    days_for_mean = st.radio(
            "Informe a quantidade de dias para a média móvel",
            (7,14,28),
            help='Selecione um valor que apresentará a média móvel, por padrão é 7, mas pode ser 14 ou 28'
        )
    st.write('<style>div.row-widget.stRadio > div{flex-direction:row;justify-content: center;} </style>', unsafe_allow_html=True)
    if isinstance(days_for_mean, int):
        try:
            mean = int(days_for_mean)
        except Exception as e:
            mean = 7
    
    st.markdown("""---""")
    st.header('Evolução de mortes por dia')
    st.plotly_chart(graph_deaths(df, days_for_mean), use_container_width=True)
    
    
    st.markdown("""---""")
    st.header('Evolução de casos por dia')
    st.plotly_chart(graph_cases(df, days_for_mean), use_container_width=True)

    st.markdown("""---""")
    st.header('Evolução de vacinas por dia')
    st.plotly_chart(graph_vaccines(df, days_for_mean), use_container_width=True)

    

def graph_deaths(df: pd.DataFrame, days_for_mean: int):
    deaths_df = df.groupby(["date"], as_index=False)['new_deaths'].sum()
    deaths_df.set_index('date', inplace=True)
    deaths_df.rename({'new_deaths':'Mortes'}, axis=1, inplace=True)
    deaths_df['media'] = deaths_df.rolling(days_for_mean, min_periods=1).mean().round(0)
    fig_deaths = px.line(
        x=deaths_df.index, 
        y=deaths_df[f'media'], 
        color=px.Constant(f'{days_for_mean} dias'), 
        labels=dict(y='Média de Mortes', x='Dia', color='Média')
        )
    fig_deaths.add_bar(
        x=deaths_df.index,
        y=deaths_df['Mortes'],
        name='Mortes dia'
    )
    
    fig_deaths.update_layout(autosize=True, legend=dict(orientation='h'))
    return fig_deaths

def graph_cases(df: pd.DataFrame, days_for_mean: int):
    cases_df = df.groupby(["date"], as_index=False)['new_cases'].sum()
    cases_df.set_index('date', inplace=True)
    cases_df.rename({'new_cases':'Casos'}, axis=1, inplace=True)
    cases_df['media'] = cases_df.rolling(days_for_mean, min_periods=1).mean().round(0)
    fig_cases = px.line(
        x=cases_df.index, 
        y=cases_df[f'media'], 
        color=px.Constant(f'{days_for_mean} dias'), 
        labels=dict(y='Total de Casos', x='Dia', color='Média')
        )
    fig_cases.add_bar(
        x=cases_df.index,
        y=cases_df['Casos'],
        name='Casos dia'
    )
    fig_cases.update_layout(autosize=True, legend=dict(orientation='h'))
    return fig_cases
def graph_vaccines(df: pd.DataFrame, days_for_mean):
    vaccines_df = df.groupby(["date"], as_index=False)['new_vaccinations'].sum()
    vaccines_df.set_index('date', inplace=True)
    vaccines_df.rename({'new_vaccinations':'Vacinas'}, axis=1, inplace=True)
    vaccines_df['media'] = vaccines_df.rolling(days_for_mean, min_periods=1).mean().round(0)
    fig_deaths = px.line(
        x=vaccines_df.index, 
        y=vaccines_df[f'media'], 
        color=px.Constant(f'{days_for_mean} dias'), 
        labels=dict(y='Média de Vacinas', x='Dia', color='Média')
        )
    fig_deaths.add_bar(
        x=vaccines_df.index,
        y=vaccines_df['Vacinas'],
        name='Vacinas dia'
    )
    
    fig_deaths.update_layout(autosize=True, legend=dict(orientation='h'))
    return fig_deaths

def get_totals(df : pd.DataFrame, date):
    df = df.sort_values(by='date', ascending=False)
    total_deaths = df[df['date'] == date]['total_deaths'].sum()
    total_cases = df[df['date'] == date]['total_cases'].sum()
    total_vaccines = df[df['date'] == date]['total_vaccinations'].sum()
    return [total_cases, total_deaths, total_vaccines]

def get_new(df : pd.DataFrame, date):
    df = df.sort_values(by='date', ascending=False)
    new_deaths = df[df['date'] == date]['new_deaths'].sum()
    new_cases = df[df['date'] == date]['new_cases'].sum()
    new_vaccines = df[df['date'] == date]['new_vaccinations'].sum()
    return [new_cases, new_deaths, new_vaccines]

def analysis_by_country(df : pd.DataFrame, date):
    df = df.sort_values(by='date', ascending=True)
    st.title('Análise dos países')
    st.markdown('----')
    col1, col2 = st.columns(2)
    df = df[df['date'] == date]
    col1.write('Novos casos por milhão')
    col1.table(convert_df_country(df, 'new_cases_per_million', 'Novos casos').head(20))
    col2.write('Novas mortes por milhão')
    col2.table(convert_df_country(df, 'new_deaths_per_million', 'Novas mortes') .head(20))

def convert_df_country(df: pd.DataFrame, old_column: str, new_columns: str):
    df = df[['location', old_column]].sort_values(by=old_column, ascending=False)
    df.reset_index(drop=True, inplace=True)
    df[old_column] = df[old_column].fillna(0.0).astype(int)
    df.rename({'localtion':'País', old_column: new_columns}, axis=1, inplace=True)
    return df

