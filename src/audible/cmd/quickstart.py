import configparser
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


CONFIG_FILE = "audible.ini"

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
        path = do_prompt("Project path for audible", ".", is_path)

    while (Path(path) / CONFIG_FILE).exists():
        print()
        print(bold(f"Error: an existing {CONFIG_FILE} has been found in the "
                   "selected project path."))
        print("audible-quickstart will not overwrite existing audible projects.")
        print()
        path = do_prompt(
            "Please enter a new project path (or just Enter to exit)",
            "",
            is_path)
        if not path:
            sys.exit(1)

    print()
    country_code = do_prompt(
        "Please enter the country code of your main audible marketplace",
        None,
        choice("us", "ca", "uk", "au", "fr", "de", "jp", "it", "in")
    )

    config = configparser.ConfigParser(defaults={"country_code": country_code})

    print()
    print(bold("Now audible quickstart will setup a main profile. Therefore a "
               "login to your audible account is required. After login, a new "
               "audible device will be registered. More audible accounts can "
               "be added with another profile to this project later."))

    print()
    main_profile = do_prompt(
        "Please enter a name for your main profile"
        "audible")
    config.add_section(main_profile)

    print()
    print("Authentication and registration data for your profile will "
          "be stored in a auth file.")

    print()
    auth_file = do_prompt(
        "Please enter a name for the file",
        f"{main_profile}.auth")
    while (Path(path) / auth_file).exists():
        print()
        print(bold(f"Error: an existing {auth_file} has been found in the "
                   "selected project path."))
        print("audible-quickstart will not overwrite existing files.")
        print()
        auth_file = do_prompt(
            "Please enter a new name for the auth file (or just Enter to exit)",
            "")
        if not path:
            sys.exit(1)

    config.set(main_profile, "auth_file", auth_file)

    file_options = {"filename": Path(path) / auth_file}

    print()    
    encryption = do_prompt(
        "Do you want to encrypt the auth file?",
        "N",
        boolean)

    if encryption:
        print()
        file_options["password"] = do_prompt(
            "Please enter a password for the auth file")        
        file_options["encryption"] = "json"


    print()
    username = do_prompt("Please enter your amazon username")
    password = do_prompt("Please enter your amazon password")

    print()
    country_code_main = do_prompt(
        "Please enter the country code for this profile",
        country_code,
        choice("us", "ca", "uk", "au", "fr", "de", "jp", "it", "in")
    )

    if country_code != country_code_main:
        config.set(main_profile, "country_code", country_code_main)

    print()
    print(bold("Now login with amazon to your audible account."))

    auth = LoginAuthenticator(
        username=username,
        password=password,
        locale=country_code_main,
        captcha_callback=cmd_captcha_callback,
        otp_callback=cmd_otp_callback)

    print()
    print(bold("Login was successful. Now registering a new device."))

    auth.register_device()
    device_name = auth.device_info["device_name"]
    print()
    print(bold(f"Successfully registered {device_name}."))
        
    auth.to_file(**file_options)
    config.write((Path(path) / CONFIG_FILE).open("w"))

    print()
    print(bold("Finished: An initial directory structure has been created."))
    print(f"The project dir can be found here {Path(path).absolute()}.")


def main(argv=sys.argv[1:]):
    if not color_terminal():
        nocolor()

    parser = get_parser(prog="audible-quickstart")
    args = parser.parse_args(argv)
    quickstart(args.path)
