import pathlib
import shutil

import audible
import requests


# get download link(s) for book
def _get_download_link(client, asin, codec="LC_128_44100_stereo"):
    # need at least v0.2.1a4
    try:
        content_url = (f"https://cde-ta-g7g.amazon.com/FionaCDEServiceEngine/"
                       f"FSDownloadContent")
        params = {
            'type': 'AUDI',
            'currentTransportMethod': 'WIFI',
            'key': asin,
            'codec': codec
        }            
        r, _ = client._request(
            "GET",
            url=content_url,
            params=params,
            allow_redirects=False
        )
        link = r.headers['Location']
        tld = client.auth.locale.domain
        new_link = link.replace("cds.audible.com", f"cds.audible.{tld}")
        return new_link
    except Exception as e:
        try:
            link = e.response.headers['Location']
        
            # prepare link
            # see https://github.com/mkb79/Audible/issues/3#issuecomment-518099852
            tld = client.auth.locale.domain
            new_link = link.replace("cds.audible.com", f"cds.audible.{tld}")
            return new_link

        except Exception as e:
            print(f"Error: {e}")
            return


def download_file(url):
    r = requests.get(url, stream=True)

    title = r.headers["Content-Disposition"].split("filename=")[1]
    filename = pathlib.Path.cwd() / "audiobooks" / title

    with open(filename, 'wb') as f:
        shutil.copyfileobj(r.raw, f)
    return filename


if __name__ == "__main__":
    password = input("Password for file: ")

    auth = audible.FileAuthenticator(
        filename="FILENAME",
        encryption="json",
        password=password
    )
    client = audible.AudibleAPI(auth)

    books, _ = client.get(
        path="library",
        params={
            "response_groups": "product_attrs",
            "num_results": "999"
            }
    )

    for book in books["items"]:
        asin = book["asin"]
        dl_link = _get_download_link(asin)

        if dl_link:
            print(f"download link now: {dl_link}")
            status = download_file(dl_link)
            print(f"downloaded file: {status}")
