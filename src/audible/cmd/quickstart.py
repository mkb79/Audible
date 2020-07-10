import io
import sys
from argparse import ArgumentParser
from pathlib import Path

import audible
import httpx
from audible.auth import LoginAuthenticator
from audible.cmd.console import bold, nocolor, color_terminal
from audible.cmd.utils import do_prompt, is_path, choice, boolean
from PIL import Image


def cmd_captcha_callback(captcha_url: str) -> str:
    """Helper function for handling captcha."""
    print()
    open_captcha = do_prompt(
        "Captcha found. Open Captcha with default image viewer",
        "Y",
        boolean)

    if open_captcha:
        captcha = httpx.get(captcha_url).content
        f = io.BytesIO(captcha)
        img = Image.open(f)
        img.show()
    else:
        print("Please open the following url with a webbrowser to get the captcha:")
        print(f"\n{captcha_url}\n")

    guess = do_prompt("Answer for CAPTCHA")
    return str(guess).strip().lower()


def cmd_otp_callback() -> str:
    """Helper function for handling 2-factor authentication."""
    print()
    print("2FA is activated for this account.")
    guess = do_prompt("Please enter OTP Code")
    return str(guess).strip().lower()


def get_parser(prog):
    parser = ArgumentParser(prog)
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s " + audible.__version__)

    parser.add_argument(
        "path",
        metavar="PROJECT_DIR",
        help="project root",
        default=".",
        nargs="?")

    return parser


def quickstart(path):
    welcome_message = f"Welcome to the audible {audible.__version__} quickstart utility."
    len_message = len(welcome_message)
    print(bold(welcome_message))
    print(bold(len_message*"="))
    print()
    print("Please enter values for the following settings (just press Enter\n"
          "to accept a default value, if one is given in brackets).")

    if path:
        print()
        print(bold(f"Selected project path: {Path(path).absolute()}"))
    else:
        print()
        print("Enter the project path for audible.")
        path = do_prompt("Project path for the documentation", ".", is_path)

    while (Path(path) / "auth.json").is_file():
        print()
        print(bold("Error: an existing auth.json has been found in the "
                   "selected project path."))
        print("audible-quickstart will not overwrite existing audible projects.")
        print()
        path = do_prompt(
            "Please enter a new project path (or just Enter to exit)",
            "",
            is_path)
        if not path:
            sys.exit(1)

    file_options = {"filename": Path(path) / "auth.json"}

    print()
    print(bold("Working with the audible package requires a authentication to "
               "amazon and for best user experience a device registration."))
    username = do_prompt("Please enter your amazon username")
    password = do_prompt("Please enter your amazon password")

    print()
    country_code = do_prompt(
        "Please enter the country code of your main audible marketplace",
        None,
        choice("us", "ca", "uk", "au", "fr", "de", "jp", "it", "in")
    )

    print()
    register = do_prompt(
       "Do you want to register a new device (recommended)?",
       "Y",
       boolean)

    print()
    print(bold("The authentication and registration response will be saved "
               "to auth.json"))
    encryption = do_prompt(
        "Do you want to encrypt the auth.json file?",
        "N",
        boolean)

    if encryption:
        print()
        file_options["password"] = do_prompt(
            "Please enter a password for the config file")        
        file_options["encryption"] = "json"

    print()
    print(bold("Now login with amazon to your audible account."))

    auth = LoginAuthenticator(
        username=username,
        password=password,
        locale=country_code,
        captcha_callback=cmd_captcha_callback,
        otp_callback=cmd_otp_callback)

    print()
    print(bold("Login was successful."))

    if register:
        auth.register_device()
        device_name = auth.device_info["device_name"]
        print()
        print(bold(f"Successfully registered {device_name}."))
        
    auth.to_file(**file_options)

    print()
    print(bold("Finished: An initial directory structure has been created."))
    print(f"The project dir can be found here {Path(path).absolute()}.")


def main(argv=sys.argv[1:]):
    if not color_terminal():
        nocolor()

    parser = get_parser(prog="audible-quickstart")
    args = parser.parse_args(argv)
    quickstart(args.path)
