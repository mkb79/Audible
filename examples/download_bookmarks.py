import json
import os

import httpx

import audible


def main():
    country_code = "uk"
    filename = "./audible_credentials.txt"
    encryption = False
    if os.path.exists(filename):
        auth = audible.Authenticator.from_file(filename)
    else:
        auth = audible.Authenticator.from_login_external(locale=country_code)
        auth.to_file(filename, encryption=False)
        if encryption == "json":
            password = "sample_pass"  # noqa: S105
            auth.to_file(filename + ".json", password, encryption="json")

    local_library = []
    with audible.Client(auth=auth) as client:
        library = client.get(
            "1.0/library",
            num_results=1000,
            response_groups="product_desc, product_attrs",
            sort_by="-PurchaseDate",
        )
        books = library["items"]
        book = books[0]
        print(f"keys:{book.keys()}")
        for i, book in enumerate(books):
            asin = book.get("asin")
            print(
                f'#{i} Title: {book.get("title")} - time:{book.get("runtime_length_min")} asin:{asin}'
            )
            local_library.append(
                {
                    "title": book.get("title"),
                    "time": book.get("runtime_length_min"),
                    "asin": asin,
                }
            )

    books = local_library
    with httpx.Client(auth=auth) as client:
        for book in books:
            asin = book.get("asin")
            bookmarks = get_bookmarks(client, asin)
            book["bookmarks"] = bookmarks
            print(bookmarks)
            if bookmarks["full_text"] == "":
                print(book.get("title") + " has no bookmarks!")

    with open("books.json", "w") as write_file:
        json.dump(books, write_file, indent=4)


def sample_get_bookmarks():
    country_code = "uk"
    filename = "./audible_credentials.txt"
    encryption = False
    if os.path.exists(filename):
        auth = audible.Authenticator.from_file(filename)
    else:
        auth = audible.Authenticator.from_login_external(locale=country_code)
        auth.to_file(filename, encryption=False)
        if encryption == "json":
            password = "sample_pass"  # noqa: S105
            auth.to_file(filename + ".json", password, encryption="json")

    asin = "1639298851"

    with httpx.Client(auth=auth) as client:
        get_bookmarks(client, asin)


def authenticate(username, password, country_code):
    auth = audible.Authenticator.from_login(
        username, password, locale=country_code, with_username=False
    )
    return auth


def get_bookmarks(client, asin):
    params = {"type": "AUDI", "key": asin}
    resp = client.get(
        #  f"https://www.audible.{tld}/companion-file/{asin}"
        "https://cde-ta-g7g.amazon.com/FionaCDEServiceEngine/sidecar",
        params=params,
    )
    url = resp.url
    print(url)
    bookmarks_dict = {"bookmarks": [], "full_text": ""}
    try:
        body = resp.json()["payload"]
        # print(body)
        # print(f'keys:{body.keys()}')
        # first bookmark is last heard: {'creationTime': '2022-03-22 08:13:02.0', 'type': 'audible.last_heard', 'startPosition': '0'}
        # print(f'keys:{body["records"][1].keys()}')

        for i, bookmark in enumerate(body["records"]):
            creation_time = bookmark.get("creationTime")
            start_position = bookmark.get("startPosition")
            end_position = bookmark.get("endPosition")
            if bookmark.get("metadata"):
                metadata = bookmark.get("metadata")
                note = metadata.get("note", "")

            else:
                note = bookmark.get("text", "")
            if note == "":
                print("NOTE MISSING")
                print(bookmark)
                continue
            bookmark_line = f"#{i} created: {creation_time} from:{start_position}-{end_position}:{note}"
            print(bookmark_line)
            bookmarks_dict["bookmarks"].append(bookmark_line)
            bookmarks_dict["full_text"] = bookmarks_dict["full_text"] + (f"{note}\n")
    except Exception:
        print("FAILED response")
        print(resp.text)
    return bookmarks_dict


main()
