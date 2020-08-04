import configparser
import os
import pathlib

import click


APP_NAME = "Audible"
CONFIG_FILE = "config.ini"
CONFIG_ENV_DIR = "AUDIBLE_CONFIG_DIR"
DEFAULT_AUTH_FILE_EXTENSION = "json"


def get_config_dir_path(ignore_env=False) -> pathlib.Path:
    env_dir = os.getenv(CONFIG_ENV_DIR)
    if env_dir and not ignore_env:
        return pathlib.Path(env_dir).absolute()

    return pathlib.Path(
        click.get_app_dir(
            APP_NAME,
            roaming=False,
            force_posix=True))


def get_config_file_path(ignore_env=False) -> pathlib.Path:
    return (get_config_dir_path(ignore_env) / CONFIG_FILE).absolute()


class Config:
    """This class holds the config."""

    def __init__(self):
        self.filename = None
        self.parser = configparser.RawConfigParser(allow_no_value=True)

    def update_profile(self, profile, data: dict):
        self.parser.read_dict({profile: data})

    @property
    def primary_profile(self):
        primary = []
        for section in self.parser.sections():
            if self.parser.has_option(section, "primary"):
                primary.append(section)

        if len(primary) != 1:
            return None
        return primary[0]

    def read_config(self, filename):
        path_file = pathlib.Path(filename)

        result = self.parser.read([filename])
        if filename not in result:
            click.secho(
                f"An error occured while loading config from {filename}",
                fg="red",
                bold=True)
            click.get_current_context().abort()

        self.filename = path_file

    def write_config(self, filename=None):
        path_file = pathlib.Path(filename or self.filename)

        path_file_dir = path_file.parent
        if not path_file_dir.is_dir():
            path_file_dir.mkdir()

        self.parser.write(path_file.open("w"))

    def get_dict(self):
        try:
            d = {}
            for section in self.parser.keys():
                d.update({section: dict(self.parser[section].items())})
            return d
        except Exception as e:
            click.secho(e, fg="red", bold=True)


pass_config = click.make_pass_decorator(Config, ensure=True)


def read_config(ctx, param, value):
    """Callback that is used whenever --config is passed.  We use this to
    always load the correct config.  This means that the config is loaded
    even if the group itself never executes so our config stay always
    available.
    """
    config = ctx.ensure_object(Config)

    path_file = pathlib.Path(value)
    if not path_file.is_file():
        if ctx.info_name == "quickstart":
            config.filename = path_file
            return value

        ctx.fail(f"Config file {value} not found.")
    
    config.read_config(value)
    return value


config_option = click.option(
    "--config",
    "-c",
    type=click.Path(exists=False, dir_okay=False),
    default=get_config_file_path(),
    show_default=True,
    callback=read_config,
    expose_value=False,
    help="The config file to use instead of the default.")


debug_option = click.option(
    "--debug",
    is_flag=True,
    help="Enables debug mode.")


profile_option = click.option(
    "--profile",
    help="The profile to use instead of the primary.")


auth_file_password = click.option(
    "--password",
    "-p",
    help="The password for the profile auth file.")
