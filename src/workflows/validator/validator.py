import os
from tavily import TavilyClient
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal

from src.llm.gemini import Gemini
from src.workflows.orquestrator.models.claim import Claim
from src.workflows.validator.models.source import Source
from src.tools.gfca.gfca import GFCAClient
from src.tools.gfca.models.fact_check_result import FactCheckResult
from .models.output import ValidatorOutput, CoverageAssessment, CitationsOutput
from .utils.prompts import VALIDATOR_PROMPT, CITATIONS_PROMPT
from .utils.helper import name_from_url, detect_language

class State(TypedDict):
    claim: Claim
    evidence_source: Literal["fgca", "web_search"]
    # FGCA data
    fgca_results: list[FactCheckResult]
    # Web search data
    web_search_results: list[dict[str, any]]

    sources: list[Source]
    evidence_summary: str
    coverage: CoverageAssessment
    insufficient_evidence: bool

class Validator:
    """
    Claim validator workflow that handles information search, validation and citations.

    Attributes:
        fgca_client (GFCAClient): Instance of FGCA to call the api for fact checking results.
        tavily_cleint (TavilyClient): Instance of Tavily to perform web search.
        llm (Gemini): Instance of Gemini LLM that contains grounding tool.
        graph (StateGraph): Workflow's graph.
    """
    def __init__(self):
        """
        Initialize Validator workflow class
        """
        # Intances of search clients
        self.fgca_client = GFCAClient(api_key=os.getenv("GOOGLE_FACTCHECK_API_KEY"))
        self.tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        # LLM + grounding
        self.llm = Gemini(model_name=os.getenv("GEMINI_MODEL_SNIPPET_EXTRACTION"))

        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        Builds langgraph workflow graph.

        Returns:
            StateGraph: Instance of langgraph graph.
        """
        graph = StateGraph(State)

        graph.add_node("fgca_claim_retrieval", self._claim_info_retrieval_node)
        graph.add_node("claim_web_search", self._claim_info_web_search_node)
        graph.add_node("gfca_router", lambda state: state)
        graph.add_node("web_search_router", lambda state: state)
        graph.add_node("evidence_router", lambda state: state)
        graph.add_node("validation", self._validation_node)
        graph.add_node("citation", self._citations_node)

        graph.set_entry_point("fgca_claim_retrieval")
        graph.add_edge("fgca_claim_retrieval", "gfca_router")
        graph.add_conditional_edges(
            "gfca_router",
            self._route_by_gfca,
            {
                "continue": "validation",
                "fallback": "claim_web_search"
            }
        )
        graph.add_edge("claim_web_search", "web_search_router")
        graph.add_conditional_edges(
            "web_search_router",
            self._route_by_web_search,
            {
                "continue": "validation",
                "end": END
            }
        )
        graph.add_edge("validation", "evidence_router")
        graph.add_conditional_edges(
            "evidence_router",
            self._route_by_evidence,
            {
                "continue": "citation",
                "end": END
            }
        )
        graph.set_finish_point("citation")

        return graph.compile()
    
    def _route_by_gfca(self, state: State) -> Literal["continue", "fallback"]:
        """
        Routes graph based on GFCA results.

        Args:
            state (State): Graph state.
        Returns:
            'continue' | 'fallback': Route label based on fgca results quantity.
        """
        return "continue" if len(state["fgca_results"]) >= 1 else "fallback"

    def _route_by_web_search(self, state: State) -> Literal["continue", "end"]:
        """
        Routes graph based on web search results.

        Args:
            state (State): Graph state.
        Returns:
            'continue' | 'end': Route label based on web search results quantity.
        """
        # Always continue to validation so it can assess insufficient evidence
        return "continue"

    def _route_by_evidence(self, state: State) -> Literal["continue", "end"]:
        """
        Routes graph based on evidence presence.
        
        Args:
            state (State): Graph state.
        Returns:
            'continue' | 'end': Route label based on evidence presence.
        """
        return "end" if state["insufficient_evidence"] else "continue"

    def _claim_info_retrieval_node(self, state: State) -> dict[str, any]:
        """
        Performs claim search using FGCA API.

        Args:
            state (State): Graph state.
        Returns:
            dict[str, any]: Dictionary containing the properties to update in the state.
        """
        language = detect_language(text=state["claim"].text)

        results = self.fgca_client.search(
            query=state["claim"].text,
            language_code=language
        )

        return {
            "fgca_results": results,
            "evidence_source": "fgca"
        }

    def _claim_info_web_search_node(self, state: State) -> dict[str, any]:
        """
        Performs claim search using web search (Tavily), as fallback of FGCA.

        Args:
            state (State): Graph state.
        Returns:
            dict[str, any]: Dictionary containing the properties to update in the state.
        """
        results = self.tavily_client.search(
            query=state["claim"].text,
            search_depth="advanced",
            max_results=5)

        evidence = [
            {"url": r["url"], "title": r["title"], "content": r["content"]}
            for r in results["results"]
        ]

        return {
            "web_search_results": evidence,
            "evidence_source": "web_search",
        }
    
    def _validation_node(self, state: State) -> dict[str, any]:
        """
        Handles the validation of the fgca/web retrieved information about claim.

        Args:
            state (State): Graph state.
        Returns:
            dict[str, any]: Dictionary containing the properties to update in the state.
        """
        if state["evidence_source"] == "fgca":
            evidence_text = "\n\n".join([
                f"Source {i+1}:\n"
                f"URL: {result.reviews[0].review_url}\n"
                f"Content: {result.claim_text} — rated '{result.reviews[0].rating_normalized}' by {result.reviews[0].reviewer_name}"
                for i, result in enumerate(state["fgca_results"])
                if result.reviews
            ])
        else:
            evidence_text = "\n\n".join([
                f"Source {i+1}:\n"
                f"URL: {r['url']}\n"
                f"Content: {r['content']}"
                for i, r in enumerate(state["web_search_results"])
            ])
        
        # If no evidence found, mark as insufficient
        if not evidence_text.strip():
            return {
                "evidence_summary": "No sources or evidence could be found for this claim.",
                "coverage": CoverageAssessment(
                    source_count=0,
                    sources_agree=None,
                    evidence_directly_addresses_claim=False,
                    oldest_source_date=None,
                    newest_source_date=None
                ),
                "insufficient_evidence": True,
            }
                
        response = self.llm.invoke_model_grounded(prompt=VALIDATOR_PROMPT,
                                                  output_schema=ValidatorOutput,
                                                  input={
                                                      "claim": state["claim"].text,
                                                      "evidence": evidence_text
                                                  })
    
        if isinstance(response, ValidatorOutput):
            data = {
                "evidence_summary": response.evidence_summary,
                "coverage": response.coverage,
                "insufficient_evidence": response.insufficient_evidence,
            }
        else:
            data = {
                "evidence_summary": response.get("evidence_summary", ""),
                "coverage": response.get("coverage", {}),
                "insufficient_evidence": response.get("insufficient_evidence", False),
            }

        return {**data}

    def _citations_node(self, state: State) -> dict[str, any]:
        """
        Extracts relevant excerpts from evidence sources and builds the final Claim object to return to the parent graph.

        Args:
            state (State): Graph state.
        Returns:
            dict[str, any]: Dictionary containing the properties to update in the state.
        """
        if state["evidence_source"] == "fgca":
            sources_text = "\n\n".join([
                f"Source {i+1}:\n"
                f"URL: {result.reviews[0].review_url}\n"
                f"Content: {result.claim_text} — rated '{result.reviews[0].rating_normalized}' by {result.reviews[0].reviewer_name}"
                for i, result in enumerate(state["fgca_results"])
                if result.reviews
            ])
        else:
            sources_text = "\n\n".join([
                f"Source {i+1}:\n"
                f"URL: {r['url']}\n"
                f"Content: {r['content']}"
                for i, r in enumerate(state["web_search_results"])
            ])

        response = self.llm.invoke_model(
            prompt=CITATIONS_PROMPT,
            output_schema=CitationsOutput,
            input={
                "claim": state["claim"].text,
                "evidence_summary": state["evidence_summary"],
                "sources": sources_text,
            }
        )

        if isinstance(response, CitationsOutput):
            sources = [
                Source(
                    url=s.url,
                    name=name_from_url(s.url),
                    fragments=s.fragments,
                )
                for s in response.sources
            ]
        else:
            sources = [
                Source(
                    url=s.get("url", ""),
                    name=s.get("name") or name_from_url(s.get("url", "")),
                    fragments=s.get("fragments", []),
                )
                for s in response.get("sources", [])
            ]

        completed_claim = state["claim"].model_copy(update={
            "evidence_found": not state["insufficient_evidence"],
            "sources": sources,
        })

        return {"claim": completed_claim}

    def run(self, claim: Claim) -> Claim:
        """
        Runs the Validator workflow's graph.

        Args:
            claim (Claim): Claim to be search and get citations.
        Returns:
            Claim: Claim with evidence and citations information filled.
        """
        initial_state = State(
            claim=claim,
            evidence_source="fgca",
            fgca_results=[],
            web_search_results=[],
            evidence_summary="",
            coverage=None,
            insufficient_evidence=False
        )

        results = self.graph.invoke(initial_state)

        return {
            "claim": results["claim"],
            "evidence_summary": results["evidence_summary"],
            "coverage": results["coverage"],
            "insufficient_evidence": results["insufficient_evidence"],
        }