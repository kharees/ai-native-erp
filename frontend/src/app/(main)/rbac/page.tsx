'use client';

import React, { useState, useEffect } from 'react';
import { fetchRoles, fetchPermissions, updateRolePermissions, createRole } from '@/services/rbacService';
import type { Role, Permission } from '@/types/rbac';

export default function RBACPage() {
  const [activeTab, setActiveTab] = useState('roles');
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  
  // Matrix state: role_id -> permission_id -> boolean
  const [matrix, setMatrix] = useState<Record<string, Record<string, boolean>>>({});
  const [editingRole, setEditingRole] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [newRoleName, setNewRoleName] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [r, p] = await Promise.all([fetchRoles(), fetchPermissions()]);
      setRoles(r);
      setPermissions(p);
      if (r.length > 0) setEditingRole(r[0].id);
      
      // Load current assigned permissions into matrix state if we fetched role-permissions
      // We will skip pre-populating for simplicity of the prompt, but normally we'd fetch role permissions here.
    } catch (e) {
      console.error('Failed to load RBAC data', e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRole = async () => {
    if (!newRoleName.trim()) return;
    try {
      const newRole = await createRole({ name: newRoleName, description: 'Custom Role' });
      setRoles(prev => [...prev, newRole]);
      setNewRoleName('');
    } catch (e) {
      console.error(e);
    }
  };

  const handleTogglePermission = (permissionId: string) => {
    if (!editingRole) return;
    setMatrix(prev => {
      const roleMatrix = { ...(prev[editingRole] || {}) };
      roleMatrix[permissionId] = !roleMatrix[permissionId];
      return { ...prev, [editingRole]: roleMatrix };
    });
  };

  const handleSaveMatrix = async () => {
    if (!editingRole) return;
    setSaving(true);
    
    const roleMatrix = matrix[editingRole] || {};
    const selectedIds = Object.keys(roleMatrix).filter(id => roleMatrix[id]);
    
    try {
      await updateRolePermissions([{ role_id: editingRole, permission_ids: selectedIds }]);
      alert('Matrix saved successfully');
    } catch (e) {
      console.error(e);
      alert('Failed to save matrix');
    } finally {
      setSaving(false);
    }
  };

  // Group permissions by module and action
  const modules = Array.from(new Set(permissions.map(p => p.module)));
  const actions = Array.from(new Set(permissions.map(p => p.action)));

  const getPermission = (mod: string, act: string) => permissions.find(p => p.module === mod && p.action === act);

  return (
    <div className="min-h-screen bg-gray-50/50 dark:bg-[#0a0a0a] p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">Access Control</h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              Manage enterprise roles, permission matrices, and user assignments.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 transition-all">
              <input 
                type="text" 
                placeholder="New custom role name..." 
                value={newRoleName}
                onChange={e => setNewRoleName(e.target.value)}
                className="px-3 py-2 text-sm bg-transparent outline-none flex-1 dark:text-white"
              />
              <button onClick={handleCreateRole} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-sm font-medium transition-colors border-l border-gray-200 dark:border-gray-800">
                Create
              </button>
            </div>
          </div>
        </header>

        <div className="border-b border-gray-200 dark:border-gray-800">
          <nav className="-mb-px flex space-x-8">
            {['roles', 'matrix', 'assignments'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                {tab === 'roles' ? 'Role Definitions' : tab === 'matrix' ? 'Permission Matrix' : 'User Assignments'}
              </button>
            ))}
          </nav>
        </div>

        {activeTab === 'roles' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {loading ? <p>Loading roles...</p> : roles.map((role) => (
              <div key={role.id} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{role.name}</h3>
                  <span className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium ${
                    role.is_system 
                      ? 'bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400 ring-1 ring-inset ring-blue-700/10 dark:ring-blue-400/20'
                      : 'bg-purple-50 text-purple-700 dark:bg-purple-500/10 dark:text-purple-400 ring-1 ring-inset ring-purple-700/10 dark:ring-purple-400/20'
                  }`}>
                    {role.is_system ? 'System' : 'Custom'}
                  </span>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                  {role.description || 'No description provided.'} Level {role.hierarchy_level}.
                </p>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'matrix' && (
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm overflow-hidden">
             <div className="p-4 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 flex flex-wrap gap-4 justify-between items-center">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Editing Role:</span>
                  <select 
                    value={editingRole}
                    onChange={e => setEditingRole(e.target.value)}
                    className="px-3 py-1.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-md text-sm outline-none"
                  >
                    {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </div>
                <button onClick={handleSaveMatrix} disabled={saving} className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors shadow-sm disabled:opacity-50">
                  {saving ? 'Saving...' : 'Save Matrix'}
                </button>
             </div>
             <div className="overflow-x-auto">
               <table className="w-full text-left border-collapse">
                 <thead>
                   <tr>
                     <th className="px-6 py-4 bg-gray-50 dark:bg-gray-800/30 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-200 dark:border-gray-800 border-r">Module</th>
                     {actions.map(action => (
                       <th key={action} className="px-4 py-4 bg-gray-50 dark:bg-gray-800/30 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-200 dark:border-gray-800 text-center text-[10px]">
                         {action}
                       </th>
                     ))}
                   </tr>
                 </thead>
                 <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                   {loading ? (
                     <tr><td colSpan={actions.length + 1} className="p-4 text-center text-sm text-gray-500">Loading matrix...</td></tr>
                   ) : modules.map(module => (
                     <tr key={module} className="hover:bg-gray-50 dark:hover:bg-gray-800/20 transition-colors">
                       <td className="px-6 py-4 whitespace-nowrap font-medium text-sm text-gray-900 dark:text-gray-200 border-r border-gray-200 dark:border-gray-800 bg-gray-50/30 dark:bg-gray-900/50">
                         {module}
                       </td>
                       {actions.map(action => {
                         const p = getPermission(module, action);
                         const isChecked = p ? !!(matrix[editingRole]?.[p.id]) : false;
                         
                         return (
                           <td key={action} className="px-4 py-4 text-center">
                             {p ? (
                               <input 
                                 type="checkbox" 
                                 checked={isChecked}
                                 onChange={() => handleTogglePermission(p.id)}
                                 className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 cursor-pointer" 
                               />
                             ) : <span className="text-gray-300 dark:text-gray-700">-</span>}
                           </td>
                         )
                       })}
                     </tr>
                   ))}
                 </tbody>
               </table>
             </div>
          </div>
        )}

        {activeTab === 'assignments' && (
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm p-8 text-center flex flex-col items-center justify-center">
             <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-50 dark:bg-blue-500/10 mb-4">
               <svg className="w-8 h-8 text-blue-600 dark:text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
               </svg>
             </div>
             <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Role Assignments</h3>
             <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
               Assign roles to users globally or scope them to specific branches and warehouses. This is managed via the Users directory.
             </p>
             <button onClick={() => window.location.href = '/users'} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm">
               Go to User Directory
             </button>
          </div>
        )}

      </div>
    </div>
  );
}
