import base64
import json
import pathlib
import shutil

import audible
import httpx
from audible.aescipher import decrypt_voucher as dv


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


def decrypt_voucher(auth, license_response):
    # device data
    device_info = auth.device_info
    device_serial_number = device_info["device_serial_number"]
    device_type = device_info["device_type"]

    # user data
    customer_id = auth.customer_info["user_id"]

    # book specific data
    asin = license_response["content_license"]["asin"]
    encrypted_voucher = base64.b64decode(license_response["content_license"]["license_response"])

    return dv(device_serial_number=device_serial_number,
              customer_id=customer_id,
              device_type=device_type,
              asin=asin,
              voucher=encrypted_voucher)


def get_download_link(license_response):
    return license_response["content_license"]["content_metadata"]["content_url"]["offline_url"]


def download_file(url, filename):
    # example download function
    r = httpx.get(url)
    with open(filename, 'wb') as f:
        shutil.copyfileobj(r.iter_raw, f)
    return filename


if __name__ == "__main__":
    password = input("Password for file: ")

    auth = audible.FileAuthenticator(
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
            decrypted_voucher = decrypt_voucher(auth, lr)
            voucher_file.write_text(json.dumps(decrypt_voucher, indent=4))
            print(f"saved voucher to: {voucher_file}")
