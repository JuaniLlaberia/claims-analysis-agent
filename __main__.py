from flask import Flask

from src.routes.analysis import analysis_blueprint
from src.routes.health import health_blueprint

def create_app() -> Flask:
    """
    Creates instance of Flask API

    Returns:
        Flask: Flask server instance
    """
    app = Flask(__name__)
    app.register_blueprint(analysis_blueprint)
    app.register_blueprint(health_blueprint)

    return app

def main():
    """
    Main entry point for the claims analysis API
    """
    app = create_app()
    app.run(host="0.0.0.0", debug=True, port=5001)
    

if __name__ == "__main__":
    main()
