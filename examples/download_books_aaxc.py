import pathlib
import shutil

import audible
import httpx


# files downloaded via this script can't be converted at this moment
# audible uses a new format (aaxc instead of aax)
# more informations and workaround here:
# https://github.com/mkb79/Audible/issues/3


# get download link(s) for book
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


def download_file(url, filename):
    r = httpx.get(url)
    with open(filename, 'wb') as f:
        shutil.copyfileobj(r.iter_raw, f)
    return filename


if __name__ == "__main__":
    password = input("Password for file: ")

    auth = audible.FileAuthenticator(
        filename="FILENAME",
        encryption="json",
        password=password
    )
    client = audible.AudibleAPI(auth)

    books = client.get(
        path="0.0/library/books",
        params={
            "purchaseAfterDate": "01/01/1970"
        }
    )["books"]["book"]

    for book in books:
        asin = book['asin']
        title = book['title'] + f"( {asin}).aaxc"
        dl_link = _get_download_link(asin, quality="Extreme")
        if dl_link:
            filename = pathlib.Path.cwd() / "audiobooks" / title
            print(f"download link now: {dl_link}")
            status = download_file(dl_link, filename)
            print(f"downloaded file: {status}")
