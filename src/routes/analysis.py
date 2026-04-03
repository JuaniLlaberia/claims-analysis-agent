from flask import request, jsonify, Blueprint
from src.workflows.orquestrator.orquestrator import Orquestrator

analysis_blueprint = Blueprint("analysis", __name__)

@analysis_blueprint.route("/snippet", methods=["POST"])
def analyze_snippet_endpoint():
    """
    Endpoint to analyze the claims/validity of a snippet.

    Receives a text snippet under the label: 'snippet'.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    request_json = request.get_json()
    if "snippet" not in request_json:
        return jsonify({"error": "Missing snippet"}), 400

    if len(request_json["snippet"]) >= 500:
        return jsonify({"error": "Snippet is too long."}), 400

    try:
        orquestrator = Orquestrator(analysis_type="snippet")
        results = orquestrator.run(snippet=request_json["snippet"])

        serializable_results = []
        for r in results:
            if hasattr(r, "model_dump"):
                serializable_results.append(r.model_dump())
            else:
                serializable_results.append(r)

        return jsonify({"results": serializable_results}), 200
    except Exception as e:
        print(e)
        return jsonify({"error": "Analysis failed", "details": str(e)}), 500