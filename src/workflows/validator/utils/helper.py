from urllib.parse import urlparse

def name_from_url(url: str) -> str:
    """
    Extracts site name from URL.

    Args:
        url (str): Site's url.
    Returns:
        str: Site's name.
    """
    host = urlparse(url).netloc
    return host.replace("www.", "").split(".")[0].capitalize()