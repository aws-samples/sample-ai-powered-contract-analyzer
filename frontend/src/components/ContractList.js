import React, { useState, useEffect } from 'react';
import { fetchAuthSession } from 'aws-amplify/auth';
import { awsConfig } from '../aws-config';
import './ContractList.css';

const API_ENDPOINT = awsConfig.API.REST.ContractAnalyzer.endpoint.replace(/\/$/, '');

function ContractList({ onSelectContract }) {
  const [contracts, setContracts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchContracts();
    // Auto-refresh every 10 seconds to show status updates
    const interval = setInterval(fetchContracts, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchContracts = async () => {
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();

      const response = await fetch(`${API_ENDPOINT}/contracts`, {
        headers: {
          'Authorization': token
        }
      });

      const data = await response.json();

      if (response.ok) {
        setContracts(data.contracts || []);
        setError('');
      } else {
        setError(data.error || 'Failed to fetch contracts');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      uploaded: { label: 'Uploaded', className: 'status-uploaded' },
      processing: { label: 'Processing...', className: 'status-processing' },
      analyzed: { label: 'Completed', className: 'status-completed' },
      failed: { label: 'Failed', className: 'status-failed' }
    };

    const config = statusConfig[status] || { label: status, className: 'status-unknown' };
    return <span className={`status-badge ${config.className}`}>{config.label}</span>;
  };

  const formatDate = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  if (loading) {
    return <div className="loading">Loading contracts...</div>;
  }

  return (
    <div className="card contract-list-card">
      <div className="list-header">
        <h2>Your Contracts</h2>
        <button onClick={fetchContracts} className="btn-refresh">
          ↻ Refresh
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {contracts.length === 0 ? (
        <div className="empty-state">
          <p>No contracts uploaded yet.</p>
          <p>Upload a PDF contract to get started!</p>
        </div>
      ) : (
        <div className="contracts-table">
          <table>
            <thead>
              <tr>
                <th>File Name</th>
                <th>Upload Date</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {contracts.map((contract) => (
                <tr key={contract.contractId}>
                  <td className="file-name-cell">
                    <span className="file-icon">📄</span>
                    <div className="file-info">
                      {contract.analysis?.title ? (
                        <>
                          <div className="contract-title">{contract.analysis.title}</div>
                          <div className="file-name-small">{contract.fileName}</div>
                        </>
                      ) : (
                        <div>{contract.fileName}</div>
                      )}
                    </div>
                  </td>
                  <td>{formatDate(contract.timestamp)}</td>
                  <td>{getStatusBadge(contract.status)}</td>
                  <td>
                    {contract.status === 'analyzed' ? (
                      <button
                        onClick={() => onSelectContract(contract.contractId)}
                        className="btn-view"
                      >
                        View Details
                      </button>
                    ) : contract.status === 'processing' ? (
                      <span className="processing-text">Processing...</span>
                    ) : (
                      <span className="pending-text">Pending</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default ContractList;
