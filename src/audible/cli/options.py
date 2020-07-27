import os
from functools import partial

from argparse import ArgumentParser


def create_option(*args, **kwargs):
    option = ArgumentParser(add_help=False)
    option.add_argument(*args, **kwargs)
    return option


config_dir = partial(
    create_option,
    "path",
    metavar="CONFIG_DIR",
    help="config dir",
    default=".",
    nargs="?")

profile = partial(
    create_option,
    "--profile",
    help="name of the profile")

profile_password = partial(
    create_option,
    "--password",
    "-p",
    help="password for the auth file")


DEFAULT_CONF_DIR = os.environ.get("AUDIBLE_CONF_DIR", ".")
