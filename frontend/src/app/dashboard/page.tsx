import Link from 'next/link';
import LogoutButton from '@/components/LogoutButton';

export default function DashboardPage() {
  return (
    <div className="container">
      <header className="dashboard-header">
        <div>
          <h1>Dashboard</h1>
          <p>Overview of your enterprise metrics</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Link href="/" className="back-link">
            &larr; Back to Home
          </Link>
          <LogoutButton />
        </div>
      </header>
      
      <div className="metric-grid">
        {['Total Revenue', 'Active Users', 'Inventory Items'].map((metric) => (
          <div key={metric} className="metric-card">
            <h3>{metric}</h3>
            <p>{metric === 'Total Revenue' ? '$1.2M' : metric === 'Active Users' ? '1,492' : '8,394'}</p>
          </div>
        ))}
      </div>

      <div className="activity-card">
        <h2>Recent Activity</h2>
        <div className="activity-list">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="activity-item">
              <div className="avatar">{i}</div>
              <div className="activity-details">
                <p>Activity item {i}</p>
                <p className="time">2 hours ago</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
