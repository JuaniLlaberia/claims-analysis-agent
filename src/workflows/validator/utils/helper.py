from urllib.parse import urlparse
from langdetect import detect, LangDetectException

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

def detect_language(text: str, fallback: str = "en") -> str:
    """
    Detects the language from the given text and it fallbacks to english in case something goes wrong.
    
    Args:
        text (str): Text to detect language.
        fallback (str): Fallback langauge. Default = 'en'.
    Returns:
        str: BCP-47 code — "en", "es", "pt", etc.
    """
    try:
        return detect(text)
    except LangDetectException:
        return fallback