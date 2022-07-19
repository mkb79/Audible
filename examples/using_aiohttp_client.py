import asyncio

import aiohttp
import audible


class ClientRequest(aiohttp.ClientRequest):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.apply_auth_flow()

    def apply_auth_flow(self) -> None:
        body = self.body
        if isinstance(body, aiohttp.BytesPayload):
            body = body._value

        sign_headers = audible.auth.sign_request(
            method=self.method,
            path=self.url.path_qs,
            body=body,
            adp_token=self._session._audible_auth.adp_token,
            private_key=self._session._audible_auth.device_private_key
        )
        for header, value in sign_headers.items():
            self.headers.add(header, value)


class ClientSession(aiohttp.ClientSession):
    def __init__(self, *args, audible_auth: audible.Authenticator, **kwargs):
        if "request_class" in kwargs:
            raise Exception("`request_class` keyword is not supported")

        super().__init__(*args, request_class=ClientRequest, **kwargs)
        self._audible_auth = audible_auth


if __name__ == "__main__":
    async def main(asin):
        body = {
            "supported_drm_types": ["Mpeg", "Adrm"],
            "quality": "Extreme",
            "consumption_type": "Download",
            "response_groups": (
                "last_position_heard, pdf_url, content_reference, chapter_info"
            )
        }
    
        fn = "credentials.json"
        auth = audible.Authenticator.from_file(fn)
    
        async with ClientSession(audible_auth=auth) as session:
            async with session.post(
                f"https://api.audible.de/1.0/content/{asin}/licenserequest",
                json=body
            ) as r:
                print(await r.json())
                #print(r.request_info)
                print(r.status)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main("B004V0WRPG"))
