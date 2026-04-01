from langgraph.graph import StateGraph
from typing import TypedDict, Literal

from .models.claim import Claim

class State(TypedDict):
    analysis_type: Literal["article", "snippet"]
    # Base article types
    title: str = ""
    content: str = ""
    # Base snippet types
    snippet: str = ""
    # Analysis data
    claims: list[Claim] = []

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
        graph.add_node("validation_and_citation", self._validator)
        graph.add_node("output_formatter", self._output_formatter)
        # Add ARTICLE nodes
        graph.add_node("article_analyzer", self._article_analyzer_adapter)
        # Add SNIPPET nodes
        graph.add_node("snippet_analyzer", self._snippet_analyzer_adapter)
        
        # Add edges
        graph.add_edge("article_analyzer", "claims_router")
        graph.add_edge("snippet_analyzer", "claims_router")
        graph.add_edge("validation_and_citation", "output_formatter")

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
            self._route_by_present_claims,
            {
                "continue": "validation_and_citation",
                "end": "output_formatter"
            }
        )

        graph.set_entry_point("initial_router")
        graph.set_finish_point("output_formatter")

        return graph.compile()

    def _route_by_analysis_type(self, state: State) -> Literal["article", "snippet"]:
        """
        Router node that switches starting node based on analysis type.

        Args:
            state (State): Graph state.
        Returns:
            "article" | "snippet": Route to take based on analysis type.
        """
        return "article "if state["analysis_type"] == "article" else "snippet"

    def _route_by_present_claims(self, state: State) -> Literal["continue", "end"]:
        """
        Router node that validates if corpus has claims or not. In case of containing claims
        the workflow continues, else it ends.

        Args:
            state (State): Graph state.
        Returns:
            "continue" | "end": Route to take based on available claims quantity.
        """
        return "continue" if len(state["claims"]) >= 1 else "end"

    def _article_analyzer_adapter(self, state: State) -> dict[str, any]:
        """
        Handles execution of article analyzer sub-graph. The sub-graph internally performs multiple
        steps to analyze and extract the claims from the given article.

        Args:
            state (State): Graph state.
        Returns:
            dict[str, any]: Dictionary containing the properties to update in the global state.
        """

    def _snippet_analyzer_adapter(self, state: State) -> dict[str, any]:
        """
        Handles execution of snippet analyzer sub-graph. The sub-graph internally performs analysis and
        extraction of claims from snippet.
        
        Args:
            state (State): Graph state.
        Returns:
            dict[str, any]: Dictionary containing the properties to update in the global state.
        """

    def _validator(self, state: State) -> dict[str, any]:
        """
        Handles execution of the validation and citations sub-graph. The sub-graph internally
        verifies all provides claims and finds citations for each.
        
        Args:
            state (State): Graph state.
        Returns:
            dict[str, any]: Dictionary containing the properties to update in the global state.
        """

    def _output_formatter(self, state: State) -> dict[str, any]:
        """
        Formats final text output.

        Args:
            state (State): Graph state.
        Returns:
            dict[str, any]: Dictionary containing the properties to update in the global state.
        """

    def run(self) -> ...:
        """
        Runs Orquestrator workflows with all of it's sub-workflows.

        Returns:
            ...
        """
        initial_state = State(analysis_type=self.analysis_type)
        result = self.graph.invoke(initial_state)