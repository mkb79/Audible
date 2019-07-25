import asyncio

import aiohttp

import audible


# ASYNC FUNCTIONALITY
async def get_book_infos(asin):
    try:
        book, _ = await client.get(
            f"library/{asin}",
            response_groups=(
                "contributors, media, price, reviews, product_attrs, "
                "product_extended_attrs, product_desc, product_plan_details, "
                "product_plans, rating, sample, sku, series, ws4v, origin, "
                "relationships, review_attrs, categories, badge_types, "
                "category_ladders, claim_code_url, is_downloaded, pdf_url, "
                "is_returnable, origin_asin, percent_complete, provided_review"
            )
        )
        return book
    except Exception as e:
        print(e)


async def main(auth):
    async with aiohttp.ClientSession() as session:
        client = audible.AudibleAPI(auth, is_async=True, session=session)
        print(repr(client))

        library, _ = await client.get(
            "library",
            num_results=999
        )
        asins = [book["asin"] for book in library["items"]]

        # books = await asyncio.gather(*(dl_book(asin) for asin in asins))
        tasks = []
        for asin in asins:
            tasks.append(asyncio.ensure_future(get_book_infos(asin)))
        books = await asyncio.gather(*tasks)

        for book in books:
            if book is not None:
                print(book["item"])
                print("\n", 40*"-", "\n")


if __name__ == "__main__":
    # authenticate with login and deregister after job
    # don't stores any credentials on your system
    # don't use `with`-statement if you want to store credentials
    with audible.LoginAuthenticator(
        "USERNAME", "PASSWORD", locale="us"
    ) as auth:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main(auth))

    # authenticate with login
    # store credentials to file
    auth = audible.LoginAuthenticator(
        "USERNAME", "PASSWORD", locale="us"
    )
    auth.to_file(
        filename="FILENAME",
        encryption="json",
        password="PASSWORD"
    )

    # authenticate with file
    auth = audible.FileAuthenticator(
        filename="FILENAME",
        encryption="json",
        password="PASSWORD"
    )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(auth))
