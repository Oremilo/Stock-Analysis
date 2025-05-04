import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from routes.auth_routes import auth_bp
from routes.stock_routes import stock_bp, risk_bp
from routes.market_routes import market_bp
from utils.db import connect_db

# Load environment variables from .env
load_dotenv()

def create_app():
    app = Flask(__name__)

    # Enable CORS for all origins
    CORS(app)

    # App configuration
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", os.urandom(24)),
        DEBUG=os.getenv("FLASK_DEBUG", "False") == "True"
    )

    # Connect to the database
    try:
        db = connect_db()
        app.config['DB'] = db
    except Exception as e:
        print(f"Database connection error: {e}")

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(stock_bp, url_prefix="/stocks")
    app.register_blueprint(market_bp, url_prefix="/api/market")
    app.register_blueprint(risk_bp, url_prefix="/risk")

    return app

# Create app instance
app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=os.getenv("FLASK_DEBUG", "False") == "True"
    )
