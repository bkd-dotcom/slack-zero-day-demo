import React, { useState, useEffect, useMemo } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import './index.css'

// ----------------------------------------------------
// Icons
// ----------------------------------------------------
const SunIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="5"></circle>
    <line x1="12" y1="1" x2="12" y2="3"></line>
    <line x1="12" y1="21" x2="12" y2="23"></line>
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
    <line x1="1" y1="12" x2="3" y2="12"></line>
    <line x1="21" y1="12" x2="23" y2="12"></line>
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
  </svg>
)

const MoonIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
  </svg>
)

// ----------------------------------------------------
// Auth Overlay
// ----------------------------------------------------
function AuthOverlay({ onLogin }) {
  const [key, setKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!key.trim()) return;
    
    setLoading(true);
    setError(false);
    
    setTimeout(() => {
      onLogin();
    }, 1200);
  };

  return (
    <div className="auth-overlay">
      <div className="auth-modal">
        <div className="auth-header">
          <div className="auth-logo"></div>
          <h2>PatchGhost Access</h2>
          <p>Authenticate to view enterprise telemetry.</p>
        </div>
        <form onSubmit={handleSubmit} className="auth-form">
          <div className="input-group">
            <input 
              type="password" 
              placeholder="Enter Access Key (e.g. 'demo')" 
              value={key}
              onChange={(e) => setKey(e.target.value)}
              autoFocus
              disabled={loading}
            />
          </div>
          {error && <div className="auth-error">Authentication failed. Please verify your key.</div>}
          <button type="submit" disabled={loading || !key.trim()}>
            {loading ? 'Authenticating...' : 'Continue to Dashboard'}
          </button>
        </form>
      </div>
    </div>
  );
}

