import logging
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup
import requests


logger = logging.getLogger("audible.localization")


LOCALE_TEMPLATES = {
    "germany": {
        "countryCode": "de",
        "domain": "de",
        "marketPlaceId": "AN7V1F1VY261K"
    },
    "united_states": {
        "countryCode": "us",
        "domain": "com",
        "marketPlaceId": "AF2M0KC94RCEA"
    },
    "united_kingdom": {
        "countryCode": "uk",
        "domain": "co.uk",
        "marketPlaceId": "A2I9A3Q2GNFNGQ"
    },
    "france": {
        "countryCode": "fr",
        "domain": "fr",
        "marketPlaceId": "A2728XDNODOQ8T"
    },
    "canada": {
        "countryCode": "ca",
        "domain": "ca",
        "marketPlaceId": "A2CQZ5RBY40XE"
    },
    "italy": {
        "countryCode": "it",
        "domain": "it",
        "marketPlaceId": "A2N7FU2W2BU2ZC"
    },
    "australia": {
        "countryCode": "au",
        "domain": "com.au",
        "marketPlaceId": "AN7EY7DTAW63G"
    },
    "india": {
        "countryCode": "in",
        "domain": "in",
        "marketPlaceId": "AJO3FBRUE6J4S"
    },
    "japan": {
        "countryCode": "jp",
        "domain": "co.jp",
        "marketPlaceId": "A1QAP3MOU4173J"
    }
}


def search_template(key: str, value: Any):
    for country in LOCALE_TEMPLATES:
        locale = LOCALE_TEMPLATES[country]
        if locale[key] == value:
            logger.debug(f"found locale for {country}")
            return locale

    logger.info(f"don\'t found {value} in {key}")
    return None


def autodetect_locale(domain: str) -> Dict[str, str]:
    """
    Try to automatically detect correct settings for marketplace.

    Needs the top level domain of the audible page to continue with
    (e.g. co.uk, co.jp) and returns results found.

    """
    domain = domain.lstrip(".")
    site = f"https://www.audible.{domain}"

    try:
        resp = requests.get(site)
    except requests.exceptions.ConnectionError:
        logger.warn(f"site {site} doesn\'t exists or Network Error occours")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    login_link = soup.find("a", class_="ui-it-sign-in-link")["href"]
    parsed_link = urlparse(login_link)
    query_string = parse_qs(parsed_link.query)
    marketPlaceId = query_string['marketPlaceId'][0]
    countryCode = query_string['pageId'][0].split("_")[-1]

    return {
        "countryCode": countryCode,
        "domain": domain,
        "marketPlaceId": marketPlaceId
    }


class Locale:
    """
    Adjustments for the different marketplaces who are provided by audible.

    Look at `locales.json` for examples. You can try to
    ``autodetect_locale`` if your marketplace is not in `locales.json`.
    
    """
    def __init__(self, countryCode: Optional[str] = None,
                 domain: Optional[str] = None,
                 marketPlaceId: Optional[str] = None) -> None:

        if not all([countryCode, domain, marketPlaceId]):
            locale = None
            if countryCode:
                locale = search_template("countryCode", countryCode)
            elif domain:
                locale = search_template("domain", domain)

            if locale is None:
                raise Exception("can\'t find locale")

        self._countryCode = countryCode or locale["countryCode"]
        self._domain = domain or locale["domain"]
        self._marketPlaceId = marketPlaceId or locale["marketPlaceId"]

    def __repr__(self):
        return (f"Locale class for domain: {self.domain}, "
                f"marketplace: {self.marketPlaceId}")

    def to_dict(self) -> Dict[str, str]:
        return {
            "countryCode": self.countryCode,
            "domain": self.domain,
            "marketPlaceId": self.marketPlaceId
        }

    @property
    def countryCode(self) -> str:
        return self._countryCode

    @property
    def domain(self) -> str:
        return self._domain

    @property
    def marketPlaceId(self) -> str:
        return self._marketPlaceId
