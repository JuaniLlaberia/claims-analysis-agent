import os
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal

from src.workflows.orquestrator.models.claim import Claim
from src.llm.gemini import Gemini
from .models.output import SnippetAnalysisOutput, ClaimsNormalizationOutput
from .utils.prompts import SNIPPET_ANALYSIS_PROMPT, CLAIMS_NORMALIZATION_PROMPT

class State(TypedDict):
    snippet: str = ""
    raw_claims: list[str] = []
    claims: list[Claim] = []

class SnippetAnalyzer:
    """
    Snippet Analyzer workflow.

    Attributes:
        llm (Gemini): Gemini model instance.
        graph (StateGraph): Workflow's graph.
    """
    def __init__(self):
        """
        Initialize SnippetAnalyzer workflow class.
        """
        self.llm = Gemini(model_name=os.getenv("GEMINI_MODEL_SNIPPET_EXTRACTION"))
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        Builds langgraph workflow graph.

        Returns:
            StateGraph: Instance of langgraph graph.
        """
        graph = StateGraph(State)

        graph.add_node("interpret_node", self._interpret_snippet)
        graph.add_node("normalization_node", self._normalize_claims)
        graph.add_node("claims_router", lambda state: state)

        graph.set_entry_point("interpret_node")
        
        graph.add_edge("interpret_node", "claims_router")
        
        graph.add_conditional_edges(
            "claims_router",
            self._route_by_claims_quantity,
            {
                "continue": "normalization_node",
                "end": END
            }
        )

        graph.set_finish_point("normalization_node")

        return graph.compile()

    def _interpret_snippet(self, state: State) -> dict[str, any]:
        """
        Handles the analysis of snippets and tries to extract possible claims.

        Args:
            state (State): Graph state.
        Returns:
            dict[str, any]: Dictionary containing the properties to update in the state.
        """
        response = self.llm.invoke_model(SNIPPET_ANALYSIS_PROMPT, 
                                       output_schema=SnippetAnalysisOutput,
                                       input={"snippet": state["snippet"]})
        
        if isinstance(response, SnippetAnalysisOutput):
            data = {
                "claims": response.claims,
            }
        else:
            response_data = response.model_dump()
            data = {
                "claims": response_data.get("claims"),
            }

        return {"raw_claims": data["claims"]}

    def _route_by_claims_quantity(self, state: State) -> Literal["continue", "end"]:
        """
        Router node to validate quantity of extracted claims.

        Args:
            state (State): Graph state.
        Returns:
            'continue' | 'end': Route label based on claim quantity.
        """
        return "continue" if len(state["raw_claims"]) > 0 else "end"

    def _normalize_claims(self, state: State) -> dict[str, any]:
        """
        Handles claims normalization and string preparation to be a 'Claim' object.

        Args:
            state (State): Graph state.
        Returns:
            dict[str, any]: Dictionary containing the properties to update in the state.
        """
        response = self.llm.invoke_model(CLAIMS_NORMALIZATION_PROMPT, 
                                       output_schema=ClaimsNormalizationOutput,
                                       input={"raw_claims": state["raw_claims"]})
        
        if isinstance(response, ClaimsNormalizationOutput):
            data = {
                "claims": response.claims,
            }
        else:
            response_data = response.model_dump()
            data = {
                "claims": response_data.get("claims"),
            }

        return {"claims": [Claim(text=claim,
                                 evidence_found=False,
                                 sources=[]) for claim in data["claims"]]}

    def run(self, snippet: str) -> list[Claim]:
        """
        Runs snippet analyzer graph.

        Args:
            snippet (str): Text snippet to analyze.
        Returns:
            ...
        """
        initial_state = State(
            snippet=snippet,
            raw_claims=[],
            claims=[]
        )

        results = self.graph.invoke(initial_state)

        return results["claims"]