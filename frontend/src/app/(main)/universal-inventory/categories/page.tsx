import Link from 'next/link';

export default function CategoriesPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Dashboard</Link>
          <h1 className="text-2xl font-bold">Category Management</h1>
        </div>
        <button className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors">
          Create Category
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Category Name</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Description</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Parent Category</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            <tr>
              <td className="px-6 py-4 text-center text-gray-500" colSpan={4}>No categories found. Create one to begin building the hierarchy.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
