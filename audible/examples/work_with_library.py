import audible


audible.set_file_logger("log.log", "warn")
audible.set_console_logger("debug")

client = audible.Client.from_file(
    filename="credentials_enc.json",
    encryption="json",
    password="yourtopsecretpassword"
)

# get library
books = client.get(
    "library",
    response_groups=("contributors, media, product_desc, series,"
                     "product_extended_attrs, product_attrs"),
    num_results=999,
    page=1
)
print(books["items"])


# get download links(s) for book
def _get_book_infos(asin):
    book = client.get(
        f"library/{asin}",
        response_groups="relationships, product_desc, product_attrs, media"
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
    response = client.post(
        f"content/{asin}/licenserequest",
        body={
            "drm_type": "Adrm",
            "consumption_type": "Download",
            "quality": quality
        }
    )
    return response['content_license']['content_metadata']['content_url']['offline_url']


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
            

    '''except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            parts_dict = dict()
            parts = self.get_parts_from_multipartbook(asin)["parts"]
            for key, value in parts.items():
                parts_dict[key] = self.get_download_link(value)
            return parts_dict'''

print(get_download_link("YOUR ASIN HERE"))

