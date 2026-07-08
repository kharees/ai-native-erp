"use client";
import React, { useState, useEffect } from 'react';

export default function ForecastingPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    setTimeout(() => {
      setData({
        forecasts: [
          { type: 'REVENUE', period: 'Q3-2026', predicted: 1500000, baseline: 1250000, trend: 'UP' },
          { type: 'EXPENSE', period: 'Q3-2026', predicted: 850000, baseline: 800000, trend: 'UP' },
          { type: 'CASH_FLOW', period: 'Q3-2026', predicted: 650000, baseline: 575000, trend: 'UP' }
        ]
      });
    }, 500);
  }, []);

  if (!data) return <div className="p-6">Loading Forecasts...</div>;

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Financial Forecasting</h1>
          <p className="text-gray-500 text-sm">Predictive Revenue & Cash Flow Modeling</p>
        </div>
        <button className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">Generate Forecast</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {data.forecasts.map((forecast: any, idx: number) => (
          <div key={idx} className="bg-white shadow rounded-lg p-6 flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-center mb-4 border-b pb-2">
                <h3 className="font-bold text-gray-800 capitalize">{forecast.type.replace('_', ' ').toLowerCase()} Forecast</h3>
                <span className="text-xs text-gray-500 font-mono bg-gray-100 px-2 py-1 rounded">{forecast.period}</span>
              </div>
              <div className="mb-2">
                <p className="text-sm text-gray-500">Predicted Target</p>
                <p className="text-3xl font-bold text-indigo-700">${forecast.predicted.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400">vs Current Baseline: ${forecast.baseline.toLocaleString()}</p>
              </div>
            </div>
            
            <div className={`mt-4 p-2 text-center rounded text-sm font-bold ${
              forecast.trend === 'UP' && forecast.type === 'EXPENSE' ? 'bg-red-100 text-red-700' :
              forecast.trend === 'UP' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
            }`}>
              Projected {forecast.trend === 'UP' ? 'Increase' : 'Decrease'} of {Math.abs(((forecast.predicted - forecast.baseline) / forecast.baseline) * 100).toFixed(1)}%
            </div>
          </div>
        ))}
      </div>
      
      <div className="mt-8 bg-white shadow rounded-lg p-6 flex items-center justify-center h-64 border-dashed border-2 border-gray-300">
          <p className="text-gray-400 italic">Advanced ML Trajectory Modeling Charts will render here</p>
      </div>
    </div>
  );
}
