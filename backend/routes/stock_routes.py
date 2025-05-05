import os
import logging
import numpy as np
import requests
import yfinance as yf
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from .sentiment_analysis import fetch_and_analyze_stock_sentiment
from .risk_analysis import fetch_risk_results
from .prediction_analysis import stock_price_predictor, train_or_load_model

stock_bp = Blueprint('stock', __name__)
risk_bp = Blueprint('risk', __name__)
portfolio = ['TCS.NS', 'ITC.NS', 'ZOMATO.NS', 'TATASTEEL.NS', 'INFY.NS', 
            'RELIANCE.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'SBIN.NS']

# Financial Modeling Prep API Configuration
# Use environment variable instead of hardcoding
FMP_API_KEY = os.getenv('FMP_API_KEY', 'cRDdT2E7PbKeYPsVST8kmnUBJwof2sTa')
BASE_URL = 'https://financialmodelingprep.com/api'

def search_stocks(query):
    try:
        search_url = f"{BASE_URL}/v3/search-ticker"
        params = {
            'query': query,
            'limit': 10,
            'apikey': FMP_API_KEY
        }
        
        response = requests.get(search_url, params=params)
        
        # Add better error handling
        if response.status_code == 401:
            logging.error("API Authentication failed: Invalid API key")
            return {"error": "API authentication failed"}
        
        response.raise_for_status()
        data = response.json()
        
        return data if data else []
    
    except requests.exceptions.RequestException as e:
        logging.error(f"API request error in stock search: {e}")
        return {"error": f"API request error: {str(e)}"}
    except Exception as e:
        logging.error(f"Error in stock search: {e}")
        return {"error": f"Unexpected error: {str(e)}"}

@stock_bp.route('/search', methods=['GET'])
def search_stocks_route():
    query = request.args.get('name', '').strip()
    
    if not query:
        return jsonify({"error": "Please provide a valid stock name or symbol"}), 400
    
    try:
        search_results = search_stocks(query)
        
        # Check if we got an error response
        if isinstance(search_results, dict) and "error" in search_results:
            return jsonify(search_results), 500
            
        return jsonify(search_results)
    
    except Exception as e:
        logging.error(f"Unexpected error in search route: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500

def get_stock_details(symbol):
    try:
        # Initialize default response structure with safe defaults
        stock_details = {
            'current_quote': {
                'price': 0.0,
                'change': 0.0,
                'change_percent': 0.0,
            },
            'profile': {
                'name': 'Unknown',
                'symbol': symbol,
                'industry': 'Unknown',
                'sector': 'Unknown',
                'country': 'Unknown',
                'website': '#',
            },
            'historical_prices': [],
            'news': [],
            'sentiment': None,
            'risk_analysis': None,
            'price_prediction': None
        }

        # Fetch stock information using yfinance
        try:
            stock = yf.Ticker(symbol)
            
            # Company Profile from yfinance
            if hasattr(stock, 'info') and stock.info:
                stock_details['profile'].update({
                    'name': stock.info.get('longName', 'Unknown'),
                    'industry': stock.info.get('industry', 'Unknown'),
                    'sector': stock.info.get('sector', 'Unknown'),
                    'country': stock.info.get('country', 'Unknown'),
                    'website': stock.info.get('website', '#'),
                })

            # Current Quote from yfinance
            current_price = stock.history(period='1d')
            if not current_price.empty:
                close_price = current_price['Close'].iloc[-1]
                previous_close = current_price['Close'].iloc[0]
                change = close_price - previous_close
                change_percent = (change / previous_close) * 100

                stock_details['current_quote'] = {
                    'price': float(close_price),
                    'change': float(change),
                    'change_percent': float(change_percent)
                }

            # Historical Prices (Last 365 days) from yfinance
            historical_data = stock.history(period='1y')
            if not historical_data.empty:
                stock_details['historical_prices'] = [
                    {
                        'date': idx.strftime('%Y-%m-%d'),
                        'close': float(row['Close'])
                    }
                    for idx, row in historical_data.iterrows()
                ]
        except Exception as e:
            logging.error(f"YFinance error: {e}")
            # Continue with defaults rather than failing completely
        
        # News from Financial Modeling Prep with better error handling
        try:
            news_url = f"{BASE_URL}/v3/stock_news"
            news_response = requests.get(news_url, params={
                'tickers': symbol,
                'limit': 5,
                'apikey': FMP_API_KEY
            })
            
            if news_response.status_code == 401:
                logging.error("FMP API Authentication failed when fetching news")
                # Continue with empty news
            else:
                news_response.raise_for_status()
                news_data = news_response.json()

                if news_data and isinstance(news_data, list):
                    stock_details['news'] = [
                        {
                            'title': article.get('title', ''),
                            'publisher': article.get('site', ''),
                            'link': article.get('url', ''),
                            'published_at': article.get('publishedDate', '')
                        }
                        for article in news_data[:5]
                    ]
        except requests.exceptions.RequestException as e:
            logging.error(f"News API request error: {e}")
            # Continue with empty news
        except Exception as e:
            logging.error(f"News processing error: {e}")
            # Continue with empty news

        # Fetch sentiment analysis 
        try:
            sentiment_data = fetch_and_analyze_stock_sentiment(symbol)
            
            # Combine existing news with sentiment news if needed
            existing_news = stock_details.get('news', [])
            sentiment_news = sentiment_data.get('news', [])
            
            # Merge news, prioritizing sentiment news but keeping existing if sentiment news is empty
            stock_details['news'] = sentiment_news if sentiment_news else existing_news
            
            stock_details['sentiment'] = {
                'overall_prediction': sentiment_data.get('overall_prediction', None)
            }
        except Exception as e:
            logging.error(f"Error fetching sentiment: {e}")
            stock_details['sentiment'] = None
            
        # Fetch Risk Analysis
        try:
            # Use requests to make an internal API call
            risk_response = requests.get(f"{request.host_url}risk/analyze/{symbol}")
            if risk_response.ok:
                stock_details['risk_analysis'] = risk_response.json().get('risk_analysis')
            else:
                logging.warning(f"Risk analysis returned status code {risk_response.status_code}")
                stock_details['risk_analysis'] = {
                    'risk_level': 'N/A',
                    'volatility': 'N/A',
                    'daily_return': 'N/A',
                    'current_price': 'N/A',
                    'latest_close': None,
                    'trend': 'N/A'
                }
        except Exception as e:
            logging.error(f"Error fetching risk analysis: {e}")
            stock_details['risk_analysis'] = {
                'risk_level': 'N/A',
                'volatility': 'N/A',
                'daily_return': 'N/A',
                'current_price': 'N/A',
                'latest_close': None,
                'trend': 'N/A'
            }
            
        # Price Prediction
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            prediction_result = stock_price_predictor(symbol, start_date, end_date)
            
            if 'error' not in prediction_result:
                stock_details['price_prediction'] = {
                    'predicted_price': prediction_result.get('predicted_price'),
                    'last_close_price': prediction_result.get('last_close_price'),
                    'price_change': prediction_result.get('price_change'),
                    'prediction_confidence': prediction_result.get('prediction_confidence', 70),
                    'prediction_direction': prediction_result.get('prediction_direction')
                }
            else:
                logging.error(f"Price prediction error: {prediction_result['error']}")
                stock_details['price_prediction'] = None

        except Exception as e:
            logging.error(f"Error in price prediction: {e}")
            stock_details['price_prediction'] = None

        return stock_details

    except Exception as e:
        logging.error(f"Comprehensive error fetching stock details: {e}")
        # Instead of returning None, return a minimal stock details object
        # This prevents 404 errors when the API calls fail
        return {
            'current_quote': {'price': 0.0, 'change': 0.0, 'change_percent': 0.0},
            'profile': {'name': 'Unknown', 'symbol': symbol},
            'historical_prices': [],
            'news': [],
            'error': f"Failed to retrieve complete stock data: {str(e)}"
        }
    
@stock_bp.route('/details/<symbol>', methods=['GET'])
def stock_details_route(symbol):
    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400

    try:
        details = get_stock_details(symbol)
        
        # Check if there was an error but we still have some data
        if details and 'error' in details:
            return jsonify(details), 200  # Return partial data with error message
        
        # If get_stock_details returned None (should not happen with improved error handling)
        if details is None:
            return jsonify({"error": "Could not retrieve stock details"}), 500
            
        return jsonify(details)

    except Exception as e:
        logging.error(f"Error in stock details route: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500
        
@risk_bp.route('/analyze/<symbol>', methods=['GET'])
def analyze_stock_risk(symbol):
    try:
        if not symbol:
            return jsonify({"error": "Symbol is required"}), 400
        
        # Attempt to get risk analysis results
        results = fetch_risk_results(symbol, portfolio)
        
        # Check for error in results
        if 'error' in results:
            return jsonify({
                "risk_analysis": {
                    "error": results['error'],
                    "risk_level": 'N/A',
                    "volatility": 'N/A',
                    "daily_return": 'N/A',
                    "current_price": 'N/A',
                    "trend": 'N/A',
                    "latest_close": None
                }
            }), 400
        
        # Return successful risk analysis
        return jsonify({
            "risk_analysis": {
                "risk_level": results.get('risk_level', 'N/A'),
                "volatility": results.get('volatility', 'N/A'),
                "daily_return": results.get('daily_return', 'N/A'),
                "current_price": results.get('current_price', 'N/A'),
                "trend": results.get('trend', 'N/A'),
                "latest_close": results.get('latest_close', None)
            }
        })
        
    except Exception as e:
        logging.error(f"Comprehensive error analyzing risk for {symbol}: {str(e)}")
        return jsonify({
            "risk_analysis": {
                "error": "Failed to analyze stock risk",
                "risk_level": 'N/A',
                "volatility": 'N/A',
                "daily_return": 'N/A',
                "current_price": 'N/A',
                "trend": 'N/A',
                "latest_close": None
            }
        }), 500