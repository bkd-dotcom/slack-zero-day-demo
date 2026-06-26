import { useState, useEffect, useMemo } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import './index.css'

function App() {
  const [data, setData] = useState({
    vulnerabilities: [],
    score: 100,
    last_scan_time: "Never",
    all_dependencies: {},
    scan_latency_ms: 0
  });
  const [loading, setLoading] = useState(true);
  const [connectionError, setConnectionError] = useState(false);
  const [failCount, setFailCount] = useState(0);
  const [theme, setTheme] = useState('dark');
  const [expandedVuln, setExpandedVuln] = useState(null);

  // Handle theme switching
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/status');
        const json = await response.json();
        setData(json);
        setLoading(false);
        setConnectionError(false);
        setFailCount(0);
      } catch (error) {
        console.error("Error fetching status:", error);
        setFailCount(prev => {
          const next = prev + 1;
          if (next >= 3) {
            setConnectionError(true);
            setLoading(false);
          }
          return next;
        });
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const isDark = theme === 'dark';

  const graphData = useMemo(() => {
    const nodes = [];
    const links = [];

    // Root
    nodes.push({ id: 'Root', name: 'slack-zero-day-demo', val: 5, color: isDark ? '#EFEFEF' : '#1C1C1C' });

    // Ecosystems
    const ecosystems = ['npm', 'PyPI', 'Go'];
    ecosystems.forEach(eco => {
      nodes.push({ id: eco, name: eco, val: 3, color: isDark ? '#888888' : '#666666' });
      links.push({ source: 'Root', target: eco });
    });

    const vulnNames = data.vulnerabilities.map(v => v.name);
    let totalNodes = 4;

    if (data.all_dependencies) {
      Object.entries(data.all_dependencies).forEach(([eco, pkgs]) => {
        if (!pkgs) return;
        Object.entries(pkgs).forEach(([pkg, ver]) => {
          totalNodes++;
          const isVuln = vulnNames.includes(pkg);
          
          let nodeColor;
          if (isVuln) {
            nodeColor = isDark ? '#FCA5A5' : '#B91C1C';
          } else {
            nodeColor = isDark ? '#555555' : '#999999';
          }

          nodes.push({
            id: pkg,
            name: pkg,
            val: isVuln ? 4 : 2,
            color: nodeColor
          });
          links.push({ source: eco, target: pkg });
        });
      });
    }

    return { nodes, links, totalNodes };
  }, [data, isDark]);

  if (loading) {
    return <div className="loading">Initializing Telemetry...</div>;
  }

  if (connectionError) {
    return (
      <div className="loading">
        <div style={{fontSize: '2rem', marginBottom: '16px'}}>⚠️</div>
        <div style={{fontStyle: 'normal', fontFamily: 'var(--font-sans)', fontWeight: 500}}>Backend Offline</div>
        <div style={{marginTop: '12px', fontSize: '0.9rem', color: 'var(--text-muted)', maxWidth: '400px', lineHeight: 1.6}}>
          Could not connect to the Sentinel API at <code>localhost:5000</code>.<br/>
          Start the backend with <code>python3 app.py</code> and this page will auto-reconnect.
        </div>
      </div>
    );
  }

  const { vulnerabilities, score, last_scan_time, scan_latency_ms } = data;
  const isSecure = score === 100;
  const nodeCount = graphData.totalNodes;

  return (
    <div className="app-container">
      
      <button className="theme-toggle" onClick={toggleTheme}>
        {isDark ? '☀️ Light Mode' : '🌙 Dark Mode'}
      </button>

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand">
          <h1>Sentinel</h1>
          <span>Autonomous DevSecOps</span>
        </div>
        <nav>
          <div className="nav-item active">Dashboard</div>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="page-header">
          <h2>Overview</h2>
          <p>Real-time dependency analysis and autonomous remediation.</p>
        </header>

        {/* Telemetry Grid */}
        <div className="telemetry-grid">
          <div className="stat-box">
            <div className="stat-label">Security Score</div>
            <div className={`stat-value ${isSecure ? 'success' : 'danger'}`}>
              {score}/100
            </div>
          </div>
          <div className="stat-box">
            <div className="stat-label">Scan Latency</div>
            <div className="stat-value">{scan_latency_ms > 0 ? `${scan_latency_ms}ms` : '—'}</div>
          </div>
          <div className="stat-box">
            <div className="stat-label">Nodes Monitored</div>
            <div className="stat-value">{nodeCount}</div>
          </div>
          <div className="stat-box">
            <div className="stat-label">Last Synchronization</div>
            <div className="stat-value" style={{fontSize: '0.9rem', lineHeight: '2.5'}}>
              {last_scan_time}
            </div>
          </div>
        </div>

        {/* Network Graph Panel */}
        <div className="panel">
          <div className="panel-header">Topology Map</div>
          <div className="graph-container" style={{ height: '350px' }}>
            <ForceGraph2D
              graphData={graphData}
              width={900}
              height={350}
              nodeLabel="name"
              nodeColor="color"
              nodeRelSize={5}
              linkColor={() => isDark ? '#333333' : '#E6E4DD'}
              backgroundColor={isDark ? '#121212' : '#F9F8F6'}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
            />
          </div>
        </div>

        {/* Vulnerabilities Panel */}
        <div className="panel">
          <div className="panel-header">Active Threats</div>
          
          {vulnerabilities.length === 0 ? (
            <div style={{color: 'var(--success-text)', fontFamily: 'var(--font-mono)'}}>
              [SYS] No vulnerabilities detected in current state.
            </div>
          ) : (
            <div className="vuln-list">
              {vulnerabilities.map((v, i) => (
                <div className="vuln-item" key={i}>
                  <div className="vuln-main">
                    <h3>{v.name} ({v.version})</h3>
                    <p className="vuln-desc">{v.summary}</p>
                    {v.ai_threat_analysis && (
                      <div className="ai-analysis">
                        <button 
                          className="ai-toggle"
                          onClick={() => setExpandedVuln(expandedVuln === i ? null : i)}
                        >
                          🤖 {expandedVuln === i ? 'Hide' : 'View'} AI Threat Analysis
                        </button>
                        {expandedVuln === i && (
                          <p className="ai-text">{v.ai_threat_analysis}</p>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="vuln-meta">
                    <span className="badge">{v.latest_id}</span>
                    <span className="badge">{v.ecosystem}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </main>
    </div>
  )
}

export default App
