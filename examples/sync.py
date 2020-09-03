import audible


# get library
def get_library():
    books = client.get(
        path="library",
        params={
            "response_groups": (
                "contributors, media, product_desc, series,"
                "product_extended_attrs, product_attrs"
            ),
            "num_results": 999,
            "page": 1
        }
    )
    return books


def _get_book_infos(asin):
    book = client.get(
        path=f"library/{asin}",
        params={
            "response_groups": "relationships, product_desc, product_attrs, media"
        }
    )
    book = book["item"]

    book_info = dict()
    book_info["title"] = book["title"]
    book_info["subtitle"] = book["subtitle"]
    book_info["image_url"] = book["product_images"]

    if book["content_delivery_type"] != "MultiPartBook":
        book_info["parts"] = None
        return book_info

    # get parts from MultiPartBook
    parts = book["relationships"]
    parts_dict = dict()
    for part in parts:
        if part["relationship_type"] == "component":
            parts_dict[part["sort"]] = part["asin"]
    book_info["parts"] = dict(sorted(parts_dict.items()))

    return book_info


def _get_download_link(asin, quality):
    data = client.post(
        path=f"content/{asin}/licenserequest",
        body={
            "drm_type": "Adrm",
            "consumption_type": "Download",
            "quality": quality
        }
    )
    return data['content_license']['content_metadata']['content_url']['offline_url']


def get_download_link(asin, quality="Extreme"):
    book_infos = _get_book_infos(asin)

    if book_infos["parts"] is None:
        book_infos["dl_links"] = {"1": _get_download_link(asin, quality)}

    else:
        parts = book_infos["parts"]
        dl_links = dict()
        for key, value in parts.items():
            dl_links[key] = _get_download_link(value, quality)
        book_infos["dl_links"] = dl_links

    book_infos.pop("parts")
    return book_infos


if __name__ == "__main__":
    password = input("Password for file: ")

    auth = audible.FileAuthenticator(
        filename="FILENAME",
        password=password
    )
    client = audible.AudibleAPI(auth)
    link = get_download_link("BOOK_ASIN")
    print(link)
