'use client';

import { useCallback, useEffect, useState } from 'react';
import apiClient, { isApiError } from '@/lib/apiClient';

/**
 * hooks/useCrudResource.ts
 * ========================
 * Shared data-fetching/mutation boilerplate for the simple flat-entity CRUD
 * pages (Brands, UOM, Warehouses, etc.) - same manual useState/useEffect
 * pattern already used in universal-inventory/categories, items,
 * finance/chart-of-accounts, and omnichannel-billing/customers, factored out
 * so each new page only needs to supply its own form/table JSX.
 *
 * The backend's list endpoints return either a bare array (Finance-style) or
 * a `{ items, meta }` paginated envelope (Universal Inventory-style) -
 * `listKey` picks which shape to unwrap.
 */
export function useCrudResource<T extends { id: string }>(
  basePath: string,
  options: { listKey?: 'items' | null } = {}
) {
  const { listKey = 'items' } = options;
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    apiClient
      .get(basePath)
      .then((res) => {
        const body = res.data;
        setData(listKey ? body?.[listKey] ?? [] : Array.isArray(body) ? body : []);
      })
      .catch((err) => setError(isApiError(err) ? err.message : 'Failed to load data'))
      .finally(() => setLoading(false));
  }, [basePath, listKey]);

  useEffect(() => {
    load();
  }, [load]);

  const create = useCallback(
    async (payload: unknown) => {
      setSaving(true);
      setError('');
      try {
        await apiClient.post(basePath, payload);
        load();
        return true;
      } catch (err) {
        setError(isApiError(err) ? err.message : 'Failed to create record');
        return false;
      } finally {
        setSaving(false);
      }
    },
    [basePath, load]
  );

  const update = useCallback(
    async (id: string, payload: unknown) => {
      setSaving(true);
      setError('');
      try {
        await apiClient.patch(`${basePath}/${id}`, payload);
        load();
        return true;
      } catch (err) {
        setError(isApiError(err) ? err.message : 'Failed to update record');
        return false;
      } finally {
        setSaving(false);
      }
    },
    [basePath, load]
  );

  const remove = useCallback(
    async (id: string) => {
      setError('');
      try {
        await apiClient.delete(`${basePath}/${id}`);
        load();
        return true;
      } catch (err) {
        setError(isApiError(err) ? err.message : 'Failed to delete record');
        return false;
      }
    },
    [basePath, load]
  );

  return { data, loading, error, setError, saving, load, create, update, remove };
}
