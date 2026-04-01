from flask import jsonify, Blueprint

health_blueprint = Blueprint("health", __name__)

@health_blueprint.route("/health", methods=["GET"])
def check_health_endpoint():
    """
    """
    return jsonify({"status": "healthy"}), 200
