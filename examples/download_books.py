import pathlib
import requests
import shutil

import audible


# get download link(s) for book

'''
since 2019-07-18 retrieving library (api_version 1.0) seems to be broken
get a single book with ``client.get(f"library/{asin}") is still possible

switch back to api_version 0.0 when retrieving library
'''

def _get_download_link(asin, quality):
    try:
        response = client.post(
            f"content/{asin}/licenserequest",
            body={
                "drm_type": "Adrm",
                "consumption_type": "Download",
                "quality": quality
            }
        )
        return response['content_license']['content_metadata']['content_url']['offline_url']
    except Exception as e:
        print(f"Error: {e}")
        return

    return response['content_license']['content_metadata']['content_url']['offline_url']


def download_file(url, filename):
    r = requests.get(url, stream=True)
    with open(filename, 'wb') as f:
        shutil.copyfileobj(r.raw, f)
    return filename


if __name__ == "__main__":
    password = input("Password for file: ")

    client = audible.Client.from_file("credentials_enc.json", password, encryption="json")

    books = client.get("library/books", api_version="0.0", purchaseAfterDate="01/01/1970")["books"]["book"]

    for book in books:
        asin = book['asin']
        title = book['title'] + ".aax"
        dl_link = _get_download_link(asin, quality="Extreme")
        if dl_link:
            filename = pathlib.Path.cwd() / "audiobooks" / title
            print(f"download link now: {dl_link}")
            status = download_file(dl_link, filename)
            print(f"downloaded file: {status}")
