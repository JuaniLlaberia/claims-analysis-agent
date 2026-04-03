from langgraph.graph import StateGraph, END
from langgraph.types import Send
from typing import TypedDict, Literal, Annotated
from operator import add

from src.workflows.validator.validator import Validator
from .models.claim import Claim, AnalyzedClaim
from src.workflows.snippet_analyzer.snippet_analyzer import SnippetAnalyzer

class State(TypedDict):
    analysis_type: Literal["article", "snippet"]
    # Base article types
    title: str = ""
    content: str = ""
    # Base snippet types
    snippet: str = ""
    # Analysis data
    claims: list[Claim] = []
    analyzed_claims: Annotated[list[AnalyzedClaim], add]

class Orquestrator:
    """
    Workflow for claims analysis from two different sources (article or snippet).

    Attributes:
        analysis_type ('article' | 'snippet'): Whether the orquestrator is running for a full article or for a snippet.
        graph (StateGraph): Workflow's graph.
    """ 
    def __init__(self, analysis_type: Literal["article", "snippet"]):
        """
        Initialices Orquestrator workflow class.

        Args:
            analysis_type ('article' | 'snippet'): Whether the orquestrator is running for a full article or for a snippet.
        """
        self.analysis_type = analysis_type
        self.validator = Validator()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        Builds langgraph workflow graph.

        Returns:
            StateGraph: Instance of langgraph graph.
        """
        graph = StateGraph(State)

        # Add GLOBAL nodes
        graph.add_node("initial_router", lambda state: state)
        graph.add_node("claims_router", lambda state: state)
        graph.add_node("validation_and_citation", self._validator_node)
        # Add ARTICLE nodes
        graph.add_node("article_analyzer", self._article_analyzer_adapter_node)
        # Add SNIPPET nodes
        graph.add_node("snippet_analyzer", self._snippet_analyzer_adapter_node)
        
        # Add edges
        graph.add_edge("article_analyzer", "claims_router")
        graph.add_edge("snippet_analyzer", "claims_router")

        # Conditionals
        graph.add_conditional_edges(
            "initial_router",
            self._route_by_analysis_type,
            {
                "article": "article_analyzer",
                "snippet": "snippet_analyzer"
            }
        )

        graph.add_conditional_edges(
            "claims_router",
            self._route_or_assign_workers,
            {
                "end": END
            }
        )

        graph.set_entry_point("initial_router")
        graph.set_finish_point("validation_and_citation")

        return graph.compile()

    def _route_by_analysis_type(self, state: State) -> Literal["article", "snippet"]:
        """
        Router node that switches starting node based on analysis type.

        Args:
            state (State): Graph state.
        Returns:
            "article" | "snippet": Route to take based on analysis type.
        """
        return "article" if state["analysis_type"] == "article" else "snippet"



    def _article_analyzer_adapter_node(self, state: State) -> dict[str, any]:
        """
        Handles execution of article analyzer sub-graph. The sub-graph internally performs multiple
        steps to analyze and extract the claims from the given article.

        Args:
            state (State): Graph state.
        Returns:
            dict[str, any]: Dictionary containing the properties to update in the global state.
        """

        return state

    def _snippet_analyzer_adapter_node(self, state: State) -> dict[str, any]:
        """
        Handles execution of snippet analyzer sub-graph. The sub-graph internally performs analysis and
        extraction of claims from snippet.
        
        Args:
            state (State): Graph state.
        Returns:
            dict[str, any]: Dictionary containing the properties to update in the global state.
        """

        snippet_analyzer = SnippetAnalyzer()
        extracted_claims = snippet_analyzer.run(snippet=state["snippet"])

        return {
            "claims": extracted_claims
        }
    
    def _route_or_assign_workers(self, state: State):
        """
        Routes to end if no claims, otherwise assigns parallel validator workers for each claim.
        """
        if len(state["claims"]) == 0:
            return "end"
        return [Send("validation_and_citation", {"claim": claim}) for claim in state["claims"]]

    def _validator_node(self, state: dict[str, any]) -> dict[str, any]:
        """
        Handles execution of the validation and citations sub-graph for a single claim. The sub-graph internally
        verifies the claim and finds citations for it.
        
        Args:
            state (dict): Partial state containing a single claim.
        Returns:
            dict[str, any]: Dictionary containing the analyzed claim to add to global state.
        """
        claim = state["claim"]
        validator_result_dict = self.validator.run(claim)
        validator_result = AnalyzedClaim(**validator_result_dict)

        return {"analyzed_claims": [validator_result]}

    def run(self, snippet: str | None = "") -> list[AnalyzedClaim]:
        """
        Runs Orquestrator workflows with all of it's sub-workflows.

        Returns:
            list[AnalyzedClaim]: List of analyzed claims contaning information about the sources, evidence and it's analysis.
        """
        initial_state = State(
            analysis_type=self.analysis_type,
            snippet=snippet,
            title="",
            content="",
            claims=[],
            analyzed_claims=[]
        )

        results = self.graph.invoke(initial_state)
        return results["analyzed_claims"]