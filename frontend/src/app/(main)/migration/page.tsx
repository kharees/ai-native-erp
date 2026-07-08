'use client';

import React, { useState } from 'react';
import { Upload, FileText, Database, ShieldAlert, Sparkles, CheckCircle, Search, Settings, AlertTriangle } from 'lucide-react';

export default function MigrationHubPage() {
  const [activeTab, setActiveTab] = useState<'upload' | 'mapping' | 'cleansing' | 'validation' | 'preview'>('upload');
  const [file, setFile] = useState<File | null>(null);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-8 font-sans text-slate-800 dark:text-slate-200">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header */}
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
              <Database className="w-8 h-8 text-indigo-500" />
              Enterprise Data Migration Hub
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
              AI-Powered Master Data Importer with automated cleansing and validation.
            </p>
          </div>
          <div className="flex gap-4">
            <span className="px-4 py-2 bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400 rounded-full font-semibold flex items-center gap-2">
              <Sparkles className="w-4 h-4" /> AI Advisory Active
            </span>
          </div>
        </header>

        {/* Tab Navigation */}
        <div className="flex gap-4 border-b border-slate-200 dark:border-slate-800 pb-4 overflow-x-auto">
          {[
            { id: 'upload', icon: Upload, label: '1. File Upload' },
            { id: 'mapping', icon: Settings, label: '2. AI Mapping' },
            { id: 'cleansing', icon: Search, label: '3. Cleansing Dashboard' },
            { id: 'validation', icon: ShieldAlert, label: '4. Validation Dashboard' },
            { id: 'preview', icon: CheckCircle, label: '5. Preview & Import' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700'
              }`}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-8 min-h-[500px]">
          
          {/* UPLOAD TAB */}
          {activeTab === 'upload' && (
            <div className="flex flex-col items-center justify-center h-full space-y-6 text-center animate-in fade-in">
              <div className="w-24 h-24 bg-indigo-50 dark:bg-indigo-900/20 rounded-full flex items-center justify-center">
                <FileText className="w-12 h-12 text-indigo-500" />
              </div>
              <div>
                <h3 className="text-xl font-bold mb-2">Drag & Drop Master Data</h3>
                <p className="text-slate-500 max-w-md mx-auto">Supports Excel (.xlsx), CSV, JSON, and XML exported from Tally, SAP, Zoho, and more.</p>
              </div>
              <input type="file" className="block w-full max-w-sm text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 dark:file:bg-indigo-900/30 dark:file:text-indigo-300" />
            </div>
          )}

          {/* AI MAPPING TAB */}
          {activeTab === 'mapping' && (
            <div className="space-y-6 animate-in fade-in">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold flex items-center gap-2"><Sparkles className="text-amber-500"/> AI Field Mapping Suggestions</h2>
                <span className="text-sm bg-green-100 text-green-700 px-3 py-1 rounded-full">Overall Confidence: 87%</span>
              </div>
              <div className="grid grid-cols-3 gap-4 font-semibold text-slate-500 border-b pb-2">
                <div>Source Column (Excel)</div>
                <div>Suggested Target Field</div>
                <div>Confidence Score</div>
              </div>
              {[
                { source: 'Customer Name', target: 'name', score: 95 },
                { source: 'Email Address', target: 'email', score: 95 },
                { source: 'Phone No', target: 'phone', score: 82 },
                { source: 'Random Field', target: 'Unmapped', score: 0 },
              ].map((row, i) => (
                <div key={i} className="grid grid-cols-3 gap-4 items-center py-4 border-b border-slate-100 dark:border-slate-700">
                  <div className="font-medium">{row.source}</div>
                  <div>
                    <select className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-600 rounded p-2 w-full max-w-[200px]">
                      <option value={row.target}>{row.target}</option>
                    </select>
                  </div>
                  <div>
                    {row.score > 0 ? (
                      <div className="flex items-center gap-3">
                        <div className="w-full bg-slate-200 rounded-full h-2.5 dark:bg-slate-700 max-w-[150px]">
                          <div className={`h-2.5 rounded-full ${row.score > 80 ? 'bg-green-500' : 'bg-amber-500'}`} style={{ width: `${row.score}%` }}></div>
                        </div>
                        <span className="text-sm font-semibold">{row.score}%</span>
                      </div>
                    ) : (
                      <span className="text-sm text-slate-400">Needs manual mapping</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* CLEANSING TAB */}
          {activeTab === 'cleansing' && (
            <div className="space-y-6 animate-in fade-in">
               <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold flex items-center gap-2"><Search className="text-blue-500"/> Data Cleansing Dashboard</h2>
                <span className="text-sm bg-blue-100 text-blue-700 px-3 py-1 rounded-full">1 Duplicate Cluster Detected</span>
              </div>
              <div className="bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 p-6 rounded-xl">
                <h3 className="font-semibold text-amber-800 dark:text-amber-500 flex items-center gap-2 mb-4">
                  <AlertTriangle className="w-5 h-5"/> Potential Duplicate Customers
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between bg-white dark:bg-slate-800 p-4 rounded border">
                    <div>
                      <div className="font-bold">Acme Corp</div>
                      <div className="text-sm text-slate-500">info@acme.com | 1234567890</div>
                    </div>
                    <button className="text-blue-600 text-sm font-semibold hover:underline">Select as Primary</button>
                  </div>
                  <div className="flex justify-between bg-white dark:bg-slate-800 p-4 rounded border">
                    <div>
                      <div className="font-bold">Acme Corporation</div>
                      <div className="text-sm text-slate-500">info@acme.com | 1234567890</div>
                    </div>
                    <button className="text-blue-600 text-sm font-semibold hover:underline">Select as Primary</button>
                  </div>
                </div>
                <div className="mt-4 flex gap-3">
                  <button className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold">Merge & Keep Primary</button>
                  <button className="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-200 rounded-lg text-sm font-semibold">Keep Both</button>
                </div>
              </div>
            </div>
          )}

          {/* VALIDATION TAB */}
          {activeTab === 'validation' && (
             <div className="space-y-6 animate-in fade-in">
             <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold flex items-center gap-2"><ShieldAlert className="text-red-500"/> Validation Rules Engine</h2>
              <span className="text-sm bg-red-100 text-red-700 px-3 py-1 rounded-full">3 Errors Found</span>
            </div>
            <div className="grid gap-4">
              <div className="p-4 border border-red-200 bg-red-50 dark:bg-red-900/10 dark:border-red-800 rounded-lg flex items-start gap-4">
                <AlertTriangle className="w-6 h-6 text-red-500 mt-1 flex-shrink-0" />
                <div>
                  <h4 className="font-bold text-red-800 dark:text-red-400">Row 42: Invalid email format in field &apos;email&apos;</h4>
                  <p className="text-sm text-red-600 dark:text-red-300 mt-1">Value provided: &quot;invalid_email.com&quot;</p>
                  <div className="mt-3 bg-white dark:bg-slate-800 p-3 rounded border text-sm text-slate-600 dark:text-slate-300">
                    <span className="font-bold text-indigo-600 dark:text-indigo-400">AI Assistant:</span> The email format is incorrect. Ensure it contains an &apos;@&apos; symbol and a valid domain.
                  </div>
                </div>
              </div>
            </div>
          </div>
          )}

          {/* PREVIEW TAB */}
          {activeTab === 'preview' && (
             <div className="space-y-6 animate-in fade-in h-full flex flex-col">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold flex items-center gap-2"><CheckCircle className="text-green-500"/> Migration Readiness Preview</h2>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="text-sm text-slate-500">Data Quality Score</div>
                    <div className="text-2xl font-bold text-green-600">98%</div>
                  </div>
                  <button className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white font-bold rounded-xl shadow-lg transition-transform hover:scale-105 active:scale-95">
                    Start Import
                  </button>
                </div>
              </div>
              <div className="bg-slate-50 dark:bg-slate-900 border rounded-lg overflow-x-auto flex-1">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b bg-white dark:bg-slate-800">
                      <th className="p-4 font-semibold text-sm">Status</th>
                      <th className="p-4 font-semibold text-sm">Name</th>
                      <th className="p-4 font-semibold text-sm">Email</th>
                      <th className="p-4 font-semibold text-sm">Phone</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[1, 2, 3].map((row) => (
                      <tr key={row} className="border-b dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800">
                        <td className="p-4"><span className="w-3 h-3 rounded-full bg-green-500 inline-block"></span></td>
                        <td className="p-4 font-medium">Acme Corp</td>
                        <td className="p-4 text-slate-500">info@acme.com</td>
                        <td className="p-4 text-slate-500">1234567890</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
             </div>
          )}
        </div>
      </div>
    </div>
  );
}
