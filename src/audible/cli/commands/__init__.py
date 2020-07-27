from . import quickstart, config


def add_commands(parser):
    commands = [quickstart, config]

    for command in commands:
        command.add_to_parser(parser)
