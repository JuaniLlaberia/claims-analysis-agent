from flask import Flask
from dotenv import load_dotenv
import os
import sys

from src.routes.analysis import analysis_blueprint
from src.routes.health import health_blueprint

load_dotenv()

def validate_environment():
    """
    Validates that all required environment variables are set.
    Exits the application if any are missing.
    """
    required_vars = [
        "GOOGLE_GEMINI_KEY",
        "GEMINI_MODEL_SNIPPET_EXTRACTION",
        "GEMINI_MODEL_VALIDATION",
        "GOOGLE_FACTCHECK_API_KEY",
        "TAVILY_API_KEY",
        "PORT"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in your .env file or environment.")
        sys.exit(1)

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
    validate_environment()
    app = create_app()
    app.run(host="0.0.0.0", debug=True, port=5001)
    

if __name__ == "__main__":
    main()
    main()