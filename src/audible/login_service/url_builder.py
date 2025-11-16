from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlencode


if TYPE_CHECKING:
    from audible.device import BaseDevice
    from audible.localization import Locale
    from audible.login_service.pkce import PKCE


OAUTH_SCOPES = "device_auth_access"
SUPPORTED_USERNAME_DOMAINS = ("de", "com", "co.uk")


@dataclass(slots=True, frozen=True)
class OAuthURLBuilder:
    """Build OAuth URL for Amazon/Audible device login.

    Attributes:
        locale: Marketplace instance.
        pkce: PKCE pair with a precomputed challenge.
        device: Device settings.
        with_username: Switch to username login flow (DE/US/UK only).
    """

    locale: Locale
    pkce: PKCE
    device: BaseDevice
    with_username: bool = False

    def build(self) -> str:
        """Build the OAuth URL and return it with the device serial.

        Returns:
            String of oauth_url.

        Raises:
            ValueError: If username flow is requested for an unsupported domain.
        """
        domain_lc = self.locale.domain.lower()
        if self.with_username and domain_lc not in SUPPORTED_USERNAME_DOMAINS:
            raise ValueError(
                "Login with username is only supported for DE, US and UK marketplaces!"
            )

        if self.with_username:
            base_url = f"https://www.audible.{domain_lc}/ap/signin"
            return_to = f"https://www.audible.{domain_lc}/ap/maplanding"
            assoc_handle = f"amzn_audible_ios_lap_{self.locale.country_code}"
            page_id = "amzn_audible_ios_privatepool"
        else:
            base_url = f"https://www.amazon.{domain_lc}/ap/signin"
            return_to = f"https://www.amazon.{domain_lc}/ap/maplanding"
            assoc_handle = f"amzn_audible_ios_{self.locale.country_code}"
            page_id = "amzn_audible_ios"

        params = {
            "openid.oa2.response_type": "code",
            "openid.oa2.code_challenge_method": "S256",
            "openid.oa2.code_challenge": self.pkce.challenge,
            "openid.return_to": return_to,
            "openid.assoc_handle": assoc_handle,
            "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
            "pageId": page_id,
            "accountStatusPolicy": "P1",
            "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.mode": "checkid_setup",
            "openid.ns.oa2": "http://www.amazon.com/ap/ext/oauth/2",
            "openid.oa2.client_id": f"device:{self.device.build_client_id()}",
            "openid.ns.pape": "http://specs.openid.net/extensions/pape/1.0",
            "marketPlaceId": self.locale.market_place_id,
            "openid.oa2.scope": OAUTH_SCOPES,
            "forceMobileLayout": "true",
            "openid.ns": "http://specs.openid.net/auth/2.0",
            "openid.pape.max_auth_age": "0",
        }

        return f"{base_url}?{urlencode(params)}"
