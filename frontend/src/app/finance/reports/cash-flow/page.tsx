"use client";
import React, { useState, useEffect } from 'react';

export default function CashFlowPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    setTimeout(() => {
      setData({
        operating_activities: [
          { description: 'Net Income', amount: 350000 },
          { description: 'Depreciation & Amortization', amount: 45000 },
          { description: 'Increase in Accounts Receivable', amount: -65000 },
          { description: 'Increase in Accounts Payable', amount: 17550 },
          { description: 'Decrease in Inventory', amount: 5000 }
        ],
        net_operating_cash: 352550,
        investing_activities: [
          { description: 'Purchase of Property & Equipment', amount: -150000 },
          { description: 'Sale of Investments', amount: 20000 }
        ],
        net_investing_cash: -130000,
        financing_activities: [
          { description: 'Proceeds from Long-term Debt', amount: 250000 },
          { description: 'Dividends Paid', amount: -25000 }
        ],
        net_financing_cash: 225000,
        net_cash_increase: 447550,
        opening_cash_balance: 127450,
        closing_cash_balance: 575000
      });
    }, 500);
  }, []);

  if (!data) return <div className="p-6">Loading statement...</div>;

  const renderSection = (title: string, lines: any[], totalTitle: string, totalAmount: number) => (
    <div className="mb-6">
      <h3 className="font-bold text-gray-800 bg-gray-100 px-4 py-2 rounded-t-lg">{title}</h3>
      <div className="bg-white p-4 border-x border-b rounded-b-lg">
        {lines.map((line, idx) => (
          <div key={idx} className="flex justify-between py-2 text-sm text-gray-700 border-b last:border-0 hover:bg-gray-50">
            <span>{line.description}</span>
            <span className={line.amount < 0 ? 'text-red-600' : 'text-gray-900'}>
              {line.amount < 0 ? `($${Math.abs(line.amount).toLocaleString()})` : `$${line.amount.toLocaleString()}`}
            </span>
          </div>
        ))}
        <div className="flex justify-between py-3 mt-2 border-t-2 font-bold text-gray-900">
          <span>{totalTitle}</span>
          <span className={totalAmount < 0 ? 'text-red-600' : 'text-gray-900'}>
            {totalAmount < 0 ? `($${Math.abs(totalAmount).toLocaleString()})` : `$${totalAmount.toLocaleString()}`}
          </span>
        </div>
      </div>
    </div>
  );

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold">Statement of Cash Flows</h1>
          <p className="text-gray-500 text-sm">Indirect Method</p>
        </div>
        <button className="bg-gray-100 text-gray-700 px-4 py-2 rounded shadow hover:bg-gray-200">Export PDF</button>
      </div>

      <div className="flex justify-between py-4 px-6 font-bold text-lg bg-blue-50 rounded mb-6 text-blue-900">
        <span>Opening Cash Balance</span>
        <span>${data.opening_cash_balance.toLocaleString()}</span>
      </div>

      {renderSection('Operating Activities', data.operating_activities, 'Net Cash from Operating Activities', data.net_operating_cash)}
      {renderSection('Investing Activities', data.investing_activities, 'Net Cash from Investing Activities', data.net_investing_cash)}
      {renderSection('Financing Activities', data.financing_activities, 'Net Cash from Financing Activities', data.net_financing_cash)}

      <div className="flex justify-between py-4 px-6 font-bold text-lg bg-green-50 rounded mt-6 text-green-900 border-t-4 border-green-200">
        <span>Closing Cash Balance</span>
        <span>${data.closing_cash_balance.toLocaleString()}</span>
      </div>
    </div>
  );
}
