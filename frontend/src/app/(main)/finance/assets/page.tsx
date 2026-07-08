"use client";
import React, { useState, useEffect } from 'react';

export default function AssetsPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    setTimeout(() => {
      setData({
        assets: [
          { id: '1', code: 'IT-001', name: 'Server Rack Alpha', category: 'IT Equipment', cost: 15000, value: 12500, method: 'SLM', status: 'ACTIVE' },
          { id: '2', code: 'VEH-045', name: 'Delivery Van', category: 'Vehicles', cost: 45000, value: 31000, method: 'WDV', status: 'ACTIVE' },
          { id: '3', code: 'OFF-102', name: 'Executive Desks', category: 'Furniture', cost: 8500, value: 2000, method: 'SLM', status: 'ACTIVE' }
        ],
        stats: {
          total_assets: 3,
          total_acquisition_cost: 68500,
          current_book_value: 45500,
          depreciation_ytd: 23000
        }
      });
    }, 500);
  }, []);

  if (!data) return <div className="p-6">Loading Asset Register...</div>;

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Fixed Asset Management</h1>
          <p className="text-gray-500 text-sm">Asset Register & Depreciation</p>
        </div>
        <div className="space-x-2">
          <button className="bg-white border text-gray-700 px-4 py-2 rounded shadow hover:bg-gray-50">Run Depreciation</button>
          <button className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">+ Add Asset</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-4 shadow rounded-lg border-t-4 border-gray-800">
          <p className="text-sm text-gray-500 font-medium">Total Assets</p>
          <p className="text-3xl font-bold">{data.stats.total_assets}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-t-4 border-blue-500">
          <p className="text-sm text-gray-500 font-medium">Acquisition Cost</p>
          <p className="text-3xl font-bold">${data.stats.total_acquisition_cost.toLocaleString()}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-t-4 border-green-500">
          <p className="text-sm text-gray-500 font-medium">Current Book Value</p>
          <p className="text-3xl font-bold text-green-600">${data.stats.current_book_value.toLocaleString()}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-t-4 border-red-500">
          <p className="text-sm text-gray-500 font-medium">Accum. Depreciation</p>
          <p className="text-3xl font-bold text-red-600">${data.stats.depreciation_ytd.toLocaleString()}</p>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Asset Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Cost</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Book Value</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Method</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.assets.map((item: any) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{item.code}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{item.name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.category}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">${item.cost.toLocaleString()}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-green-600">${item.value.toLocaleString()}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.method}</td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                    {item.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
