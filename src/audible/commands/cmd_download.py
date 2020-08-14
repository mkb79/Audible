import asyncio
import pathlib

import click
import httpx
from click import echo
from tabulate import tabulate

from .utils import pass_config, LongestSubString
from ..auth import FileAuthenticator
from ..client import Client


def search_by_title(search_title, library, p=80):
    items = library["items"]
    matching_items = []

    for item in items:
        title = item["title"]
        subtitle = item["subtitle"]
        title += f": {subtitle}" if subtitle else ""

        match = LongestSubString(search_title, title)

        if match.percentage >= p:
             matching_items.append(
                 {
                     "title": title,
                     "asin": item["asin"],
                     "match_percentage": round(match.percentage, 2)
                 }
             )

    matching_items = sorted(matching_items, key = lambda i: i["match_percentage"], reverse=True)

    if len(matching_items) == 0:
        echo(f"Product with title '{search_title}' not found.")
        return

    if len(matching_items) > 1:
        full_match = [item for item in matching_items if item["match_percentage"] == 100]
        
        if len(full_match) > 1:
            head = ["percentage", "title", "asin"]
            data = []
    
            for item in matching_items:
                data.append(
                    [item["match_percentage"], item["title"], item["asin"]])
                
            echo("Too many matches found. Please limit your search.")
            table = tabulate(
                data, head, tablefmt="pretty",
                colalign=("center", "left", "left"))        
            echo(table)
            return

    asin = matching_items[0]["asin"]
    title = matching_items[0]["title"]
    echo(f"Found {title} with asin {asin}")
    if click.confirm("Proceed with this product"):
        return asin


# get download link(s) for book
async def get_download_link(auth, asin, codec="LC_128_44100_stereo"):
    # need at least v0.4.0dev
    if auth.adp_token is None:
        raise Exception("No adp token present. Can't get download link.")

    try:
        content_url = ("https://cde-ta-g7g.amazon.com/FionaCDEServiceEngine/"
                       "FSDownloadContent")
        params = {
            'type': 'AUDI',
            'currentTransportMethod': 'WIFI',
            'key': asin,
            'codec': codec
        }
        async with httpx.AsyncClient() as client:
            r = await client.get(
                    url=content_url,
                    params=params,
                    allow_redirects=False,
                    auth=auth)

        # prepare link
        # see https://github.com/mkb79/Audible/issues/3#issuecomment-518099852
        link = r.headers['Location']
        tld = auth.locale.domain
        new_link = link.replace("cds.audible.com", f"cds.audible.{tld}")
        return new_link
    except Exception as e:
        echo(f"Error: {e}")


async def download_file(url): 
    try:
        client = httpx.AsyncClient(timeout=15)
        async with client.stream("GET", url) as r:
            title = r.headers["Content-Disposition"].split("filename=")[1]
            length = int(r.headers["Content-Length"])
            filename = pathlib.Path.cwd() / title

            echo(f"Downloading: {title}")
            echo(f"Size:        {(length / 1024 / 1024):.2f} MB")
            with click.progressbar(length=length) as bar:
                with filename.open("wb") as f:
                    async for chunk in r.aiter_bytes():
                        f.write(chunk)
                        bar.update(len(chunk))

            echo(f"File downloaded in {r.elapsed}")
            return filename
    except KeyError:
        return "Nothing downloaded"


async def start(auth, asin, title, link_only):
    asin = list(asin)

    if title:
        with Client(auth) as client:
            library = client.get("library", response_groups="product_desc")
        for t in title:
            result = search_by_title(t, library)
            asin.append(result) if result else ""

    for a in asin:
        link = await get_download_link(auth, a)
        if link_only:
            echo(link)
            continue

        status = await download_file(link)
        echo(status)


@click.command()
@click.option(
    "--profile", "-P",
    help="The profile to use instead primary profile."
)
@click.option(
    "--password", "-p",
    help="The password for the profile auth file."
)
@click.option(
    "--asin",
    required=False,
    multiple=True,
    help="The asin of the product you want to download"
)
@click.option(
    "--title",
    required=False,
    multiple=True,
    help="The tile of the product you want to download"
)
@click.option(
    "--link-only",
    is_flag=True,
    help="Returns the download link instead of downloding the file"
)
@pass_config
@click.pass_context
def cli(ctx, config, profile, password, asin, title, link_only):
    """download file from library"""
    profile = profile or config.primary_profile

    if profile is None:
        ctx.fail("No profile provided and primary profile not set properly in config.")
         
    if profile not in config.data["profile"]:
        ctx.fail("Provided profile not found in config.")

    profile = config.data["profile"][profile]

    auth_file = config.dir_path / profile["auth_file"]
    country_code = profile["country_code"]

    auth = FileAuthenticator(
        auth_file, password, country_code)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(start(auth, asin, title, link_only))
