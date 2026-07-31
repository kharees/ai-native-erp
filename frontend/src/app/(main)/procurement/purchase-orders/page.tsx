'use client';

import { useEffect, useState, useCallback } from 'react';
import apiClient, { isApiError } from '@/lib/apiClient';
import { PageShell, DataTable, Button, Card, CardContent, FormSection, FormRow, Input, Select, Alert, Badge } from '@/components/ui';
import { Column } from '@/components/ui/DataTable';
import { Plus } from 'lucide-react';
import Link from 'next/link';
import { formatCurrency } from '@/lib/formatCurrency';

interface Vendor {
  id: string;
  name: string;
}

interface Warehouse {
  id: string;
  name: string;
}

interface Item {
  id: string;
  name: string;
}

interface PurchaseOrderLine {
  id: string;
  item_id: string;
  quantity: number;
  unit_cost: string;
  quantity_received: number;
}

interface PurchaseOrder {
  id: string;
  vendor_id: string;
  po_number: string;
  status: 'draft' | 'sent' | 'partially_received' | 'received' | 'cancelled';
  expected_date: string | null;
  created_at: string;
  lines: PurchaseOrderLine[];
}

const BASE = '/api/v1/procurement';

function statusVariant(status: PurchaseOrder['status']): 'success' | 'accent' | 'warning' | 'neutral' | 'danger' {
  switch (status) {
    case 'received': return 'success';
    case 'partially_received': return 'warning';
    case 'cancelled': return 'danger';
    case 'sent': return 'accent';
    default: return 'neutral';
  }
}

function poTotal(po: PurchaseOrder): number {
  return po.lines.reduce((sum, line) => sum + line.quantity * Number(line.unit_cost), 0);
}

export default function PurchaseOrdersPage() {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const [vendorId, setVendorId] = useState('');
  const [warehouseId, setWarehouseId] = useState('');
  const [expectedDate, setExpectedDate] = useState('');
  const [itemId, setItemId] = useState('');
  const [quantity, setQuantity] = useState('1');
  const [unitCost, setUnitCost] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      apiClient.get(`${BASE}/purchase-orders`),
      apiClient.get('/api/v1/finance-ar-ap/ap/vendors'),
      apiClient.get('/api/v1/universal-warehousing/warehouses'),
      apiClient.get('/api/v1/universal-inventory/items'),
    ])
      .then(([poRes, vendorRes, whRes, itemRes]) => {
        setOrders(poRes.data.items || []);
        setVendors(vendorRes.data || []);
        setWarehouses(whRes.data?.items ?? []);
        setItems(itemRes.data?.items ?? []);
      })
      .catch((err) => {
        console.error('Failed to load purchase orders page data', err);
        setError(isApiError(err) ? err.message : 'Failed to load purchase orders');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const vendorName = (id: string) => vendors.find((v) => v.id === id)?.name || id;

  const resetForm = () => {
    setShowForm(false);
    setVendorId('');
    setWarehouseId('');
    setExpectedDate('');
    setItemId('');
    setQuantity('1');
    setUnitCost('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await apiClient.post(`${BASE}/purchase-orders`, {
        vendor_id: vendorId,
        warehouse_id: warehouseId,
        expected_date: expectedDate ? new Date(expectedDate).toISOString() : null,
        lines: [{ item_id: itemId, quantity: parseFloat(quantity), unit_cost: Number(unitCost).toFixed(2) }],
      });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to create purchase order');
    } finally {
      setSaving(false);
    }
  };

  const columns: Column<PurchaseOrder>[] = [
    {
      key: 'po_number',
      header: 'PO Number',
      sortable: true,
      cell: (row) => (
        <Link href={`/procurement/purchase-orders/${row.id}`} className="font-mono text-accent-600 hover:text-accent-700 dark:text-accent-400 dark:hover:text-accent-300 hover:underline">
          {row.po_number}
        </Link>
      ),
    },
    {
      key: 'vendor_id',
      header: 'Vendor',
      sortable: true,
      cell: (row) => vendorName(row.vendor_id),
    },
    {
      key: 'total',
      header: 'Total Value',
      align: 'right',
      cell: (row) => formatCurrency(poTotal(row)),
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      cell: (row) => <Badge variant={statusVariant(row.status)}>{row.status.replace(/_/g, ' ')}</Badge>,
    },
    {
      key: 'expected_date',
      header: 'Expected',
      cell: (row) => (row.expected_date ? new Date(row.expected_date).toLocaleDateString() : '-'),
    },
  ];

  return (
    <PageShell
      title="Purchase Orders"
      actions={
        <Button variant={showForm ? 'outline' : 'primary'} onClick={() => (showForm ? resetForm() : setShowForm(true))} leftIcon={!showForm ? <Plus size={16} /> : undefined}>
          {showForm ? 'Cancel' : 'New Purchase Order'}
        </Button>
      }
    >
      <div className="space-y-6">
        <p className="text-body text-neutral-500 dark:text-neutral-400">
          Create purchase orders and receive stock against them -- receiving updates inventory and creates the matching AP bill automatically.
        </p>

        {error && <Alert variant="error">{error}</Alert>}

        {showForm && (
          <Card>
            <CardContent className="p-6">
              <FormSection title="New Purchase Order (single line item)">
                <form onSubmit={handleSubmit} className="space-y-4">
                  <FormRow>
                    <Select label="Vendor" required value={vendorId} onChange={(e) => setVendorId(e.target.value)}>
                      <option value="">- Select -</option>
                      {vendors.map((v) => (<option key={v.id} value={v.id}>{v.name}</option>))}
                    </Select>
                    <Select label="Receiving Warehouse" required value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)}>
                      <option value="">- Select -</option>
                      {warehouses.map((w) => (<option key={w.id} value={w.id}>{w.name}</option>))}
                    </Select>
                    <Input type="date" label="Expected Date" value={expectedDate} onChange={(e) => setExpectedDate(e.target.value)} />
                  </FormRow>
                  <FormRow>
                    <Select label="Item" required value={itemId} onChange={(e) => setItemId(e.target.value)}>
                      <option value="">- Select -</option>
                      {items.map((i) => (<option key={i.id} value={i.id}>{i.name}</option>))}
                    </Select>
                    <Input type="number" step="0.01" label="Quantity" required value={quantity} onChange={(e) => setQuantity(e.target.value)} />
                    <Input type="number" step="0.01" label="Unit Cost" required value={unitCost} onChange={(e) => setUnitCost(e.target.value)} />
                  </FormRow>
                  <div className="flex justify-end gap-2 pt-4">
                    <Button variant="outline" type="button" onClick={resetForm}>Cancel</Button>
                    <Button variant="primary" type="submit" isLoading={saving}>Save Purchase Order</Button>
                  </div>
                </form>
              </FormSection>
            </CardContent>
          </Card>
        )}

        <div className="h-[600px]">
          <DataTable
            data-testid="purchase-orders-table"
            data={orders}
            columns={columns}
            keyExtractor={(row) => row.id}
            isLoading={loading}
            searchPlaceholder="Search purchase orders..."
          />
        </div>
      </div>
    </PageShell>
  );
}
