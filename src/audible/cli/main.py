import sys
from argparse import ArgumentParser

import audible
from audible.cli.console import nocolor, color_terminal
from audible.cli.commands import add_commands 


COMMAND_NAME = "audible"


def get_parser(prog):
    parser = ArgumentParser(prog)
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s " + audible.__version__)

    command_parsers = parser.add_subparsers(metavar="command", dest="command")
    command_parsers.required = True

    # add commands
    add_commands(command_parsers)

    return parser


def main(args=None):
    if not color_terminal():
        nocolor()

    if args is None:
        args = sys.argv[1:]

    parser = get_parser(prog=COMMAND_NAME)
    parsed_args = parser.parse_args(args)
    parsed_args.func(parsed_args)
