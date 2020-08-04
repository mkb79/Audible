import click
from click import echo
from tabulate import tabulate

from . import options


SUB_COMMAND_NAME = "profile"


def list_profiles(config):
    head = ["Profile", "auth file", "cc"]
    data = []
    profiles = config.sections()
    for profile in profiles:
        auth_file = config.get(profile, "auth_file")
        is_primary = config.has_option(profile, "primary")
        country_code = config.get(profile, "country_code")
        profile_name = "*" + profile if is_primary else profile
        data.append([profile_name, auth_file, country_code])
    table = tabulate(data, head, showindex=True, tablefmt="pretty",
                     colalign=("center", "left", "left", "center")
    )
    echo(table)


@click.group()
def cli():
    """manage profiles"""


@cli.command()
@options.config_option
@options.pass_config
def list(config):
    """list profiles in config file"""
    list_profiles(config.parser)
