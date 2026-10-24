"""The app and device the library presents itself as.

Every value that identifies the app or its platform lives here, because an
app for another platform sends different ones: at registration, in token and
cookie refreshes, in the browser sign-in of pre-Amazon accounts and in the
activation-bytes request. A new app version is changed in this one place.

:data:`IPHONE` reports Audible for iPhone 4.60 on iOS 26.2. Devices registered
with the older 3.56.2 profile and a 32-character serial can be refused ADRM
licenses with ``AYCL / CustomerThrottled``; this profile is granted them. The
software version is the build number of exactly that app version, so the two
change together.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceProfile:
    """The values an Audible app reports about itself and its device.

    Attributes:
        device_type: Amazon's identifier of the device family. It is part of
            the OAuth client id, so it cannot change for a registered device.
        registration_domain: The ``domain`` of the registration data.
        device_model: The device model sent at registration.
        device_name: The name template Amazon fills in with the account
            owner's first name.
        os_version: The operating system version.
        software_version: The build number of the app.
        app_name: The name of the app.
        app_version: The version of the app.
        user_agent: The user agent of the device-code requests.
        sign_in_assoc_handle: The ``openid.assoc_handle`` of the browser
            sign-in without the country code, which is appended to it.
        sign_in_page_id: The ``pageId`` of the browser sign-in.
        player_manufacturer: The ``player_manuf`` of the activation-bytes
            request.
        player_model: The ``player_model`` of the activation-bytes request.
    """

    device_type: str
    registration_domain: str
    device_model: str
    device_name: str
    os_version: str
    software_version: str
    app_name: str
    app_version: str
    user_agent: str
    sign_in_assoc_handle: str
    sign_in_page_id: str
    player_manufacturer: str
    player_model: str


IPHONE = DeviceProfile(
    device_type="A2CZJZGLK2JJVM",
    registration_domain="Device",
    device_model="iPhone",
    device_name=(
        "%FIRST_NAME%%FIRST_NAME_POSSESSIVE_STRING%%DUPE_STRATEGY_1ST%"
        "Audible for iPhone"
    ),
    os_version="26.2",
    software_version="46000856",
    app_name="Audible",
    app_version="4.60",
    # WebKit freezes the OS token since iOS 26: the app's web view reports 18_7
    # while the device registers as iOS 26.x.
    user_agent=(
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    ),
    sign_in_assoc_handle="amzn_audible_ios_lap",
    sign_in_page_id="amzn_audible_ios_privatepool",
    player_manufacturer="Audible,iPhone",
    player_model="iPhone",
)
