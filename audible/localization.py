class Markets:
    def __init__(self, amazon_login, amazon_api, audible_api, accept_language,
                 marketPlaceId, openid_assoc_handle, oauth_lang,
                 auth_register_domain, market_code=None):

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
        return "Stores market object"

    @classmethod
    def from_market_code(cls, market_code):
        return cls(**market_templates[market_code], market_code=market_code)

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


market_templates = {
    "de": {
        "amazon_login": "https://www.amazon.de",
        "amazon_api": "https://api.amazon.de",
        "audible_api": "https://api.audible.de",
        "accept_language": "de-DE",
        "marketPlaceId": "AN7V1F1VY261K",
        "openid_assoc_handle": "amzn_audible_ios_de",
        "oauth_lang": "de-DE",
        "auth_register_domain": ".amazon.de"
    },
    "us": {
        "amazon_login": "https://www.amazon.com",
        "amazon_api": "https://api.amazon.com",
        "audible_api": "https://api.audible.com",
        "accept_language": "en-US",
        "marketPlaceId": "AF2M0KC94RCEA",
        "openid_assoc_handle": "amzn_audible_ios_us",
        "oauth_lang": "en-US",
        "auth_register_domain": ".amazon.com"
    },
    "uk": {
        "amazon_login": "https://www.amazon.co.uk",
        "amazon_api": "https://api.amazon.co.uk",
        "audible_api": "https://api.audible.co.uk",
        "accept_language": "en-GB",
        "marketPlaceId": "A2I9A3Q2GNFNGQ",
        "openid_assoc_handle": "amzn_audible_ios_uk",
        "oauth_lang": "en-GB",
        "auth_register_domain": ".amazon.co.uk"
    },
    "fr": {
        "amazon_login": "https://www.amazon.fr",
        "amazon_api": "https://api.amazon.fr",
        "audible_api": "https://api.audible.fr",
        "accept_language": "fr-FR",
        "marketPlaceId": "A2728XDNODOQ8T",
        "openid_assoc_handle": "amzn_audible_ios_fr",
        "oauth_lang": "fr-FR",
        "auth_register_domain": ".amazon.fr"
    },
    "ca": {
        "amazon_login": "https://www.amazon.ca",
        "amazon_api": "https://api.amazon.ca",
        "audible_api": "https://api.audible.ca",
        "accept_language": "en-CA",
        "marketPlaceId": "A2CQZ5RBY40XE",
        "openid_assoc_handle": "amzn_audible_ios_ca",
        "oauth_lang": "en-CA",
        "auth_register_domain": ".amazon.ca"
    }
}


def custom_market(amazon_login, amazon_api, audible_api, accept_language,
                  marketPlaceId, openid_assoc_handle, oauth_lang,
                  auth_register_domain):
    """
    This function is deprecated and will be removed in future releases.
    Please use Markets class instead.
    """
    market = {
        "amazon_login": amazon_login,
        "amazon_api": amazon_api,
        "audible_api": audible_api,
        "accept_language": accept_language,
        "marketPlaceId": marketPlaceId,
        "openid_assoc_handle": openid_assoc_handle,
        "oauth_lang": oauth_lang,
        "auth_register_domain": auth_register_domain
    }
    return Markets(**market)
