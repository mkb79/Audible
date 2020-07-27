import configparser
import io
import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional

import audible
import httpx
from audible.auth import LoginAuthenticator
from audible.cli.console import bold, nocolor, color_terminal
from audible.cli import options
from audible.cli.utils import do_prompt, is_path, choice, boolean, allow_empty
from PIL import Image


DEFAULT_CONF_DIR = os.environ.get("AUDIBLE_CONF_DIR", None)
CONFIG_FILE = "audible.ini"
DEFAULT_AUTH_FILE_EXTENSION = "json"


def prompt_captcha_callback(captcha_url: str) -> str:
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
        print()
        print(captcha_url)
        print()

    guess = do_prompt("Answer for CAPTCHA")
    return str(guess).strip().lower()


def prompt_otp_callback() -> str:
    """Helper function for handling 2-factor authentication."""
    print()
    print("2FA is activated for this account.")
    guess = do_prompt("Please enter OTP Code")
    return str(guess).strip().lower()


def save_config(config: configparser.ConfigParser, path: Path):
    config.write((path / CONFIG_FILE).open("w"))


def ask_user(d: dict):
    welcome_message = (f"Welcome to the audible {audible.__version__} "
                       f"quickstart utility.")

    print(bold(welcome_message))
    print(bold(len(welcome_message)*"="))

    print()
    print("Please enter values for the following settings (just press Enter\n"
          "to accept a default value, if one is given in brackets).")

    if d.get("path", None) is None:
        print()
        print("Enter the config dir for audible.")
        d["path"] = do_prompt("Config dir", ".", is_path)

    path = d["path"]
    while (Path(path) / CONFIG_FILE).exists():
        print()
        print(bold(
            f"Error: an existing {CONFIG_FILE} has been found in the "
            f"config dir."))
        print("audible quickstart will not overwrite existing config files.")
        print()
        path = do_prompt(
            "Please enter a new config dir (or just Enter to exit)",
            "",
            is_path)
        if not path:
            sys.exit(1)

    print()
    print(bold("Selected config dir:"))
    print(f"{Path(path).absolute()}")

    print()
    print(bold(
        "A country code can now set as default. This country code is used,\n"
        "if no other is provided."))

    print()
    d["default_country_code"] = do_prompt(
        "Which country country code should be set as default",
        None,
        choice("us", "ca", "uk", "au", "fr", "de", "jp", "it", "in")
    )

    print()
    print(bold(
        "Audible quickstart will now create a profile. This profile is\n"
        "choosen as default, if no other one is selected.\n"
        "A auth file must assigned to every profile. This file contains\n"
        "credentials and other data for a specific audible user. It will be\n"
        "stored in the config dir. A auth file can be shared between multiple\n"
        "profiles. Simple enter the same file name for the corresponding profiles."
        "\n\n"
        "If the auth file don't exists, a new one will created. To retrieve the\n"
        "necessary auth data, credentials for the audible account which you want\n"
        "to use must be provided.\n"
        "Audible quickstart login to the audible account and register a new\n"
        "audible device. The password will not be stored.\n"
        "To protect the auth data, the file can be encrypted optionally.\n"
        "More accounts/profiles can be added to this project later.\n"))

    d["profile_name"] = do_prompt(
        "Please enter a name for your primary profile",
        "audible")

    print()
    auth_file = do_prompt(
        "Please enter a name for the auth file",
        d["profile_name"] + f".{DEFAULT_AUTH_FILE_EXTENSION}")

    use_existing_file = False
    while (Path(path) / auth_file).exists():
        print()
        print(bold("The auth file exists already in config dir."))
        print()

        use_existing_file = do_prompt(
            "Should this file be used for the new profile",
            "N",
            boolean)

        if use_existing_file:
            break

        print()
        auth_file = do_prompt(
            "Please enter a new name for the auth file (or just Enter to exit)",
            "",
            allow_empty)
        if not auth_file:
            sys.exit(1)

    d["use_existing_file"] = use_existing_file
    d["profile_auth_file"] = auth_file

    if not use_existing_file:
        print()    
        encrypt_file = do_prompt(
            "Do you want to encrypt the auth file?",
            "N",
            boolean)
    
        if encrypt_file:
            print()
            d["profile_auth_file_password"] = do_prompt(
                "Please enter a password for the auth file")        
            d["profile_auth_file_encryption"] = "json"
    
    
        print()
        d["profile_username"] = do_prompt("Please enter your amazon username")
        d["profile_password"] = do_prompt("Please enter your amazon password",
                                          use_getpass=True)

    print()
    profile_country_code = do_prompt(
        "Please enter the country code for the primary profile",
        "default",
        choice("us", "ca", "uk", "au", "fr", "de", "jp", "it", "in", "default")
    )
    if profile_country_code != "default":
        d["profile_country_code"] = profile_country_code

    return d


def add_to_parser(parser):
    default_options = [options.config_dir(default=DEFAULT_CONF_DIR)]
    command_parser = parser.add_parser(
        "quickstart",
        help="audible quickstart setup",
        parents=default_options)
    command_parser.set_defaults(func=main)


def main(args):
    if not isinstance(args, dict):
        args = vars(args)
    d = ask_user(args)

    profile_name = d.get("profile_name")
    profile_auth_file = d.get("profile_auth_file")
    profile_country_code = d.get("profile_country_code", None)

    config = configparser.ConfigParser()
    config.set(
        config.default_section,
        "default_country_code",
        d.get("default_country_code"))
    config.set(config.default_section, "default_profile", profile_name)

    config.add_section(profile_name)
    config.set(profile_name, "auth_file", profile_auth_file)
    if profile_country_code:
        config.set(profile_name, "country_code", profile_country_code)

    path = Path(d.get("path"))
    file_options = {"filename": Path(path) / profile_auth_file}
    if "profile_auth_file_encryption" in d:
        file_options["password"] = d.get("profile_auth_file_password")
        file_options["encryption"] = d.get("profile_auth_file_encryption")

    if not d.get("use_existing_file"):
        print()
        print(bold("Now login with amazon to your audible account."))

        auth = LoginAuthenticator(
            username=d.get("profile_username"),
            password=d.get("profile_password"),
            locale=config.get(profile_name, "country_code"),
            captcha_callback=prompt_captcha_callback,
            otp_callback=prompt_otp_callback)

        print()
        print(bold("Login was successful. Now registering a new device."))

        auth.register_device()
        device_name = auth.device_info["device_name"]
        print()
        print(bold(f"Successfully registered {device_name}."))
        
        auth.to_file(**file_options)

    save_config(config, path)

    print()
    print(bold("Finished: An initial directory structure has been created."))
    print("The project dir can be found here:")
    print(f"{path.absolute()}")
