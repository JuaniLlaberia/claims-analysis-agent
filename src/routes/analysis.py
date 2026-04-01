from flask import request, jsonify, Blueprint

analysis_blueprint = Blueprint("analysis", __name__)

@analysis_blueprint.route("/article", methods=["POST"])
def analyze_article_endpoint():
    """
    Endpoint to analyze the claims/validity of a full article.

    Receives a news articles information under the labels: 'title', 'content'.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    request_json = request.get_json()
    if "title" not in request_json or "content" not in request_json:
        return jsonify({"error": "Missing title or content"}), 400

    

    return jsonify({"status": "ok"}), 200

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

    return jsonify({"status": "ok"}), 200