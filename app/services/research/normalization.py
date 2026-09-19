import hashlib
import json
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

class ResearchNormalizationService:
    """
    Normalizes and deduplicates incoming research data.
    """

    def normalize_url(self, url: str) -> str:
        """
        Normalizes a URL by parsing it, lowercasing the scheme and netloc,
        and sorting query parameters.
        """
        if not url:
            return ""
        try:
            parsed = urlparse(url)
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            path = parsed.path
            
            # Sort query parameters for consistency
            if parsed.query:
                query_list = parse_qsl(parsed.query, keep_blank_values=True)
                query_list.sort()
                query = urlencode(query_list)
            else:
                query = ""
                
            normalized = urlunparse((scheme, netloc, path, parsed.params, query, ""))
            return normalized
        except Exception:
            # If parsing fails, return original or stripped
            return url.strip()

    def generate_fingerprint(self, content: str, url: str = None) -> str:
        """
        Generates a SHA-256 fingerprint from the normalized URL and text content.
        Used to deduplicate evidence.
        """
        components = []
        if url:
            normalized_url = self.normalize_url(url)
            if normalized_url:
                components.append(normalized_url)
                
        if content:
            # Strip whitespace and normalize
            normalized_content = " ".join(content.split())
            components.append(normalized_content)
            
        raw = "|".join(components)
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()
