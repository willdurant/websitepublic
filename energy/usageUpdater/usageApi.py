from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import requests
import pandas as pd
import polars as pl
from energy.models import Energy

load_dotenv()

# Get environment variables
API_KEY = os.getenv("API_KEY")
ACCOUNT_NUMBER = os.getenv("ACCOUNT_NUMBER")
ELEC_MPAN = os.getenv("ELEC_MPAN")
ELEC_SN = os.getenv("ELEC_SN")
GAS_MPRN = os.getenv("GAS_MPRN")
GAS_SN = os.getenv("GAS_SN")

electricity_url = (
    "https://api.octopus.energy/v1/electricity-meter-points/"
    + ELEC_MPAN
    + "/meters/"
    + ELEC_SN
    + "/consumption/"
)

gas_url = (
    "https://api.octopus.energy/v1/gas-meter-points/"
    + GAS_MPRN
    + "/meters/"
    + GAS_SN
    + "/consumption/"
)

tarriff_url = "https://api.octopus.energy/v1/products/VAR-22-04-02"
URLS = {"ELEC": electricity_url, "GAS": gas_url, "TARRIFF": tarriff_url}
headers = {"Content-type": "application/json", "$API_KEY": API_KEY}


def make_request(energy_type: str) -> requests.Response:
    period_from = datetime(2022, 9, 1)
    period_to = datetime.today().date() - timedelta(days=1)
    response = requests.get(
        url=URLS[energy_type],
        auth=(API_KEY, ""),
        params={
            "period_from": str(period_from),
            "period_to": str(period_to),
            "page_size": 25000,
        },
    )
    return response


# Get the right types for dates and times, set column for type of energy
def standardise_data(df: pd.DataFrame, energy_type: str) -> pl.DataFrame:
    data = (
        pl.DataFrame(df)
        .with_columns(
            pl.col("interval_start")
            .str.strptime(pl.Datetime, fmt="%+", utc=True)
            .dt.convert_time_zone(time_zone="Europe/London")
            .alias("interval_start")
        )
        .with_columns(
            pl.col("interval_end")
            .str.strptime(pl.Datetime, fmt="%+", utc=True)
            .dt.convert_time_zone(time_zone="Europe/London")
            .alias("interval_end")
        )
        .with_columns(pl.lit(energy_type).alias("energy_type"))
    )
    return data


# Calculate the cost of the energy usage
def calculate_cost(df: pl.DataFrame, energy_type: str) -> pl.DataFrame:
    if energy_type == "ELEC":
        data = df.with_columns((pl.col("consumption") * 65.23).alias("cost"))
        return data
    data = df.with_columns(
        ((pl.col("consumption") * 1.02264 * 39) / 3.6).alias("consumption")
    ).with_columns((pl.col("consumption") * 16.24).alias("cost"))
    return data


def process_data(response: requests.Response, energy_type: str) -> pl.DataFrame:
    df = pd.DataFrame(response.json()["results"])
    df = standardise_data(df, energy_type)
    df = calculate_cost(df, energy_type)
    return df


def create_objects(response: requests.Response, energy_type: str):
    data = process_data(response, energy_type)

    for row in data.iter_rows(named=True):
        Energy.objects.get_or_create(
            date=row["interval_start"].date(),
            energy_type=row["energy_type"],
            interval_start=row["interval_start"],
            interval_end=row["interval_end"],
            consumption=row["consumption"],
            cost=row["cost"],
        )


def import_new_energy_data():
    e_types = [n[0] for n in Energy.ENERGY_TYPE_CHOICES]
    for energy_type in e_types:
        response = make_request(energy_type)
        if response:
            try:
                create_objects(response, energy_type)
            except:
                pass
