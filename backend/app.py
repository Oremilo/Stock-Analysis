import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from routes.auth_routes import auth_bp
from routes.stock_routes import stock_bp
from routes.market_routes import market_bp
from routes.stock_routes import risk_bp
from utils.db import connect_db

# Load environment variables
load_dotenv()

def create_app():
    # Initialize Flask app
    app = Flask(__name__)

    # Enable CORS with explicit configuration
    # CORS(app, resources={r"/*": {"origins": "*", 
    #                             "allow_headers": ["Content-Type", "Authorization"],
    #                             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]}})
    CORS(app, supports_credentials=True)
    # Add CORS headers to all responses
    # @app.after_request
    # def after_request(response):
    #     response.headers.add('Access-Control-Allow-Origin', '*')
    #     response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    #     response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    #     return response

    # Configure app settings
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", os.urandom(24)),
        DEBUG=os.getenv("FLASK_DEBUG", "False") == "True"
    )

    # Connect to database
    try:
        db = connect_db()
        app.config['DB'] = db
    except Exception as e:
        print(f"Database connection error: {e}")

    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(stock_bp, url_prefix="/stocks")
    app.register_blueprint(market_bp, url_prefix='/api/market')
    app.register_blueprint(risk_bp, url_prefix='/risk')

    @app.route('/')
    def home():
        return {'status': 'ok', 'message': 'Stock Analysis API is running'}

    # Add a route to check API status
    @app.route('/health')
    def health_check():
        return {'status': 'ok', 'version': '1.0.0'}

    return app

# Application factory pattern
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv('PORT', 5000))
    if os.getenv("FLASK_ENV", "development") == "production":
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        app.run(host='127.0.0.1', port=port, debug=True)