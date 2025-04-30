import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ArrowUp, ArrowDown, Building, TrendingUp, TrendingDown, AlertTriangle, AlertOctagon } from 'lucide-react';
import { motion } from 'framer-motion';
import RiskAnalysisSection from '../components/RiskAnalysisSection';
import PricePredictionCard from '../components/PricePredictionCard';
import { Card, CardHeader, CardTitle, CardContent } from '../components/card';
import { Alert, AlertDescription } from '../components/alert';
import StockSentimentDisplay from '../components/StockSentimentDisplay';

const SentimentAnalysisCard = ({ sentiment }) => {
  if (!sentiment || !sentiment.overall_prediction) {
    return null;
  }

  const score = sentiment.overall_prediction;

  const getSentimentColor = (score) => {
    if (score <= 40) return 'text-red-500';
    if (score >= 60) return 'text-green-500';
    return 'text-yellow-500';
  };

  const getSentimentText = (score) => {
    if (score <= 40) return 'Bearish';
    if (score >= 60) return 'Bullish';
    return 'Neutral';
  };

  const getSentimentIcon = (score) => {
    if (score <= 40) return <TrendingDown className="h-6 w-6" />;
    if (score >= 60) return <TrendingUp className="h-6 w-6" />;
    return <AlertTriangle className="h-6 w-6" />;
  };

  return (
    <Card className="bg-gray-800">
      <CardHeader>
        <CardTitle className="flex items-center text-xl">
          {getSentimentIcon(score)}
          <span className="ml-2">Market Sentiment</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-center">
          <div className={`text-3xl font-bold mb-2 ${getSentimentColor(score)}`}>
            {getSentimentText(score)}
          </div>
          <div className="text-gray-400">
            Sentiment Score: {score.toFixed(1)}
          </div>
          <div className="mt-4 w-full bg-gray-700 rounded-full h-2.5">
            <div
              className={`h-2.5 rounded-full ${getSentimentColor(score)}`}
              style={{ width: `${score}%` }}
            ></div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

const LoadingState = ({ loadingSteps }) => {
  return (
    <div className="flex flex-col justify-center items-center min-h-screen">
      <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500 mb-8"></div>
      <div className="text-xl text-gray-300 mb-2">Loading Stock Analysis</div>
      
      <div className="space-y-3 mt-6 w-full max-w-md">
        {loadingSteps.map((step, index) => (
          <motion.div 
            key={index}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.7 }}
            className="flex items-center"
          >
            <div className="w-6 h-6 mr-3">
              {step.active && <div className="w-full h-full rounded-full bg-blue-500 animate-pulse"></div>}
              {step.completed && <div className="w-full h-full rounded-full bg-green-500 flex items-center justify-center">✓</div>}
            </div>
            <div className={`${step.active ? 'text-blue-400' : step.completed ? 'text-green-400' : 'text-gray-500'}`}>
              {step.text}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

const StockAnalysis = () => {
  const { symbol } = useParams();
  const [stockDetails, setStockDetails] = useState({
    current_quote: {
      price: 0,
      change: 0,
      change_percent: 0,
    },
    profile: {
      name: '',
      symbol: '',
      industry: '',
      sector: '',
      country: '',
      website: '',
    },
    historical_prices: [],
    news: [],
    country_news: [],
    sentiment: null,
    risk_analysis: null,
    price_prediction: null
  });
  const [loading, setLoading] = useState({
    main: true,
    prediction: false,
    risk: false
  });
  const [errors, setErrors] = useState({
    main: "",
    prediction: "",
    risk: ""
  });
  
  // Loading steps state
  const [loadingSteps, setLoadingSteps] = useState([
    { text: "Fetching stock data", active: true, completed: false },
    { text: "Training sentiment analysis model", active: false, completed: false },
    { text: "Analyzing market risks", active: false, completed: false },
    { text: "Generating price predictions", active: false, completed: false }
  ]);

  useEffect(() => {
    const fetchStockData = async () => {
      if (!symbol) {
        setErrors(prev => ({ ...prev, main: "No stock symbol provided" }));
        setLoading(prev => ({ ...prev, main: false }));
        return;
      }

      try {
        setLoading(prev => ({ ...prev, main: true }));
        
        // Start loading animation
        const stepDelay = 4000; // Delay between steps in ms
        
        // We'll use setTimeout to simulate the progressive loading steps
        const stepTimers = [];
        
        // Step 1 is already active from initial state
        
        // Step 2: Sentiment analysis (after delay)
        stepTimers.push(setTimeout(() => {
          setLoadingSteps(prev => {
            const updated = [...prev];
            updated[0].completed = true;
            updated[0].active = false;
            updated[1].active = true;
            return updated;
          });
        }, stepDelay));
        
        // Step 3: Risk analysis (after another delay)
        stepTimers.push(setTimeout(() => {
          setLoadingSteps(prev => {
            const updated = [...prev];
            updated[1].completed = true;
            updated[1].active = false;
            updated[2].active = true;
            return updated;
          });
        }, stepDelay * 2));
        
        // Step 4: Price prediction (after another delay)
        stepTimers.push(setTimeout(() => {
          setLoadingSteps(prev => {
            const updated = [...prev];
            updated[2].completed = true;
            updated[2].active = false;
            updated[3].active = true;
            return updated;
          });
        }, stepDelay * 3));

        // Actual data fetching
        const response = await fetch(`${process.env.REACT_APP_API_URL}/stocks/details/${symbol}`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch stock data: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.error) {
          throw new Error(data.error);
        }

        // Mark final step as completed
        setLoadingSteps(prev => {
          const updated = [...prev];
          updated[3].completed = true;
          updated[3].active = false;
          return updated;
        });

        // Set the actual data
        setStockDetails(prevDetails => ({
          ...prevDetails,
          ...data
        }));
        setErrors(prev => ({ ...prev, main: "" }));
        
        // Small delay to show the completed state before removing loading screen
        setTimeout(() => {
          setLoading(prev => ({ ...prev, main: false }));
        }, 800);
        
      } catch (err) {
        console.error('Fetch error:', err);
        setErrors(prev => ({ ...prev, main: err.message || "Failed to load stock data" }));
        
        // Clear all loading timers if there's an error
        clearLoadingSteps();
        
        setLoading(prev => ({ ...prev, main: false }));
      }
    };

    const clearLoadingSteps = () => {
      // Clear any pending step updates
      for (let i = 0; i < 10; i++) {
        clearTimeout(i);
      }
    };

    fetchStockData();
    
    // Cleanup timers on component unmount
    return () => {
      for (let i = 0; i < 10; i++) {
        clearTimeout(i);
      }
    };
  }, [symbol]);

  const renderError = (error, type) => {
    if (!error) return null;
    
    return (
      <Alert variant="destructive" className="mb-4">
        <AlertOctagon className="h-4 w-4" />
        <AlertDescription>
          {type === 'prediction' && 'Price Prediction Error: '}
          {type === 'risk' && 'Risk Analysis Error: '}
          {error}
        </AlertDescription>
      </Alert>
    );
  };

  if (loading.main) {
    return <LoadingState loadingSteps={loadingSteps} />;
  }

  if (errors.main) {
    return (
      <Alert variant="destructive" className="m-4">
        <AlertOctagon className="h-4 w-4" />
        <AlertDescription>{errors.main}</AlertDescription>
      </Alert>
    );
  }

  const isPositiveChange = stockDetails.current_quote.change > 0;

  return (
    <div className="max-w-7xl mx-auto p-4 space-y-6">
      {/* Header Section */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gray-800 rounded-xl p-6 shadow-lg"
      >
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold mb-2">{stockDetails.profile.name}</h1>
            <p className="text-gray-400">{symbol}</p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">${stockDetails.current_quote.price.toFixed(2)}</div>
            <div className={`flex items-center justify-end ${isPositiveChange ? 'text-green-500' : 'text-red-500'}`}>
              {isPositiveChange ? <ArrowUp size={20} /> : <ArrowDown size={20} />}
              <span className="ml-1">{Math.abs(stockDetails.current_quote.change_percent).toFixed(2)}%</span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Error Messages */}
      {renderError(errors.prediction, 'prediction')}
      {renderError(errors.risk, 'risk')}

      {/* Analysis Cards Grid */}
      <div className="grid md:grid-cols-2 gap-6">
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          <SentimentAnalysisCard sentiment={stockDetails.sentiment} />
        </motion.div>
        
        {stockDetails.price_prediction && (
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
          >
            <PricePredictionCard 
              prediction={stockDetails.price_prediction} 
              loading={loading.prediction}
              error={errors.prediction}
            />
          </motion.div>
        )}
      </div>

      {/* Price History Chart */}
      {stockDetails.historical_prices.length > 0 && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-gray-800 rounded-xl p-6 shadow-lg"
        >
          <h2 className="text-xl font-bold mb-4">Price History</h2>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stockDetails.historical_prices}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="date" 
                  stroke="#9CA3AF"
                  tickFormatter={(value) => new Date(value).toLocaleDateString()}
                />
                <YAxis stroke="#9CA3AF" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1F2937',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '12px'
                  }}
                  labelFormatter={(value) => new Date(value).toLocaleDateString()}
                />
                <Line
                  type="monotone"
                  dataKey="close"
                  stroke={isPositiveChange ? "#10B981" : "#EF4444"}
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      )}

      {/* Company Info */}
      <div className="grid grid-cols-1 gap-6">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-gray-800 rounded-xl p-6 shadow-lg"
        >
          <h2 className="text-xl font-bold mb-4 flex items-center">
            <Building className="mr-2" />
            Company Information
          </h2>
          <div className="space-y-3">
            <p><span className="text-gray-400">Industry:</span> {stockDetails.profile.industry}</p>
            <p><span className="text-gray-400">Sector:</span> {stockDetails.profile.sector}</p>
            <p><span className="text-gray-400">Country:</span> {stockDetails.profile.country}</p>
            <p>
              <span className="text-gray-400">Website:</span> 
              <a href={stockDetails.profile.website} target="_blank" rel="noopener noreferrer" 
                 className="ml-2 text-blue-400 hover:text-blue-300">
                {stockDetails.profile.website}
              </a>
            </p>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <StockSentimentDisplay stockDetails={stockDetails} />
        </motion.div>

        {/* Risk Analysis Section */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
        >
          <RiskAnalysisSection 
            riskAnalysis={stockDetails.risk_analysis}
            loading={loading.risk}
            error={errors.risk}
          />
        </motion.div>
      </div>
    </div>
  );
};

export default StockAnalysis;