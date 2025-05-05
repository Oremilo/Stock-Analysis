import os
import logging
import numpy as np
import requests
import yfinance as yf
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, timedelta
from .sentiment_analysis import fetch_and_analyze_stock_sentiment
from .risk_analysis import fetch_risk_results
from .prediction_analysis import stock_price_predictor, train_or_load_model

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

stock_bp = Blueprint('stock', __name__)
risk_bp = Blueprint('risk', __name__)
portfolio = ['TCS.NS', 'ITC.NS', 'ZOMATO.NS', 'TATASTEEL.NS', 'INFY.NS', 
            'RELIANCE.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'SBIN.NS']

# Financial Modeling Prep API Configuration
FMP_API_KEY = os.getenv('FMP_API_KEY', '')
BASE_URL = 'https://financialmodelingprep.com/api'

def search_stocks(query):
    try:
        # Log that we're starting the search
        logger.info(f"Searching for stocks matching: {query}")
        
        # Check if API key is available
        if not FMP_API_KEY:
            logger.error("FMP_API_KEY is not set or empty")
            return {"error": "API key not configured"}
            
        search_url = f"{BASE_URL}/v3/search-ticker"
        params = {
            'query': query,
            'limit': 10,
            'apikey': FMP_API_KEY
        }
        
        # Log the URL we're requesting (without API key)
        logger.info(f"Making request to: {search_url} with query: {query}")
        
        response = requests.get(search_url, params=params, timeout=10)
        
        # Handle common error codes
        if response.status_code == 401:
            logger.error("API Authentication failed: Invalid API key")
            return {"error": "API authentication failed. Check your API key."}
        elif response.status_code == 429:
            logger.error("API rate limit exceeded")
            return {"error": "API rate limit exceeded. Try again later."}
        elif response.status_code != 200:
            logger.error(f"API request failed with status code {response.status_code}")
            return {"error": f"API request failed with status code {response.status_code}"}
        
        data = response.json()
        logger.info(f"Search returned {len(data) if isinstance(data, list) else 0} results")
        
        return data if data else []
    
    except requests.exceptions.Timeout:
        logger.error("API request timed out")
        return {"error": "API request timed out. Try again later."}
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {e}")
        return {"error": f"API request error. Please try again."}
    except Exception as e:
        logger.error(f"Unexpected error in search: {e}")
        return {"error": f"An unexpected error occurred"}

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
        logger.exception(f"Error in search route: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500

def get_stock_details(symbol):
    try:
        logger.info(f"Fetching stock details for {symbol}")
        
        # Initialize default response structure with safe defaults
        stock_details = {
            'current_quote': {
                'price': 0.0,
                'change': 0.0,
                'change_percent': 0.0,
            },
            'profile': {
                'name': symbol,  # Use symbol as default name
                'symbol': symbol,
                'industry': 'N/A',
                'sector': 'N/A',
                'country': 'N/A',
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
            logger.info(f"Fetching yfinance data for {symbol}")
            stock = yf.Ticker(symbol)
            
            # Company Profile from yfinance
            if hasattr(stock, 'info') and stock.info:
                stock_details['profile'].update({
                    'name': stock.info.get('longName', symbol),
                    'industry': stock.info.get('industry', 'N/A'),
                    'sector': stock.info.get('sector', 'N/A'),
                    'country': stock.info.get('country', 'N/A'),
                    'website': stock.info.get('website', '#'),
                })
                logger.info(f"Retrieved profile data for {symbol}")
            else:
                logger.warning(f"No info attribute or empty info for {symbol}")

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
                logger.info(f"Retrieved current price data for {symbol}")
            else:
                logger.warning(f"Empty current price data for {symbol}")

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
                logger.info(f"Retrieved historical data for {symbol}: {len(stock_details['historical_prices'])} data points")
            else:
                logger.warning(f"Empty historical data for {symbol}")
                
        except Exception as e:
            logger.error(f"YFinance error for {symbol}: {e}")
            # Continue with defaults rather than failing completely
        
        # News from Financial Modeling Prep with better error handling
        try:
            if FMP_API_KEY:
                logger.info(f"Fetching news for {symbol}")
                news_url = f"{BASE_URL}/v3/stock_news"
                params = {
                    'tickers': symbol,
                    'limit': 5,
                    'apikey': FMP_API_KEY
                }
                
                # Log the URL we're requesting (without API key)
                logger.info(f"Making news request for {symbol}")
                
                news_response = requests.get(news_url, params=params, timeout=10)
                
                if news_response.status_code == 401:
                    logger.error(f"FMP API Authentication failed when fetching news for {symbol}")
                    # Continue with empty news
                elif news_response.status_code != 200:
                    logger.error(f"News API request failed with status code {news_response.status_code}")
                else:
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
                        logger.info(f"Retrieved {len(stock_details['news'])} news items for {symbol}")
                    else:
                        logger.warning(f"No news data or invalid format for {symbol}")
            else:
                logger.warning("Skipping news fetch - FMP_API_KEY not set")
        except requests.exceptions.Timeout:
            logger.error(f"News API request timed out for {symbol}")
        except requests.exceptions.RequestException as e:
            logger.error(f"News API request error for {symbol}: {e}")
        except Exception as e:
            logger.error(f"News processing error for {symbol}: {e}")

        # Fetch sentiment analysis - if the function exists
        try:
            logger.info(f"Fetching sentiment for {symbol}")
            sentiment_data = fetch_and_analyze_stock_sentiment(symbol)
            
            if sentiment_data and isinstance(sentiment_data, dict):
                # Combine existing news with sentiment news if needed
                existing_news = stock_details.get('news', [])
                sentiment_news = sentiment_data.get('news', [])
                
                # Merge news, prioritizing sentiment news but keeping existing if sentiment news is empty
                if sentiment_news:
                    stock_details['news'] = sentiment_news
                
                stock_details['sentiment'] = {
                    'overall_prediction': sentiment_data.get('overall_prediction', 'Neutral')
                }
                logger.info(f"Retrieved sentiment data for {symbol}")
            else:
                logger.warning(f"No sentiment data or invalid format for {symbol}")
        except NameError:
            logger.warning(f"Sentiment analysis function not available for {symbol}")
        except Exception as e:
            logger.error(f"Error fetching sentiment for {symbol}: {e}")
            stock_details['sentiment'] = {'overall_prediction': 'Neutral'}
            
        # Fetch Risk Analysis
        try:
            logger.info(f"Fetching risk analysis for {symbol}")
            
            # Use the fetch_risk_results function directly if possible
            try:
                risk_results = fetch_risk_results(symbol, portfolio)
                logger.info(f"Direct risk results fetched for {symbol}")
                
                if 'error' not in risk_results:
                    stock_details['risk_analysis'] = {
                        'risk_level': risk_results.get('risk_level', 'N/A'),
                        'volatility': risk_results.get('volatility', 'N/A'),
                        'daily_return': risk_results.get('daily_return', 'N/A'),
                        'current_price': risk_results.get('current_price', 'N/A'),
                        'trend': risk_results.get('trend', 'N/A'),
                        'latest_close': risk_results.get('latest_close', None)
                    }
                else:
                    logger.warning(f"Risk analysis returned error for {symbol}: {risk_results['error']}")
                    stock_details['risk_analysis'] = {
                        'risk_level': 'N/A',
                        'volatility': 'N/A',
                        'daily_return': 'N/A',
                        'current_price': 'N/A',
                        'latest_close': None,
                        'trend': 'N/A'
                    }
            except NameError:
                # Fall back to internal API call if function not available directly
                logger.info(f"Falling back to API call for risk analysis for {symbol}")
                host_url = request.host_url.rstrip('/')
                risk_url = f"{host_url}/risk/analyze/{symbol}"
                logger.info(f"Making risk request to: {risk_url}")
                
                risk_response = requests.get(risk_url, timeout=10)
                
                if risk_response.ok:
                    stock_details['risk_analysis'] = risk_response.json().get('risk_analysis')
                    logger.info(f"Retrieved risk analysis via API for {symbol}")
                else:
                    logger.warning(f"Risk analysis API call failed with status code {risk_response.status_code}")
                    stock_details['risk_analysis'] = {
                        'risk_level': 'N/A',
                        'volatility': 'N/A', 
                        'daily_return': 'N/A',
                        'current_price': 'N/A',
                        'latest_close': None,
                        'trend': 'N/A'
                    }
        except Exception as e:
            logger.error(f"Error fetching risk analysis for {symbol}: {e}")
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
            logger.info(f"Calculating price prediction for {symbol}")
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
                logger.info(f"Generated price prediction for {symbol}")
            else:
                logger.error(f"Price prediction error for {symbol}: {prediction_result['error']}")
                stock_details['price_prediction'] = None
        except Exception as e:
            logger.error(f"Error in price prediction for {symbol}: {e}")
            stock_details['price_prediction'] = None

        return stock_details

    except Exception as e:
        logger.exception(f"Comprehensive error fetching stock details for {symbol}: {e}")
        # Return a minimal stock details object instead of None
        # This prevents 404 errors when API calls fail
        return {
            'current_quote': {'price': 0.0, 'change': 0.0, 'change_percent': 0.0},
            'profile': {'name': symbol, 'symbol': symbol},
            'historical_prices': [],
            'news': [],
            'error': f"Failed to retrieve complete stock data: {str(e)}"
        }
    
@stock_bp.route('/details/<symbol>', methods=['GET'])
def stock_details_route(symbol):
    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400

    try:
        logger.info(f"Stock details route called for {symbol}")
        details = get_stock_details(symbol)
        
        # Always return a 200 status if we have any data at all
        return jsonify(details), 200
    except Exception as e:
        logger.exception(f"Unhandled error in stock details route for {symbol}: {e}")
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500
        
@risk_bp.route('/analyze/<symbol>', methods=['GET'])
def analyze_stock_risk(symbol):
    try:
        if not symbol:
            return jsonify({"error": "Symbol is required"}), 400
        
        logger.info(f"Risk analysis route called for {symbol}")
        
        # Attempt to get risk analysis results
        results = fetch_risk_results(symbol, portfolio)
        
        # Check for error in results
        if 'error' in results:
            logger.warning(f"Risk analysis error for {symbol}: {results['error']}")
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
            }), 200  # Still return 200 to prevent cascading errors
        
        # Return successful risk analysis
        logger.info(f"Risk analysis successful for {symbol}")
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
        logger.exception(f"Unhandled error analyzing risk for {symbol}: {e}")
        return jsonify({
            "risk_analysis": {
                "error": f"Failed to analyze stock risk: {str(e)}",
                "risk_level": 'N/A',
                "volatility": 'N/A',
                "daily_return": 'N/A',
                "current_price": 'N/A',
                "trend": 'N/A',
                "latest_close": None
            }
        }), 200  # Still return 200 to prevent cascading errors