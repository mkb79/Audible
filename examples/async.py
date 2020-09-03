import asyncio

import audible


# ASYNC FUNCTIONALITY
async def get_book_infos(client, asin):
    try:
        book = await client.get(
            path=f"library/{asin}",
            params={
                "response_groups": (
                    "contributors, media, price, reviews, product_attrs, "
                    "product_extended_attrs, product_desc, product_plan_details, "
                    "product_plans, rating, sample, sku, series, ws4v, origin, "
                    "relationships, review_attrs, categories, badge_types, "
                    "category_ladders, claim_code_url, is_downloaded, pdf_url, "
                    "is_returnable, origin_asin, percent_complete, provided_review"
                )
            }
        )
        return book
    except Exception as e:
        print(e)


async def main(auth):
    async with audible.AsyncClient(auth) as client:
        print(repr(client))

        library = await client.get(
            path="library",
            params={
                "num_results": 999
            }
        )
        asins = [book["asin"] for book in library["items"]]

        # books = await asyncio.gather(*(dl_book(asin) for asin in asins))
        tasks = []
        for asin in asins:
            tasks.append(asyncio.ensure_future(get_book_infos(client, asin)))
        books = await asyncio.gather(*tasks)

        for book in books:
            if book is not None:
                print(book["item"])
                print("\n", 40*"-", "\n")


if __name__ == "__main__":
    # authenticate with login
    # don't stores any credentials on your system
    auth = audible.LoginAuthenticator(
        "USERNAME",
        "PASSWORD",
        locale="us"
    )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(auth))

    # store credentials to file
    auth.to_file(
        filename="FILENAME",
        encryption="json",
        password="PASSWORD"
    )

    # register device
    auth.register_device()

    # save again
    auth.to_file()

    # load credentials from file
    auth = audible.FileAuthenticator(
        filename="FILENAME",
        password="PASSWORD"
    )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(auth))

    # deregister device
    auth.deregister_device()
