import React, { useState, useEffect } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
  BarControllerChartOptions,
  LineControllerChartOptions
} from 'chart.js';
import { Bar, Line } from 'react-chartjs-2';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend
);

// Types for API responses
interface ScoreBucket {
  bucket: string;
  count: number;
}

interface PassRateEntry {
  task: string;
  avg_score: number;
  attempts: number;
}

interface TimelineEntry {
  date: string;
  submissions: number;
}

// Chart data types
interface BarChartData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    backgroundColor: string;
    borderColor: string;
    borderWidth: number;
  }>;
}

interface LineChartData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    fill: boolean;
    borderColor: string;
    tension: number;
    pointBackgroundColor: string;
    pointBorderColor: string;
    pointHoverBackgroundColor: string;
    pointHoverBorderColor: string;
  }>;
}

type LabOption = 'lab-01' | 'lab-02' | 'lab-03' | 'lab-04' | 'lab-05';

interface LoadingState {
  scores: boolean;
  passRates: boolean;
  timeline: boolean;
}

interface ErrorState {
  scores: string | null;
  passRates: string | null;
  timeline: string | null;
}

const DASHBOARD_STYLES = {
  container: { padding: '20px' } as React.CSSProperties,
  section: { marginBottom: '40px', height: '400px' } as React.CSSProperties,
  tableSection: { marginBottom: '40px' } as React.CSSProperties,
  errorText: { color: 'red' } as React.CSSProperties,
  select: { padding: '8px', marginLeft: '10px' } as React.CSSProperties,
  table: { width: '100%', borderCollapse: 'collapse' as const },
  th: { border: '1px solid #ddd', padding: '12px', textAlign: 'left' as const, backgroundColor: '#f2f2f2' },
  td: { border: '1px solid #ddd', padding: '8px' },
  labelSection: { marginBottom: '20px' } as React.CSSProperties,
};

const chartOptions: ChartOptions<'bar' | 'line'> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
    },
  },
};

