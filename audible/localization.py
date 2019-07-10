from bs4 import BeautifulSoup
import logging
import re
import requests
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse


_localization_logger = logging.getLogger('audible.localization')


class Markets:
    """
    Adjustments for the different marketplaces who are provided by audible.

    Look at `market_templates` for examples. You can try to
    ``autodetect_market`` if your marketplace is not in `market_templates`.
    
    """
    def __init__(self, amazon_login: str, amazon_api: str,
                 audible_api: str, accept_language: str,
                 marketPlaceId: str, openid_assoc_handle: str,
                 oauth_lang: str, auth_register_domain: str,
                 market_code: Optional[str] = None) -> None:

        self._amazon_login = amazon_login
        self._amazon_api = amazon_api
        self._audible_api = audible_api
        self._accept_language = accept_language
        self._marketPlaceId = marketPlaceId
        self._openid_assoc_handle = openid_assoc_handle
        self._oauth_lang = oauth_lang
        self._auth_register_domain = auth_register_domain

        if market_code is None:
            self._market_code = None
        elif market_code not in market_templates:
            raise ValueError(f"{market_code} not found in market templates")
        else:
            self._market_code = market_code

    def __repr__(self):
        return (f"Market class for api: {self._audible_api}, "
                f"marketplace: {self._marketPlaceId}")

    @classmethod
    def from_market_code(cls, market_code: str):
        """
        Compares `market_code` with dict keys from `market_templates` and
        returns a ``Markets`` instance from match result.

        """
        return cls(**market_templates[market_code], market_code=market_code)

    @classmethod
    def from_autodetect_market(cls, tld: str):
        """
        Uses ``autodetct_market`` to automatically detect correct settings for
        marketplace.

        Needs the top level domain of the audible page to continue with.

        """
        return cls(**autodetect_market(tld))

    def to_dict(self) -> Dict[str, str]:
        return {"amazon_login": self._amazon_login,
                "amazon_api": self._amazon_api,
                "audible_api": self._audible_api,
                "accept_language": self._accept_language,
                "marketPlaceId": self._marketPlaceId,
                "openid_assoc_handle": self._openid_assoc_handle,
                "oauth_lang": self._oauth_lang,
                "auth_register_domain": self._auth_register_domain}

    @property
    def amazon_login(self):
        return self._amazon_login

    @property
    def amazon_api(self):
        return self._amazon_api

    @property
    def audible_api(self):
        return self._audible_api

    @property
    def accept_language(self):
        return self._accept_language

    @property
    def marketPlaceId(self):
        return self._marketPlaceId

    @property
    def openid_assoc_handle(self):
        return self._openid_assoc_handle

    @property
    def oauth_lang(self):
        return self._oauth_lang

    @property
    def auth_register_domain(self):
        return self._auth_register_domain

    @property
    def market_code(self):
        return self._market_code


market_templates = {"de": {"amazon_login": "https://www.amazon.de",
                           "amazon_api": "https://api.amazon.de",
                           "audible_api": "https://api.audible.de",
                           "accept_language": "de-DE",
                           "marketPlaceId": "AN7V1F1VY261K",
                           "openid_assoc_handle": "amzn_audible_ios_de",
                           "oauth_lang": "de-DE",
                           "auth_register_domain": ".amazon.de"},

                    "us": {"amazon_login": "https://www.amazon.com",
                           "amazon_api": "https://api.amazon.com",
                           "audible_api": "https://api.audible.com",
                           "accept_language": "en-US",
                           "marketPlaceId": "AF2M0KC94RCEA",
                           "openid_assoc_handle": "amzn_audible_ios_us",
                           "oauth_lang": "en-US",
                           "auth_register_domain": ".amazon.com"},

                    "uk": {"amazon_login": "https://www.amazon.co.uk",
                           "amazon_api": "https://api.amazon.co.uk",
                           "audible_api": "https://api.audible.co.uk",
                           "accept_language": "en-GB",
                           "marketPlaceId": "A2I9A3Q2GNFNGQ",
                           "openid_assoc_handle": "amzn_audible_ios_uk",
                           "oauth_lang": "en-GB",
                           "auth_register_domain": ".amazon.co.uk"},

                    "fr": {"amazon_login": "https://www.amazon.fr",
                           "amazon_api": "https://api.amazon.fr",
                           "audible_api": "https://api.audible.fr",
                           "accept_language": "fr-FR",
                           "marketPlaceId": "A2728XDNODOQ8T",
                           "openid_assoc_handle": "amzn_audible_ios_fr",
                           "oauth_lang": "fr-FR",
                           "auth_register_domain": ".amazon.fr"},

                    "ca": {"amazon_login": "https://www.amazon.ca",
                           "amazon_api": "https://api.amazon.ca",
                           "audible_api": "https://api.audible.ca",
                           "accept_language": "en-CA",
                           "marketPlaceId": "A2CQZ5RBY40XE",
                           "openid_assoc_handle": "amzn_audible_ios_ca",
                           "oauth_lang": "en-CA",
                           "auth_register_domain": ".amazon.ca"}}


def custom_market(amazon_login: str, amazon_api: str, audible_api: str,
                  accept_language: str, marketPlaceId: str,
                  openid_assoc_handle: str, oauth_lang: str,
                  auth_register_domain: str) -> Markets:
    """
    This function is deprecated and will be removed in future releases.
    Please use Markets class instead.

    """
    market = {"amazon_login": amazon_login,
              "amazon_api": amazon_api,
              "audible_api": audible_api,
              "accept_language": accept_language,
              "marketPlaceId": marketPlaceId,
              "openid_assoc_handle": openid_assoc_handle,
              "oauth_lang": oauth_lang,
              "auth_register_domain": auth_register_domain}

    return Markets(**market)


def autodetect_market(tld: str) -> Dict[str, str]:
    """
    Try to automatically detect correct settings for marketplace.

    Needs the top level domain of the audible page to continue with
    (e.g. co.uk, co.jp) and returns results found.

    """
    tld = tld.lstrip(".")
    response = requests.get(f"https://www.audible.{tld}")
    soup = BeautifulSoup(response.text, "html.parser")

    login_link = soup.find("a", class_="ui-it-sign-in-link")["href"]
    parsed_link = urlparse(login_link)
    query_string = parse_qs(parsed_link).query
    marketPlaceId = query_string['marketPlaceId'][0]
    assoc_handle = query_string['pageId'][0].split("amzn_audible_")[-1]
    
    scripts = soup.find_all("script", type="text/javascript")
    for script in scripts:
        lang = re.search('language_of_preference\:\"(.*?)\"', script.text)
        pref_lang = lang.group(1) if lang else None

    return {"amazon_login": f"https://www.amazon.{tld}",
            "amazon_api": f"https://api.amazon.{tld}",
            "audible_api": f"https://api.audible.{tld}",
            "accept_language": pref_lang,
            "marketPlaceId": marketPlaceId,
            "openid_assoc_handle": f"amzn_audible_ios_{assoc_handle}",
            "oauth_lang": pref_lang,
            "auth_register_domain": f".amazon.{tld}"}
