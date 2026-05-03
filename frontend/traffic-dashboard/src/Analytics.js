import React, { useMemo } from 'react';
import { Bar, Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, PointElement, LineElement, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Tooltip, Legend);

const Analytics = ({ parkingData = [] }) => {
  const occupancy = useMemo(() => {
    // group by date (hour)
    const map = {};
    parkingData.forEach(r => {
      const d = new Date(r.timestamp || r.Time || Date.now());
      const key = d.toISOString().slice(0,13) + ':00';
      map[key] = map[key] || { total: 0, occupied: 0 };
      map[key].total += 1;
      if ((r.status || r.Status || '').toString().toLowerCase() === 'occupied') map[key].occupied += 1;
    });
    const labels = Object.keys(map).sort();
    const occ = labels.map(l => map[l].occupied);
    const total = labels.map(l => map[l].total);
    return { labels, occ, total };
  }, [parkingData]);

  const distData = useMemo(() => {
    const dists = parkingData.map(r => parseFloat(r.distance || r.Distance || r.Distance_cm || 0)).filter(x=>!isNaN(x));
    const buckets = [0,10,20,50,100,200,500];
    const counts = buckets.map((b,i)=> dists.filter(v=> v >= b && (i===buckets.length-1 || v < buckets[i+1])).length);
    return { labels: buckets.map(b=> String(b)), counts };
  }, [parkingData]);

  return (
    <div className="analytics">
      <h3>Analytics</h3>
      <div className="analytics-grid">
        <div className="card">
          <h4>Occupancy Over Time</h4>
          <Line data={{ labels: occupancy.labels, datasets:[{ label:'Occupied', data: occupancy.occ, borderColor:'#e74c3c', backgroundColor:'rgba(231,76,60,0.2)' }]}} />
        </div>

        <div className="card">
          <h4>Distance Distribution (buckets)</h4>
          <Bar data={{ labels: distData.labels, datasets:[{ label:'Count', data: distData.counts, backgroundColor:'#667eea' }]}} />
        </div>
      </div>
    </div>
  );
};

export default Analytics;
