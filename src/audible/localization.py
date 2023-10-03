import logging
import re
from typing import Dict, Optional

import httpx
from httpcore import ConnectError


logger = logging.getLogger("audible.localization")

LOCALE_TEMPLATES = {
    "germany": {
        "country_code": "de",
        "domain": "de",
        "market_place_id": "AN7V1F1VY261K",
    },
    "united_states": {
        "country_code": "us",
        "domain": "com",
        "market_place_id": "AF2M0KC94RCEA",
    },
    "united_kingdom": {
        "country_code": "uk",
        "domain": "co.uk",
        "market_place_id": "A2I9A3Q2GNFNGQ",
    },
    "france": {
        "country_code": "fr",
        "domain": "fr",
        "market_place_id": "A2728XDNODOQ8T",
    },
    "canada": {
        "country_code": "ca",
        "domain": "ca",
        "market_place_id": "A2CQZ5RBY40XE",
    },
    "italy": {
        "country_code": "it",
        "domain": "it",
        "market_place_id": "A2N7FU2W2BU2ZC",
    },
    "australia": {
        "country_code": "au",
        "domain": "com.au",
        "market_place_id": "AN7EY7DTAW63G",
    },
    "india": {
        "country_code": "in",
        "domain": "in",
        "market_place_id": "AJO3FBRUE6J4S",
    },
    "japan": {
        "country_code": "jp",
        "domain": "co.jp",
        "market_place_id": "A1QAP3MOU4173J",
    },
    "spain": {
        "country_code": "es",
        "domain": "es",
        "market_place_id": "ALMIKO4SZCSAR",
    },
    "brazil": {
        "country_code": "br",
        "domain": "com.br",
        "market_place_id": "A10J1VAYUDTYRN",
    },
}


def search_template(key: str, value: str) -> Optional[Dict[str, str]]:
    for country in LOCALE_TEMPLATES:
        locale = LOCALE_TEMPLATES[country]
        if locale[key] == value:
            logger.debug("found locale for %s", country)
            return locale

    logger.info("do not found %s in %s", value, key)
    return None


def autodetect_locale(domain: str) -> Dict[str, str]:
    """Try to automatically detect correct settings for marketplace.

    Needs the top level domain of the audible page to continue with
    (e.g. co.uk, co.jp) and returns results found.

    Args:
        domain: The top level domain for the Audible marketplace to
            detect settings for (e.g. com).

    Returns:
        The settings for the found Audible marketplace.

    Raises:
        ConnectError: If site does not exist or network error raises.
        Exception: If marketplace or country code can't be found.
    """
    domain = domain.lstrip(".")
    site = f"https://www.audible.{domain}"
    params = {"ipRedirectOverride": True, "overrideBaseCountry": True}

    try:
        resp = httpx.get(site, params=params)
    except ConnectError as e:
        logger.warning("site %s does not exists or Network Error occurs", site)
        raise e

    marketplace_pattern = re.compile(r"ue_mid = \'(.*)\'")
    marketplace_search = re.search(marketplace_pattern, resp.text)
    if marketplace_search is None:
        raise Exception("can't find marketplace")
    market_place_id = marketplace_search.group(1)

    alias_pattern = re.compile(r"autocomplete_config.searchAlias = \"(.*)\"")
    alias_search = re.search(alias_pattern, resp.text)
    if alias_search is None:
        raise Exception("can't find country code")
    country_code = alias_search.group(1).split("-")[-1]

    return {
        "country_code": country_code,
        "domain": domain,
        "market_place_id": market_place_id,
    }


class Locale:
    """Adjustments for the different marketplaces who are provided by Audible.

    You can try to ``autodetect_locale`` if your marketplace is
    not in templates`.

    """

    def __init__(
        self,
        country_code: Optional[str] = None,
        domain: Optional[str] = None,
        market_place_id: Optional[str] = None,
    ) -> None:
        if country_code is None or domain is None or market_place_id is None:
            locale = None
            if country_code:
                locale = search_template("country_code", country_code)
            elif domain:
                locale = search_template("domain", domain)

            if locale is None:
                raise Exception("can't find locale")

            country_code = country_code or locale["country_code"]
            domain = domain or locale["domain"]
            market_place_id = market_place_id or locale["market_place_id"]

        self._country_code = country_code
        self._domain = domain
        self._market_place_id = market_place_id

    def __repr__(self) -> str:
        return (
            f"Locale class for domain: {self.domain}, "
            f"marketplace: {self.market_place_id}"
        )

    def to_dict(self) -> Dict[str, str]:
        return {
            "country_code": self.country_code,
            "domain": self.domain,
            "market_place_id": self.market_place_id,
        }

    @property
    def country_code(self) -> str:
        return self._country_code

    @property
    def domain(self) -> str:
        return self._domain

    @property
    def market_place_id(self) -> str:
        return self._market_place_id
