import requests
from sentence_transformers import SentenceTransformer, util

from src.tools.gfca.models.claim_review import ClaimReview
from src.tools.gfca.models.fact_check_result import FactCheckResult
from src.tools.gfca.utils.constants import RATING_MAP

class GFCAClient:
    """
    Google Fact Check Tools API client with:
    - Semantic similarity filtering
    - URL-level deduplication
    - Rating normalization
    """

    BASE_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

    def __init__(
        self,
        api_key: str = None,
        similarity_model: str = "paraphrase-multilingual-mpnet-base-v2",
        similarity_threshold: float = 0.35,
    ):
        """
        Args:
            api_key: Google Fact Check Tools API key.
            similarity_model: SentenceTransformer model for semantic filtering.
            similarity_threshold: Minimum cosine similarity to keep a result (0-1).
        """
        self.api_key = api_key
        if not self.api_key:
            raise ValueError(
                "No API key provided."
            )

        self.similarity_threshold = similarity_threshold    
        self.encoder = SentenceTransformer(similarity_model)

    def search(
        self,
        query: str,
        language_code: str = "en",
        max_age_days: int = 365 * 3,
        page_size: int = 10,
        publisher_filter: str = None) -> list[FactCheckResult]:
        """
        Search GFCA for fact-checked claims matching `query`.

        Args:
            query: The claim text to search for.
            language_code: BCP-47 code — "en", "es", "pt", etc.
            max_age_days: How far back to look. Default 3 years.
            page_size: Max raw results to fetch from GFCA before filtering.
            publisher_filter: Pin to a specific fact-checker site.

        Returns:
            Filtered, deduplicated, similarity-scored list of FactCheckResult.
            Empty list if nothing passes the similarity threshold → triggers fallback.
        """
        # Get GFCA raw results from API
        raw_results = self._fetch_gfca(query, language_code, max_age_days, page_size, publisher_filter)
        # Data preparation and filtering
        parsed = self._parse_results(raw=raw_results)
        scored = self._score_similarity(query=query, results=parsed)
        deduped = self._deduplicate_facts(results=scored)
        filtered = self._filte_by_similarity(results=deduped)

        return filtered

    def _fetch_gfca(
        self,
        query: str,
        language_code: str,
        max_age_days: int,
        page_size: int,
        publisher_filter: str | None) -> dict:
        """
        Raw HTTP call to the GFCA REST endpoint.
        
        Args:
            query: The claim text to search for.
            language_code: BCP-47 code — "en", "es", "pt", etc.
            max_age_days: How far back to look. Default 3 years.
            page_size: Max raw results to fetch from GFCA before filtering.
            publisher_filter: Pin to a specific fact-checker site.
        Returns:
            ...
        """
        params = {
            "query": query,
            "languageCode": language_code,
            "maxAgeDays": max_age_days,
            "pageSize": page_size,
            "key": self.api_key,
        }
        if publisher_filter:
            params["reviewPublisherSiteFilter"] = publisher_filter

        response = requests.get(self.BASE_URL, params=params)
        response.raise_for_status()

        return response.json()

    def _parse_results(self, raw: dict) -> list[FactCheckResult]:
        """
        Convert raw GFCA response into FactCheckResult objects.
        
        Args:
            ...
        Returns:
            ...
        """
        results = []
        for claim in raw.get("claims", []):
            reviews = [
                ClaimReview(
                    rating_raw=r.get("textualRating", ""),
                    rating_normalized=self._normalize_rating(r.get("textualRating", "")),
                    reviewer_name=r.get("publisher", {}).get("name", ""),
                    reviewer_site=r.get("publisher", {}).get("site", ""),
                    review_url=r.get("url", ""),
                    review_date=r.get("reviewDate", ""),
                    language=r.get("languageCode", ""),
                )
                for r in claim.get("claimReview", [])
            ]

            results.append(FactCheckResult(
                claim_text=claim.get("text", ""),
                claimant=claim.get("claimant", "Unknown"),
                claim_date=claim.get("claimDate", ""),
                similarity_score=0.0,
                reviews=reviews,
            ))

        return results

    def _score_similarity(self, query: str, results: list[FactCheckResult]) -> list[FactCheckResult]:
        """
        Compute cosine similarity between the query and each claim text.
        
        Args:
            results (list[FactCheckResult]): List of facts comming from gfca api.
        Returns:
            list[FactCheckResult]: Updated list of facts containing the similarity score
            compared against the original query (Sorted from higher to lower).
        """
        if not results:
            return []

        query_embedding = self.encoder.encode(query, convert_to_tensor=True)
        claim_texts = [r.claim_text for r in results]
        claim_embeddings = self.encoder.encode(claim_texts, convert_to_tensor=True)

        scores = util.cos_sim(query_embedding, claim_embeddings)[0]

        for result, score in zip(results, scores):
            result.similarity_score = round(score.item(), 4)

        return sorted(results, key=lambda r: r.similarity_score, reverse=True)

    def _deduplicate_facts(self, results: list[FactCheckResult]) -> list[FactCheckResult]:
        """
        Deduplicate by review URL so a single article with multiple claims doesn't inflate the evidence pool.

        Args:
            results (list[FactCheckResults]): List of facts containing all of it's data.
        Returns:
            list[FactCheckResult]: Deduped list of facts.
        """
        seen_urls: set[str] = set()

        deduped = []
        for result in results:
            unique_reviews = []

            for review in result.reviews:
                if review.review_url not in seen_urls:
                    seen_urls.add(review.review_url)
                    unique_reviews.append(review)

            if unique_reviews:
                result.reviews = unique_reviews
                deduped.append(result)

        return deduped

    def _filte_by_similarity(self, results: list[FactCheckResult]) -> list[FactCheckResult]:
        """
        Drop results below the similarity threshold.
        
        Args:
            results (list[FactCheckResults]): List of deduped facts.
        Returns:
            list[FactCheckResult]: List of filtered facts based on similarity threshold.
        """
        return [r for r in results if r.similarity_score >= self.similarity_threshold]

    def _normalize_rating(self, raw: str) -> str:
        """
        Map publisher-specific rating labels to a canonical set.

        Args:
            raw (str): Raw label assigned by published.
        Returns:
            str: Mapped label to normalized labels.
        """
        return RATING_MAP.get(raw.lower().strip(), "UNVERIFIED")