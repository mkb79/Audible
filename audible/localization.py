from urllib.parse import urlparse


localization = {
    "de": {
        "AMAZON_LOGIN": urlparse("https://www.amazon.de"),
        "AMAZON_API": urlparse("https://api.amazon.de"),
        "AUDIBLE_API": urlparse("https://api.audible.de"),
        "Accept-Language": "de-DE",
        "marketPlaceId": "AN7V1F1VY261K",
        "openid_assoc_handle": "amzn_audible_ios_de",
        "oauth_lang": "de-DE",
        "auth_register_domain": ".amazon.de"
    },
    "us": {
        "AMAZON_LOGIN": urlparse("https://www.amazon.com"),
        "AMAZON_API": urlparse("https://api.amazon.com"),
        "AUDIBLE_API": urlparse("https://api.audible.com"),
        "Accept-Language": "en-US",
        "marketPlaceId": "AF2M0KC94RCEA",
        "openid_assoc_handle": "amzn_audible_ios_us",
        "oauth_lang": "en-US",
        "auth_register_domain": ".amazon.com"
    },
    "uk": {
        "AMAZON_LOGIN": urlparse("https://www.amazon.co.uk"),
        "AMAZON_API": urlparse("https://api.amazon.co.uk"),
        "AUDIBLE_API": urlparse("https://api.audible.co.uk"),
        "Accept-Language": "en-GB",
        "marketPlaceId": "A2I9A3Q2GNFNGQ",
        "openid_assoc_handle": "amzn_audible_ios_uk",
        "oauth_lang": "en-GB",
        "auth_register_domain": ".amazon.co.uk"
    },
    "fr": {
        "AMAZON_LOGIN": urlparse("https://www.amazon.fr"),
        "AMAZON_API": urlparse("https://api.amazon.fr"),
        "AUDIBLE_API": urlparse("https://api.audible.fr"),
        "Accept-Language": "fr-FR",
        "marketPlaceId": "A2728XDNODOQ8T",
        "openid_assoc_handle": "amzn_audible_ios_fr",
        "oauth_lang": "fr-FR",
        "auth_register_domain": ".amazon.fr"
    },
    "ca": {
        "AMAZON_LOGIN": urlparse("https://www.amazon.ca"),
        "AMAZON_API": urlparse("https://api.amazon.ca"),
        "AUDIBLE_API": urlparse("https://api.audible.ca"),
        "Accept-Language": "en-CA",
        "marketPlaceId": "A2CQZ5RBY40XE",
        "openid_assoc_handle": "amzn_audible_ios_ca",
        "oauth_lang": "en-CA",
        "auth_register_domain": ".amazon.ca"
    }
}


def custom_local(amazon_login, amazon_api, audible_api, accept_language, marketPlaceId,
                 openid_assoc_handle, oauth_lang, auth_register_domain):
    return {
        "AMAZON_LOGIN": urlparse(amazon_login),
        "AMAZON_API": urlparse(amazon_api),
        "AUDIBLE_API": urlparse(audible_api),
        "Accept-Language": accept_language,
        "marketPlaceId": marketPlaceId,
        "openid_assoc_handle": openid_assoc_handle,
        "oauth_lang": oauth_lang,
        "auth_register_domain": auth_register_domain
    }

