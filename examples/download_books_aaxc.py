import json
import pathlib

import audible
import httpx
from audible.aescipher import decrypt_voucher_from_licenserequest


# files downloaded via this script can be converted
# audible uses a new format (aaxc instead of aax)
# more informations and workaround here:
# https://github.com/mkb79/Audible/issues/3
# especially: https://github.com/mkb79/Audible/issues/3#issuecomment-705262614


# get license response for book
def get_license_response(client, asin, quality):
    try:
        response = client.post(
            f"content/{asin}/licenserequest",
            body={
                "drm_type": "Adrm",
                "consumption_type": "Download",
                "quality": quality
            }
        )
        return response
    except Exception as e:
        print(f"Error: {e}")
        return


def get_download_link(license_response):
    return license_response["content_license"]["content_metadata"]["content_url"]["offline_url"]


def download_file(url, filename):
    headers = {
        "User-Agent": "Audible/671 CFNetwork/1240.0.4 Darwin/20.6.0"
    }
    with httpx.stream("GET", url, headers=headers) as r:
        with open(filename, 'wb') as f:
            for chunck in r.iter_bytes():
                f.write(chunck)
    return filename


if __name__ == "__main__":
    password = input("Password for file: ")

    auth = audible.Authenticator.from_file(
        filename="FILENAME",
        password=password
    )
    client = audible.Client(auth)

    books = client.get(
        path="library",
        params={
            "response_groups": "product_attrs",
            "num_results": "999"
            }
    )

    for book in books["items"]:
        asin = book["asin"]
        title = book["title"] + f"( {asin}).aaxc"
        lr = get_license_response(client, asin, quality="Extreme")

        if lr:
            # download book
            dl_link = get_download_link(lr)
            filename = pathlib.Path.cwd() / "audiobooks" / title
            print(f"download link now: {dl_link}")
            status = download_file(dl_link, filename)
            print(f"downloaded file: {status} to {filename}")

            # save voucher
            voucher_file = filename.with_suffix(".json")
            decrypted_voucher = decrypt_voucher_from_licenserequest(auth, lr)
            voucher_file.write_text(json.dumps(decrypted_voucher, indent=4))
            print(f"saved voucher to: {voucher_file}")
