import json
import os
from datetime import date
from typing import TYPE_CHECKING

import pandas as pd

import audible


if TYPE_CHECKING:
    from statsmodels.tsa.seasonal import DecomposeResult


def main():
    country_code = "uk"
    filename = "./audible_credentials.txt"
    encryption = False
    if os.path.exists(filename):
        auth = audible.Authenticator.from_file(filename)
    else:
        auth = audible.Authenticator.from_login_external(locale=country_code)
        auth.to_file(filename, encryption=False)
        if encryption == "json":
            password = "sample_pass"  # noqa: S105
            auth.to_file(filename + ".json", password, encryption="json")

    # with audible.Client(auth=auth) as client:
    #     library = client.get(
    #         "1.0/library",
    #         num_results=1000,
    #         response_groups="product_desc, product_attrs",
    #         sort_by="-PurchaseDate"
    #     )
    #     books = library["items"]
    #     book = books[0]
    #     print(f'keys:{book.keys()}')
    #     for i,book in enumerate(books):
    #         print(f'#{i} Title: {book.get("title")} - time:{book.get("runtime_length_min")}')

    # get stats example
    # with audible.Client(auth=auth) as client:
    #     stats = client.get(
    #         "1.0/stats/aggregates",
    #         monthly_listening_interval_duration="3", #number of months to aggragate for
    #         monthly_listening_interval_start_date="2021-03", #start month for aggragation
    #         store="Audible"

    #     )
    #     print(stats)

    with audible.Client(auth=auth) as client:
        year_aggregate = get_reading_time_since_signup(client)

    print(year_aggregate)
    with open("stats.json", "w") as write_file:
        json.dump(year_aggregate, write_file, indent=4)


def authenticate(username, password, country_code):
    auth = audible.Authenticator.from_login(
        username, password, locale=country_code, with_username=False
    )
    return auth


def get_reading_time_since_signup(client):
    signup_year = get_signup_year(client)
    current_year = date.today().year
    year_aggregate = {}
    for i in range(current_year - signup_year + 1):
        target_year = signup_year + i
        target_month = "01"
        print(target_year)
        stats = client.get(
            "1.0/stats/aggregates",
            monthly_listening_interval_duration="12",  # number of months to aggragate for
            monthly_listening_interval_start_date=f"{target_year}-{target_month}",  # start month for aggragation
            store="Audible",
        )
        # iterate over each month
        for stat in stats["aggregated_monthly_listening_stats"]:
            year_aggregate[stat.get("interval_identifier")] = (
                convert_miliseconds_to_hours_minutes_seconds(stat["aggregated_sum"])
            )
    return year_aggregate


def get_signup_year(client):
    # TODO
    return 2013


def convert_miliseconds_to_hours_minutes_seconds(milliseconds):
    seconds = (int)(milliseconds / 1000) % 60
    minutes = (int)((milliseconds / (1000 * 60)) % 60)
    hours = (int)((milliseconds / (1000 * 60 * 60)) % 24)
    return hours, minutes, seconds


def export_to_csv(file_name):
    import pandas as pd

    df = pd.read_json(file_name)  # e.g. stats.json
    df = df.transpose()
    df.columns = ["hours", "minutes", "seconds"]
    file_name_csv = file_name.split(".")[0] + ".csv"
    df.to_csv(file_name_csv, index=None)


def analyse_stats(file_name="stats.json"):
    """file_name: json dump of return value of get_reading_time_since_signup."""
    import statsmodels

    df = pd.read_json(file_name)  # e.g. stats.json
    df = df.transpose()
    df.columns = ["hours", "minutes", "seconds"]
    file_name.split(".")[0] + ".csv"
    df["hours"].plot.line(figsize=(20, 8))
    df["hours"].plot.bar(figsize=(20, 8))

    sd = statsmodels.tsa.api.seasonal_decompose(df["hours"], period=12)
    combine_seasonal_cols(sd, "stats_analysis.csv")  # custom helper function
    # TODO visualise per month, per quarter, per year seasonality in python
    # for now further processing can be done in excell


def combine_seasonal_cols(
    seasonal_model_results: "DecomposeResult", csv_file: str = ""
) -> pd.DataFrame:
    """Adds new seasonal cols to a df given seasonal results.

    See
    https://www.statsmodels.org/dev/generated/statsmodels.tsa.seasonal.seasonal_decompose.html.

    Args:
        seasonal_model_results: (statsmodels DecomposeResult object)
        csv_file: csv file to save to.

    Returns:
        The modified data frame.
    """
    # Add results to original df
    modified_df = pd.DataFrame()

    modified_df["observed"] = seasonal_model_results.observed
    modified_df["residual"] = seasonal_model_results.resid
    modified_df["seasonal"] = seasonal_model_results.seasonal
    modified_df["trend"] = seasonal_model_results.trend
    if csv_file:
        modified_df.to_csv(csv_file)
    return modified_df


main()
