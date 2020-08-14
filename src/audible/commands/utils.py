import io
import pathlib
from difflib import SequenceMatcher
from typing import Optional, Union

import click
import httpx
import toml
from click import echo, secho, prompt
from PIL import Image

from ..auth import LoginAuthenticator


DEFAULT_AUTH_FILE_EXTENSION = "json"
DEFAULT_AUTH_FILE_ENCRYPTION = "json"


class Config:
    """This class holds the config and environment."""

    def __init__(self):
        self.filename: pathlib.Path = None
        self._config_data = {
            "APP": {},
            "profile": {}
        }
        self._params = {}

        if "title" not in self.data:
            self.data["title"] = "Audible Config File"

    @property
    def data(self):
        return self._config_data

    @property
    def params(self):
        return self._params

    def file_exists(self):
        return self.filename.exists()

    @property
    def dir_path(self):
        return self.filename.parent

    def dir_path_exists(self):
        return self.filename.parent.exists()

    @property
    def primary_profile(self):
        return self.data["APP"]["primary_profile"]

    def read_config(self, filename):
        config_file = pathlib.Path(filename).resolve()

        try:
            self.data.update(toml.load(config_file))
        except FileNotFoundError:
            message = f"Config file {filename} could not be found"
            try:
                ctx = click.get_current_context()
                ctx.fail(message)
            except RuntimeError:
                raise FileNotFoundError(message)

        self.filename = config_file

    def write_config(self, filename=None):
        config_file = pathlib.Path(filename or self.filename).resolve()
        config_dir = config_file.parent

        if not config_dir.is_dir():
            config_dir.mkdir(parents=True)

        toml.dump(self.data, config_file.open("w"))

    def add_profile(
            self,
            name: str,
            auth_file: Union[str, pathlib.Path],
            country_code: str,
            is_primary: bool = False,
            abort_on_existing_profile: bool = True,
            write_config: bool = True,
            **additional_options):

        if name in self.data["profile"] and abort_on_existing_profile:
            message = "Profile already exists."
            try:
                ctx = click.get_current_context()
                ctx.fail(message)
            except RuntimeError:
                raise RuntimeError("Profile already exists.")
        
        self.data["profile"][name] = {
            "auth_file": str(auth_file),
            "country_code": country_code,
            **additional_options
        }

        if is_primary:
            self.data["APP"]["primary_profile"] = name

        if write_config:
            self.write_config()


pass_config = click.make_pass_decorator(Config, ensure=True)


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


def build_auth_file(
        filename: pathlib.Path,
        username: str,
        password: str,
        country_code: str,
        file_password: Optional[str] = None):
    echo()
    secho("Now login with amazon to your audible account.", bold=True)

    file_options = {"filename":  filename}
    if file_password:
        file_options.update(
            password=file_password,
            encryption=DEFAULT_AUTH_FILE_ENCRYPTION)

    auth = LoginAuthenticator(
        username=username,
        password=password,
        locale=country_code,
        captcha_callback=prompt_captcha_callback,
        otp_callback=prompt_otp_callback)

    echo()
    secho("Login was successful. Now registering a new device.", bold=True)

    auth.register_device()
    device_name = auth.device_info["device_name"]
    echo()
    secho(f"Successfully registered {device_name}.", bold=True)

    if not filename.parent.exists():
        filename.parent.mkdir(parents=True)

    auth.to_file(**file_options)


class LongestSubString:
    def __init__(self, search_for, search_in, case_sensitiv=False):
        search_for = search_for.lower() if case_sensitiv else search_for
        search_in = search_in.lower() if case_sensitiv else search_in

        self._search_for = search_for
        self._search_in = search_in
        self._s = SequenceMatcher(None, self._search_for, self._search_in)
        self._match = self.match()

    def match(self):
        return self._s.find_longest_match(
            0, len(self._search_for), 0, len(self._search_in)
        )

    @property
    def longest_match(self):
        return self._search_for[self._match.a:
                                self._match.a + self._match.size]

    @property
    def percentage(self):
        return (self._match.size / len(self._search_for) * 100)
