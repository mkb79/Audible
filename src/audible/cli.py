import importlib

import audible
from audible.commands import AVAILABLE_COMMANDS, options
import click


class CliCommands(click.Group):
    def list_commands(self, ctx):
        return AVAILABLE_COMMANDS

    def get_command(self, ctx, name):
        try:
            mod = importlib.import_module(f"audible.commands.cmd_{name}")
        except ImportError:
            click.secho(
                f"Something went wrong during setup command: {name}\n",
                fg="red",
                bold=True)
            return
        return mod.cli


@click.group(cls=CliCommands)
@click.version_option(audible.__version__)
@options.debug_option
def main(debug):
    pass