// ----------------------------------------------------
// Main Dashboard Application
// ----------------------------------------------------
function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return localStorage.getItem('sentinel_auth') === 'true';
  });
  
  const handleLogin = () => {
    localStorage.setItem('sentinel_auth', 'true');
    setIsAuthenticated(true);
  };

  const [theme, setTheme] = useState('dark');
  const [currentView, setCurrentView] = useState('overview'); // overview, topology, logs, settings
  
  const [data, setData] = useState({
    vulnerabilities: [],
    score: 100,
    last_scan_time: "Never",
    all_dependencies: {},
    scan_latency_ms: 0
  });
  const [loading, setLoading] = useState(true);
  const [connectionError, setConnectionError] = useState(false);
  const [expandedVuln, setExpandedVuln] = useState(null);
  const [expandedLog, setExpandedLog] = useState(null);

  // Apply Theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  // Poll backend
  useEffect(() => {
    if (!isAuthenticated) return;

    const fetchStatus = async () => {
      try {
        const response = await fetch('/api/status');
        const json = await response.json();
        setData(json);
        setLoading(false);
        setConnectionError(false);
      } catch (error) {
        console.error("Error fetching status:", error);
        setConnectionError(true);
        setLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  // Graph Data Processing
  const graphData = useMemo(() => {
    const nodes = [];
    const links = [];

    // Colors based on theme
    const rootColor = theme === 'dark' ? '#FFFFFF' : '#000000';
    const ecoColor = theme === 'dark' ? '#666666' : '#999999';
    const safeNodeColor = theme === 'dark' ? '#333333' : '#CCCCCC';
    const dangerNodeColor = theme === 'dark' ? '#E57373' : '#D32F2F';

    // Root
    nodes.push({ id: 'Root', name: 'slack-zero-day-demo', val: 5, color: rootColor });

    // Ecosystems
    const ecosystems = ['npm', 'PyPI', 'Go'];
    ecosystems.forEach(eco => {
      nodes.push({ id: eco, name: eco, val: 3, color: ecoColor });
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
          
          nodes.push({
            id: pkg,
            name: pkg,
            val: isVuln ? 4 : 2,
            color: isVuln ? dangerNodeColor : safeNodeColor
          });
          links.push({ source: eco, target: pkg });
        });
      });
    }

    return { nodes, links, totalNodes };
  }, [data, theme]);

  if (!isAuthenticated) {
    return <AuthOverlay onLogin={handleLogin} />;
  }

  if (loading) {
    return (
      <div className="full-screen-center">
        <div className="spinner"></div>
        <p className="loading-text">Initializing telemetry interface...</p>
      </div>
    );
  }

  if (connectionError) {
    return (
      <div className="full-screen-center error-state">
        <div className="error-icon">⚠️</div>
        <h3>Backend Offline</h3>
        <p>Could not connect to the PatchGhost API.</p>
        <p className="error-subtext">Start the backend with `python3 app.py` and this page will auto-reconnect.</p>
      </div>
    );
  }

  const { vulnerabilities, score, last_scan_time, scan_latency_ms } = data;
  const isSecure = score === 100;
  const nodeCount = graphData.totalNodes;

  // Render Views
  const renderOverview = () => {
    const bgColor = theme === 'dark' ? '#0a0a0a' : '#f7f7f7';
    const linkColor = theme === 'dark' ? '#222222' : '#e5e5e5';

    return (
      <div className="content-grid">
        <div className="threats-column">
          <div className="panel-header">
            <h3>Active Threats Overview</h3>
            <span className="badge-count">{vulnerabilities.length}</span>
          </div>
          
          <div className="panel-body">
            {vulnerabilities.length === 0 ? (
              <div className="empty-state">
                No vulnerabilities detected in the current state.
              </div>
            ) : (
              <div className="vuln-list">
                {vulnerabilities.map((v, i) => (
                  <div className="vuln-card" key={i}>
                    <div className="vuln-header">
                      <h4>{v.name} <span className="vuln-version">{v.version}</span></h4>
                      <div>
                        <span className="badge badge-danger" style={{marginRight: '8px'}}>{v.latest_id}</span>
                        <span className="badge" style={{backgroundColor: '#f39c12', color: '#fff'}}>{v.vuln_count} Advisories</span>
                      </div>
                    </div>
                    <p className="vuln-desc">{v.summary}</p>
                    
                    {v.ai_threat_analysis && (
                      <div className="ai-analysis-block">
                        <button 
                          className="ai-toggle-btn"
                          onClick={() => setExpandedVuln(expandedVuln === i ? null : i)}
                        >
                          {expandedVuln === i ? '− Hide Analysis' : '+ View AI Threat Analysis (Gemini 2.0 Flash)'}
                        </button>
                        {expandedVuln === i && (
                          <div className="ai-content">
                            <p>{v.ai_threat_analysis}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="topology-column">
          <div className="panel-header">
            <h3>Dependency Topology</h3>
          </div>
          <div className="panel-body graph-wrapper">
            <ForceGraph2D
              graphData={graphData}
              width={600} 
              height={350}
              nodeLabel="name"
              nodeColor="color"
              nodeRelSize={4}
              linkColor={() => linkColor}
              backgroundColor={bgColor}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
            />
          </div>
        </div>
      </div>
    );
  };

  const renderTopology = () => {
    const bgColor = theme === 'dark' ? '#0a0a0a' : '#f7f7f7';
    const linkColor = theme === 'dark' ? '#222222' : '#e5e5e5';

    return (
      <div className="topology-column">
        <div className="panel-header">
          <h3>Dependency Topology</h3>
        </div>
        <div className="panel-body graph-wrapper full-height">
          <ForceGraph2D
            graphData={graphData}
            width={1000} 
            height={450}
            nodeLabel="name"
            nodeColor="color"
            nodeRelSize={4}
            linkColor={() => linkColor}
            backgroundColor={bgColor}
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.3}
          />
        </div>
      </div>
    );
  };

  const logsToRender = data.incident_logs || [];

  const renderLogs = () => (
    <div className="logs-column">
      <div className="panel-header">
        <h3>Incident Logs</h3>
      </div>
      <div className="panel-body">
        {logsToRender.length === 0 ? (
          <div className="empty-state">No historical incidents logged.</div>
        ) : (
          <table className="logs-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Ecosystem</th>
                <th>Package</th>
                <th>Vulnerability ID</th>
                <th>Advisories Found</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {logsToRender.map((v, i) => (
                <React.Fragment key={i}>
                  <tr style={{cursor: 'pointer'}} onClick={() => setExpandedLog(expandedLog === i ? null : i)}>
                    <td className="log-time">{v.caught_time}</td>
                    <td>{v.ecosystem}</td>
                    <td className="log-pkg">{v.name} ({v.version})</td>
                    <td className="log-id">{v.latest_id}</td>
                    <td className="log-count"><strong>{v.vuln_count}</strong></td>
                    <td><span className={v.status === 'Unresolved' ? 'badge badge-danger' : 'badge badge-success'}>{v.status}</span></td>
                  </tr>
                  {expandedLog === i && (
                    <tr className="log-expansion-row">
                      <td colSpan="6" style={{padding: '16px', backgroundColor: theme === 'dark' ? '#1a1a1a' : '#f9f9f9', borderLeft: '3px solid #E57373', textAlign: 'left'}}>
                        <div style={{display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.9em'}}>
                          <div><strong style={{color: '#E57373'}}>Slack Alert Timestamp:</strong> {v.caught_time}</div>
                          <div><strong style={{color: '#E57373'}}>Vulnerability Summary:</strong> {v.summary}</div>
                          <div><strong style={{color: '#E57373'}}>AI Threat Analysis:</strong> <em>{v.ai_threat_analysis}</em></div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );

  const renderSettings = () => (
    <div className="settings-column">
      <div className="panel-header">
        <h3>System Settings</h3>
      </div>
      <div className="panel-body settings-list">
        <div className="setting-item">
          <div className="setting-info">
            <h4>Proactive Scanner Daemon</h4>
            <p>Continuously scans package manifests in the background.</p>
          </div>
          <div className="setting-action">
            <span className="badge badge-success">Active</span>
          </div>
        </div>
        <div className="setting-item">
          <div className="setting-info">
            <h4>Zero-Touch PR Creation</h4>
            <p>Automatically opens patched pull requests on GitHub.</p>
          </div>
          <div className="setting-action">
            <span className="badge badge-success">Enabled</span>
          </div>
        </div>
        <div className="setting-item">
          <div className="setting-info">
            <h4>AI Threat Analysis</h4>
            <p>Model engine used for security context generation.</p>
          </div>
          <div className="setting-action">
            <span className="setting-value">Gemini 2.0 Flash</span>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="dashboard-layout">
      
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-logo"></div>
          <div>
            <h1>PatchGhost</h1>
            <span>Autonomous DevSecOps</span>
          </div>
        </div>
        <nav className="sidebar-nav">
          <button 
            className={`nav-item ${currentView === 'overview' ? 'active' : ''}`}
            onClick={() => setCurrentView('overview')}
          >
            Overview
          </button>
          <button 
            className={`nav-item ${currentView === 'topology' ? 'active' : ''}`}
            onClick={() => setCurrentView('topology')}
          >
            Topology Map
          </button>
          <button 
            className={`nav-item ${currentView === 'logs' ? 'active' : ''}`}
            onClick={() => setCurrentView('logs')}
          >
            Incident Logs
          </button>
          <button 
            className={`nav-item ${currentView === 'settings' ? 'active' : ''}`}
            onClick={() => setCurrentView('settings')}
          >
            Settings
          </button>
        </nav>
        <div className="sidebar-footer">
          <div className="status-indicator">
            <span className="dot pulse-green"></span> System Online
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        
        {/* Top Bar with Theme Toggle */}
        <div className="top-bar">
          <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle Theme">
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>
        </div>

        <header className="page-header">
          <h2>
            {currentView === 'overview' && 'Security Overview'}
            {currentView === 'topology' && 'Network Topology'}
            {currentView === 'logs' && 'Incident Audit Logs'}
            {currentView === 'settings' && 'Configuration'}
          </h2>
          <p>
            {currentView === 'overview' && 'Real-time dependency analysis and autonomous remediation engine.'}
            {currentView === 'topology' && 'Visual representation of all monitored dependencies across ecosystems.'}
            {currentView === 'logs' && 'Historical log of detected vulnerabilities and actions taken.'}
            {currentView === 'settings' && 'Manage PatchGhost daemon and automation preferences.'}
          </p>
        </header>

        {/* Sharp Telemetry Grid */}
        <div className="telemetry-grid">
          <div className="stat-card">
            <div className="stat-label">Security Score</div>
            <div className={`stat-value ${isSecure ? 'color-success' : 'color-danger'}`}>
              {score}/100
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Scan Latency</div>
            <div className="stat-value">{scan_latency_ms > 0 ? `${scan_latency_ms}ms` : '—'}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Nodes Monitored</div>
            <div className="stat-value">{nodeCount}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Last Synchronization</div>
            <div className="stat-value text-small">{last_scan_time}</div>
          </div>
        </div>

        <div className="view-container">
          {currentView === 'overview' && renderOverview()}
          {currentView === 'topology' && renderTopology()}
          {currentView === 'logs' && renderLogs()}
          {currentView === 'settings' && renderSettings()}
        </div>
      </main>
    </div>
  )
}

export default App
