import pathlib


def list_commands():
    cmd_folder = pathlib.Path(__file__).parent
    rv = []

    for filename in list(cmd_folder.glob("*.py")):
        if filename.stem.startswith("cmd_"):
            rv.append(filename.stem[4:])
    rv.sort()
    return rv


AVAILABLE_COMMANDS = list_commands()
