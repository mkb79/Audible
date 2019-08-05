import pathlib
import shutil

import audible
import requests


# get download link(s) for book
def _get_download_link(asin, codec="LC_128_44100_stereo"):
    try:
        content_url = f"https://cde-ta-g7g.amazon.com/FionaCDEServiceEngine/FSDownloadContent"
        params = {
            'type': 'AUDI',
            'currentTransportMethod': 'WIFI',
            'key': asin,
            'codec': codec
        }
        
        signed_headers = client._sign_request('GET', content_url, params, {})
        headers = client.headers.copy()
        for item in signed_headers:
            headers[item] = signed_headers[item]    
        
        r = client.session.request('GET', content_url, headers=headers, params=params, json={}, allow_redirects=False)
        link = r.headers['Location']
    
        # prepare link
        # see https://github.com/mkb79/Audible/issues/3#issuecomment-518099852 
        tld = auth.locale.audible_api.split("api.audible.")[1]
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
        "library",
        response_groups="product_attrs",
        num_results="999"
    )

    for book in books["items"]:
        asin = book["asin"]
        dl_link = _get_download_link(asin)

        if dl_link:
            print(f"download link now: {dl_link}")
            status = download_file(dl_link)
            print(f"downloaded file: {status}")
