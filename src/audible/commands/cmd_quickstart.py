import io
import sys

import audible
import click
import httpx
from click import echo, secho, prompt
from PIL import Image

from audible.auth import LoginAuthenticator
from . import options


SUB_COMMAND_NAME = "quickstart"


def prompt_captcha_callback(captcha_url: str) -> str:
    """Helper function for handling captcha."""

    echo("Captcha found")
    if click.confirm("Open Captcha with default image viewer", default="Y"):
        captcha = httpx.get(captcha_url).content
        f = io.BytesIO(captcha)
        img = Image.open(f)
        img.show()
    else:
        echo("Please open the following url with a webbrowser "
             "to get the captcha:")
        echo(captcha_url)

    guess = prompt("Answer for CAPTCHA")
    return str(guess).strip().lower()


def prompt_otp_callback() -> str:
    """Helper function for handling 2-factor authentication."""

    echo("2FA is activated for this account.")
    guess = prompt("Please enter OTP Code")
    return str(guess).strip().lower()


def ask_user(cfg_file):
    path = cfg_file.parent
    d = {}

    welcome_message = (f"Welcome to the audible {audible.__version__} "
                       f"quickstart utility.")

    secho(welcome_message, bold=True)
    secho(len(welcome_message)*"=", bold=True)

    echo()
    secho("Selected config dir:", bold=True)
    echo(path.absolute())

    echo()
    echo("Please enter values for the following settings (just press Enter "
         "to accept a default value, if one is given in brackets).")

    echo()
    secho("A country code can now set as default. This country code is used,"
          "if no other is provided.", bold=True)

    echo()
    d["default_country_code"] = prompt(
        "Which country country code should be set as default",
        type=click.Choice(("us", "ca", "uk", "au", "fr", "de", "jp", "it", "in")),
        show_choices=False
    )

    echo()
    secho(
        "Audible quickstart will now create a profile. This profile is "
        "choosen as default, if no other one is selected.\n"
        "A auth file must assigned to every profile. This file contains "
        "credentials and other data for a specific audible user. It will be "
        "stored in the config dir. A auth file can be shared between multiple "
        "profiles. Simple enter the same file name for the corresponding profiles."
        "\n\n"
        "If the auth file doesn't exists, a new one will created. To retrieve the "
        "necessary auth data, credentials for the audible account, which you "
        "want to use, must be provided.\n"
        "Audible quickstart login to the audible account and register a new "
        "audible device. The password will not be stored.\n"
        "To protect the auth data, the file can be encrypted optionally.\n"
        "More accounts/profiles can be added to the conf file later.\n",
        bold=True)

    profile_name = prompt(
        "Please enter a name for your primary profile",
        default="audible")
    d["profile_name"] = profile_name

    echo()
    auth_file = prompt(
        "Please enter a name for the auth file",
        default=profile_name + f".{options.DEFAULT_AUTH_FILE_EXTENSION}")

    use_existing_file = False
    while (path / auth_file).exists():
        echo()
        secho("The auth file already exists in config dir.", bold=True)
        echo()

        use_existing_file = click.confirm(
            "Should this file be used for the new profile",
            default="N")

        if use_existing_file:
            break

        echo()
        auth_file = prompt(
            "Please enter a new name for the auth file (or just Enter to exit)",
            default="")
        if not auth_file:
            sys.exit(1)

    d["use_existing_file"] = use_existing_file
    d["profile_auth_file"] = auth_file

    if not use_existing_file:
        echo()
        encrypt_file = click.confirm(
            "Do you want to encrypt the auth file?",
            default="N")
    
        if encrypt_file:
            echo()
            while True:
                file_password = prompt(
                    "Please enter a password for the auth file",
                    hide_input=True)
                confirm_password = prompt(
                    "Please retype password for the auth file to confirm",
                    hide_input=True)
                if file_password == confirm_password:
                    break

                secho("Passwords don't match. Please try again.")
                echo()
            d["profile_auth_file_password"] = file_password
            d["profile_auth_file_encryption"] = "json"
    
        echo()
        d["audible_username"] = prompt("Please enter your amazon username")
        d["audible_password"] = prompt("Please enter your amazon password",
                                       hide_input=True)

    echo()
    profile_country_code = prompt(
        "Please enter the country code for the primary profile",
        default="default",
        type=click.Choice(("us", "ca", "uk", "au", "fr", "de", "jp", "it", "in", "default"))
    )
    if profile_country_code != "default":
        d["profile_country_code"] = profile_country_code

    return d


@click.command()
@click.pass_context
@options.config_option
@options.pass_config
def cli(config, ctx):
    """Quicksetup audible"""
    cfg_file = config.filename
    cfg_path = cfg_file.parent
    cfg_parser = config.parser

    if cfg_file.exists():
        echo()
        secho(f"Error: an existing {cfg_file.name} has been found in the "
              f"config dir {cfg_path}.",
              bold=True)
        ctx.fail("audible quickstart will not overwrite existing config files.")

    d = ask_user(cfg_file)

    profile_name = d.get("profile_name")
    profile_auth_file = d.get("profile_auth_file")
    profile_country_code = d.get("profile_country_code", None)

    cfg_parser.set(
        cfg_parser.default_section,
        "country_code",
        d.get("default_country_code")
    )

    cfg_parser.add_section(profile_name)
    cfg_parser.set(profile_name, "primary", None)
    cfg_parser.set(profile_name, "auth_file", profile_auth_file)
    if profile_country_code:
        cfg_parser.set(profile_name, "country_code", profile_country_code)

    file_options = {"filename": cfg_path / profile_auth_file}
    if "profile_auth_file_encryption" in d:
        file_options["password"] = d.get("profile_auth_file_password")
        file_options["encryption"] = d.get("profile_auth_file_encryption")

    if not d.get("use_existing_file"):
        echo()
        secho("Now login with amazon to your audible account.", bold=True)

        auth = LoginAuthenticator(
            username=d.get("audible_username"),
            password=d.get("audible_password"),
            locale=cfg_parser.get(profile_name, "country_code"),
            captcha_callback=prompt_captcha_callback,
            otp_callback=prompt_otp_callback)

        echo()
        secho("Login was successful. Now registering a new device.", bold=True)

        auth.register_device()
        device_name = auth.device_info["device_name"]
        echo()
        secho(f"Successfully registered {device_name}.", bold=True)

    config.write_config()
    auth.to_file(**file_options)

    echo()
    secho("Finished: An initial directory structure has been created.", bold=True)
    echo("The project dir can be found here:")
    echo(cfg_path.absolute())