const Dashboard: React.FC = () => {
  const [selectedLab, setSelectedLab] = useState<LabOption>('lab-04');
  const [scoresData, setScoresData] = useState<ScoreBucket[]>([]);
  const [passRatesData, setPassRatesData] = useState<PassRateEntry[]>([]);
  const [timelineData, setTimelineData] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState<LoadingState>({
    scores: true,
    passRates: true,
    timeline: true
  });
  const [error, setError] = useState<ErrorState>({
    scores: null,
    passRates: null,
    timeline: null
  });

  // Get API token from localStorage
  const getToken = (): string | null => {
    return localStorage.getItem('api_key');
  };

  // Fetch data from API
  const fetchData = async (lab: LabOption): Promise<void> => {
    const token = getToken();
    if (!token) {
      setError({
        scores: 'No API token found',
        passRates: 'No API token found',
        timeline: 'No API token found'
      });
      setLoading({ scores: false, passRates: false, timeline: false });
      return;
    }

    const headers: HeadersInit = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };

    // Fetch scores
    setLoading(prev => ({ ...prev, scores: true }));
    try {
      const scoresResponse = await fetch(`/analytics/scores?lab=${lab}`, { headers });
      if (!scoresResponse.ok) {
        throw new Error(`HTTP error! status: ${scoresResponse.status}`);
      }
      const scores: ScoreBucket[] = await scoresResponse.json();
      setScoresData(scores);
      setError(prev => ({ ...prev, scores: null }));
    } catch (err) {
      setError(prev => ({ ...prev, scores: err instanceof Error ? err.message : 'Unknown error' }));
    } finally {
      setLoading(prev => ({ ...prev, scores: false }));
    }

    // Fetch pass rates
    setLoading(prev => ({ ...prev, passRates: true }));
    try {
      const passRatesResponse = await fetch(`/analytics/pass-rates?lab=${lab}`, { headers });
      if (!passRatesResponse.ok) {
        throw new Error(`HTTP error! status: ${passRatesResponse.status}`);
      }
      const passRates: PassRateEntry[] = await passRatesResponse.json();
      setPassRatesData(passRates);
      setError(prev => ({ ...prev, passRates: null }));
    } catch (err) {
      setError(prev => ({ ...prev, passRates: err instanceof Error ? err.message : 'Unknown error' }));
    } finally {
      setLoading(prev => ({ ...prev, passRates: false }));
    }

    // Fetch timeline
    setLoading(prev => ({ ...prev, timeline: true }));
    try {
      const timelineResponse = await fetch(`/analytics/timeline?lab=${lab}`, { headers });
      if (!timelineResponse.ok) {
        throw new Error(`HTTP error! status: ${timelineResponse.status}`);
      }
      const timeline: TimelineEntry[] = await timelineResponse.json();
      setTimelineData(timeline);
      setError(prev => ({ ...prev, timeline: null }));
    } catch (err) {
      setError(prev => ({ ...prev, timeline: err instanceof Error ? err.message : 'Unknown error' }));
    } finally {
      setLoading(prev => ({ ...prev, timeline: false }));
    }
  };

  // Load data when lab changes
  useEffect(() => {
    fetchData(selectedLab);
  }, [selectedLab]);

  // Prepare bar chart data
  const barChartData: BarChartData = {
    labels: scoresData.map(item => item.bucket),
    datasets: [
      {
        label: 'Number of Submissions',
        data: scoresData.map(item => item.count),
        backgroundColor: 'rgba(75, 192, 192, 0.6)',
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1,
      },
    ],
  };

  // Prepare line chart data
  const lineChartData: LineChartData = {
    labels: timelineData.map(item => item.date),
    datasets: [
      {
        label: 'Submissions per Day',
        data: timelineData.map(item => item.submissions),
        fill: false,
        borderColor: 'rgb(75, 192, 192)',
        tension: 0.1,
        pointBackgroundColor: 'rgb(75, 192, 192)',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: 'rgb(75, 192, 192)',
      },
    ],
  };

  return (
    <div style={DASHBOARD_STYLES.container}>
      <h1>Learning Analytics Dashboard</h1>

      {/* Lab selector */}
      <div style={DASHBOARD_STYLES.labelSection}>
        <label htmlFor="lab-select">Select Lab: </label>
        <select
          id="lab-select"
          value={selectedLab}
          onChange={(e) => setSelectedLab(e.target.value as LabOption)}
          style={DASHBOARD_STYLES.select}
        >
          <option value="lab-01">Lab 01</option>
          <option value="lab-02">Lab 02</option>
          <option value="lab-03">Lab 03</option>
          <option value="lab-04">Lab 04</option>
          <option value="lab-05">Lab 05</option>
        </select>
      </div>

      {/* Score Distribution Chart */}
      <div style={DASHBOARD_STYLES.section}>
        <h2>Score Distribution</h2>
        {loading.scores && <p>Loading scores data...</p>}
        {error.scores && <p style={DASHBOARD_STYLES.errorText}>Error: {error.scores}</p>}
        {!loading.scores && !error.scores && scoresData.length > 0 && (
          <Bar data={barChartData} options={chartOptions as BarControllerChartOptions} />
        )}
        {!loading.scores && !error.scores && scoresData.length === 0 && (
          <p>No score data available for this lab</p>
        )}
      </div>

      {/* Timeline Chart */}
      <div style={DASHBOARD_STYLES.section}>
        <h2>Submissions Over Time</h2>
        {loading.timeline && <p>Loading timeline data...</p>}
        {error.timeline && <p style={DASHBOARD_STYLES.errorText}>Error: {error.timeline}</p>}
        {!loading.timeline && !error.timeline && timelineData.length > 0 && (
          <Line data={lineChartData} options={chartOptions as LineControllerChartOptions} />
        )}
        {!loading.timeline && !error.timeline && timelineData.length === 0 && (
          <p>No timeline data available for this lab</p>
        )}
      </div>

      {/* Pass Rates Table */}
      <div style={DASHBOARD_STYLES.tableSection}>
        <h2>Task Pass Rates</h2>
        {loading.passRates && <p>Loading pass rates data...</p>}
        {error.passRates && <p style={DASHBOARD_STYLES.errorText}>Error: {error.passRates}</p>}
        {!loading.passRates && !error.passRates && passRatesData.length > 0 && (
          <table style={DASHBOARD_STYLES.table}>
            <thead>
              <tr>
                <th style={DASHBOARD_STYLES.th}>Task</th>
                <th style={DASHBOARD_STYLES.th}>Average Score (%)</th>
                <th style={DASHBOARD_STYLES.th}>Number of Attempts</th>
              </tr>
            </thead>
            <tbody>
              {passRatesData.map((item) => (
                <tr key={item.task}>
                  <td style={DASHBOARD_STYLES.td}>{item.task}</td>
                  <td style={DASHBOARD_STYLES.td}>{item.avg_score.toFixed(1)}%</td>
                  <td style={DASHBOARD_STYLES.td}>{item.attempts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!loading.passRates && !error.passRates && passRatesData.length === 0 && (
          <p>No pass rates data available for this lab</p>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
