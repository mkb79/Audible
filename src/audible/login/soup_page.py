from __future__ import annotations

import logging

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag


logger = logging.getLogger(__name__)


DEFAULT_FORM_SEARCH_FIELD = {"name": "signIn"}


def _extract_message_from_box(box: Tag) -> str:
    """Extracts and concatenates message text from an HTML message box."""
    message = ""

    header = box.find("h4")
    if isinstance(header, Tag) and header.string:
        message += header.string.strip()

    for list_item in box.find_all("li"):
        if isinstance(list_item, Tag):
            list_entry = list_item.find("span")
            if isinstance(list_entry, Tag) and list_entry.string:
                message += " " + list_entry.string.strip()
    return message.strip()


class SoupPage:
    """Represents a parsed HTML page based on a httpx.Response.

    Parses the response text once into a BeautifulSoup instance and
    optionally logs detected error or warning messages.

    Args:
        resp: The httpx.Response object containing the HTML source.
    """

    def __init__(self, resp: httpx.Response) -> None:
        self.resp = resp
        self.soup = BeautifulSoup(resp.text, "html.parser")

    # ---------- Public API ----------

    def get_form_inputs(
        self, search_field: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Extracts input fields from a form on the page.

        Args:
            search_field: Optional dictionary to locate a specific form (e.g. {"name": "signIn"}).

        Returns:
            dict[str, str]: A dictionary of form input names and values.
                Hidden inputs include their actual values; others are empty strings.
        """
        form = self._find_form(search_field)

        inputs: dict[str, str] = {}
        for form_field in form.find_all("input"):
            name = form_field.get("name")
            if not name:
                continue
            value = ""
            if form_field.get("type") == "hidden":
                value = form_field.get("value", "")
            inputs[name] = value
        return inputs

    def get_next_action(
        self, search_field: dict[str, str] | None = None
    ) -> tuple[str, str]:
        """Extracts the HTTP method and action URL from the form.

        Args:
            search_field: Optional dictionary to locate a specific form (e.g. {"name": "signIn"}).

        Returns:
            A tuple (method, url) for the next request.

        Raises:
            ValueError: If method or action could not be extracted.
        """
        form = self._find_form(search_field)

        method = form.get("method", "GET")
        url = form.get("action")

        if not isinstance(method, str) or not isinstance(url, str):
            raise ValueError("Failed to extract form method or action URL.")
        return method, url

    def get_messages(self) -> dict[str, str]:
        """Extracts any known message boxes from the page.

        Returns:
            A dictionary that may contain 'error', 'warning', or 'aperror' messages.
        """
        messages: dict[str, str] = {}

        error_box = self.soup.find(id="auth-error-message-box")
        if isinstance(error_box, Tag):
            error_message = _extract_message_from_box(error_box)
            if error_message:
                messages["error"] = error_message

        warning_box = self.soup.find(id="auth-warning-message-box")
        if isinstance(warning_box, Tag):
            warning_message = _extract_message_from_box(warning_box)
            if warning_message:
                messages["warning"] = warning_message

        ap_error = self.soup.find(id="ap_error_page_message")
        if isinstance(ap_error, Tag):
            ap_error_message = ap_error.find(recursive=False, text=True)
            if isinstance(ap_error_message, NavigableString):
                messages["aperror"] = ap_error_message.strip()

        return messages

    def log_page_messages(self) -> None:
        messages = self.get_messages()
        if "error" in messages:
            logger.error("Error message: %s", messages["error"])
        if "warning" in messages:
            logger.warning("Warning message: %s", messages["warning"])
        if "aperror" in messages:
            logger.error("Error message: %s", messages["aperror"])

    # ---------- Internal Helpers ----------

    def _find_form(
        self, search_field: dict[str, str] | None, strict: bool = False
    ) -> Tag:
        """Finds a form on the page based on search criteria.

        Args:
            search_field: Optional dictionary specifying form attributes.
            strict: If True, disables fallback to default or broad search.

        Returns:
            The first matching form tag.

        Raises:
            ValueError: If no matching form is found.
        """
        if strict:
            if not search_field:
                raise ValueError("Strict mode requires explicit search criteria.")
            form = self.soup.find("form", search_field)
        else:
            criteria = search_field or DEFAULT_FORM_SEARCH_FIELD
            form = self.soup.find("form", criteria) or self.soup.find("form")

        if not isinstance(form, Tag):
            raise ValueError("No form found on page.")
        return form
