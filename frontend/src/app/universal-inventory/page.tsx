import Link from 'next/link';

export default function UniversalInventoryDashboard() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Universal Dynamic Inventory</h1>
        <div className="text-sm text-gray-500">Phase 1: Master Data</div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <DashboardCard title="Item Master" description="Manage all universal products, variants, and dynamic attributes." link="/universal-inventory/items" />
        <DashboardCard title="Categories" description="Manage product hierarchy and classifications." link="/universal-inventory/categories" />
        <DashboardCard title="Brands" description="Manage manufacturer and brand records." link="/universal-inventory/brands" />
        <DashboardCard title="Units of Measure" description="Manage base units and conversion factors." link="/universal-inventory/uom" />
      </div>
    </div>
  );
}

function DashboardCard({ title, description, link }: { title: string, description: string, link: string }) {
  return (
    <Link href={link} className="block p-6 bg-white dark:bg-gray-800 rounded-xl shadow hover:shadow-lg transition-all border border-gray-100 dark:border-gray-700 hover:border-blue-500">
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-gray-600 dark:text-gray-400 text-sm">{description}</p>
    </Link>
  );
}
