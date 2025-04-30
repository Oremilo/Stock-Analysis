import React, { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './card';
import { TrendingUp, TrendingDown, BarChart2, AlertTriangle, Construction } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const PricePredictionCard = ({ prediction }) => {
  const [visible, setVisible] = useState(true);
  const overlayTimerRef = useRef(null);
  const dataTimerRef = useRef(null);
  
  // Effect to toggle visibility with proper cleanup
  useEffect(() => {
    const showOverlay = () => {
      setVisible(true);
      // Clear any existing timer for overlay
      if (overlayTimerRef.current) clearTimeout(overlayTimerRef.current);
      
      // Set timer to hide overlay after 10 seconds
      overlayTimerRef.current = setTimeout(() => {
        setVisible(false);
        
        // Clear any existing timer for data view
        if (dataTimerRef.current) clearTimeout(dataTimerRef.current);
        
        // Set timer to show overlay again after 4 seconds of data viewing
        dataTimerRef.current = setTimeout(showOverlay, 3000);
      }, 8000);
    };
    
    // Start the cycle
    showOverlay();
    
    // Clean up all timers when component unmounts
    return () => {
      if (overlayTimerRef.current) clearTimeout(overlayTimerRef.current);
      if (dataTimerRef.current) clearTimeout(dataTimerRef.current);
    };
  }, []);
  
  // Create basic card structure when prediction is missing or has error
  if (!prediction || prediction.error) {
    return (
      <Card className="bg-gray-800">
        <CardHeader>
          <CardTitle className="flex items-center text-xl">
            <BarChart2 className="mr-2" />
            Price Prediction
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center p-4">
            <AlertTriangle className="mx-auto mb-2 text-yellow-500" size={24} />
            <div className="text-gray-400">
              Unable to generate price prediction at this time.
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const isBullish = prediction.prediction_direction === 'Bullish';
  const trendColor = isBullish ? 'text-green-500' : 'text-red-500';
  const TrendIcon = isBullish ? TrendingUp : TrendingDown;

  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price);
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 80) return 'text-green-500';
    if (confidence >= 60) return 'text-yellow-500';
    return 'text-red-500';
  };

  // Prepare training metrics data for the chart
  const trainingData = prediction.training_metrics?.loss.map((loss, index) => ({
    epoch: index + 1,
    loss: loss,
    val_loss: prediction.training_metrics.val_loss[index]
  }));

  return (
    <div className="relative">
      {/* The original card component */}
      <Card className="bg-gray-800 relative">
        <CardHeader>
          <CardTitle className="flex items-center text-xl">
            <BarChart2 className="mr-2" />
            Price Prediction
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Price Prediction Section */}
            <div className="text-center">
              <div className="text-sm text-gray-400 mb-1">Predicted Price</div>
              <div className={`text-3xl font-bold ${trendColor} flex items-center justify-center`}>
                <TrendIcon className="mr-2" size={24} />
                {formatPrice(prediction.predicted_price)}
              </div>
            </div>

            {/* Price Change Section */}
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center">
                <div className="text-sm text-gray-400 mb-1">Price Change</div>
                <div className={`font-bold ${trendColor}`}>
                  {formatPrice(prediction.price_change)}
                </div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-400 mb-1">Current Price</div>
                <div className="font-bold text-white">
                  {formatPrice(prediction.last_close_price)}
                </div>
              </div>
            </div>

            {/* Training Metrics Chart */}
            {prediction.training_metrics && (
              <div className="mt-6">
                <div className="text-sm text-gray-400 mb-2">Model Training Progress</div>
                <div className="h-64 w-full">
                  <ResponsiveContainer>
                    <LineChart data={trainingData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis 
                        dataKey="epoch" 
                        stroke="#9CA3AF"
                        label={{ value: 'Epoch', position: 'insideBottom', offset: -5 }}
                      />
                      <YAxis 
                        stroke="#9CA3AF"
                        label={{ value: 'Loss', angle: -90, position: 'insideLeft' }}
                      />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1F2937', border: 'none' }}
                        labelStyle={{ color: '#9CA3AF' }}
                      />
                      <Legend />
                      <Line 
                        type="monotone" 
                        dataKey="loss" 
                        stroke="#10B981" 
                        name="Training Loss" 
                      />
                      <Line 
                        type="monotone" 
                        dataKey="val_loss" 
                        stroke="#F59E0B" 
                        name="Validation Loss" 
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                  <div className="text-center">
                    <div className="text-gray-400">Final Training Loss</div>
                    <div className="font-medium text-green-500">
                      {prediction.training_metrics.final_loss.toFixed(2)}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-gray-400">Final Validation Loss</div>
                    <div className="font-medium text-yellow-500">
                      {prediction.training_metrics.final_val_loss.toFixed(2)}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Confidence Meter */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Prediction Confidence</span>
                <span className={getConfidenceColor(prediction.prediction_confidence)}>
                  {prediction.prediction_confidence}%
                </span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${getConfidenceColor(prediction.prediction_confidence)}`}
                  style={{ width: `${prediction.prediction_confidence}%` }}
                />
              </div>
            </div>

            {/* Prediction Direction Badge */}
            <div className="flex justify-center">
              <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                isBullish ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
              }`}>
                <TrendIcon className="mr-1" size={16} />
                {prediction.prediction_direction}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* The overlay banner - with visibility toggle */}
      <div className={`absolute inset-0 bg-black bg-opacity-60 backdrop-blur-sm flex flex-col items-center justify-center rounded-lg z-10 transition-opacity duration-1000 ${visible ? 'opacity-100' : 'opacity-0'}`}>
        <div className="flex flex-col items-center px-4 py-6 max-w-md text-center">
          <Construction className="h-10 w-10 text-yellow-400 mb-4" />
          <h3 className="text-xl font-bold text-white mb-2">Under Development</h3>
          <p className="text-gray-300">Our prediction algorithm is currently being refined. The data shown is for preview purposes only and should not be used for making investment decisions.</p>
        </div>
      </div>
    </div>
  );
};

export default PricePredictionCard;