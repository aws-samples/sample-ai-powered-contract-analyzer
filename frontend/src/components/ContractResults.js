import React, { useState, useEffect } from 'react';
import { fetchAuthSession } from 'aws-amplify/auth';
import ContractChat from './ContractChat';
import { awsConfig } from '../aws-config';
import './ContractResults.css';

const API_ENDPOINT = awsConfig.API.REST.ContractAnalyzer.endpoint.replace(/\/$/, '');

function ContractResults({ contractId }) {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchResults();
  }, [contractId]);

  const fetchResults = async () => {
    setLoading(true);
    setError('');

    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();

      const response = await fetch(
        `${API_ENDPOINT}/contracts/${contractId}/results`,
        {
          headers: {
            'Authorization': token
          }
        }
      );

      const data = await response.json();

      if (response.ok) {
        if (data.status === 'pending') {
          setError('Analysis is still in progress. Please wait...');
        } else {
          setResults(data);
        }
      } else {
        setError(data.error || 'Failed to fetch results');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading results...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!results || !results.analysis) {
    return null;
  }

  const { analysis } = results;

  return (
    <div className="results-container">
      <div className="card">
        <h2>{analysis.title || 'Contract Analysis Results'}</h2>
        <p className="file-name">File: {results.fileName}</p>
        
        <div className="confidence-score">
          Confidence Score: {(analysis.confidenceScore * 100).toFixed(0)}%
        </div>

        <section className="result-section">
          <h3>Executive Summary</h3>
          <p>{analysis.executiveSummary}</p>
        </section>

        <section className="result-section">
          <h3>Key Contract Terms</h3>
          <div className="terms-grid">
            <div className="term-item">
              <strong>Type:</strong> {analysis.keyTerms.contractType}
            </div>
            <div className="term-item">
              <strong>Value:</strong> {analysis.keyTerms.value}
            </div>
            <div className="term-item">
              <strong>Duration:</strong> {analysis.keyTerms.duration}
            </div>
          </div>
          <div className="parties">
            <strong>Parties:</strong>
            <ul>
              {analysis.keyTerms.parties.map((party, idx) => (
                <li key={idx}>{party}</li>
              ))}
            </ul>
          </div>
        </section>

        {analysis.keyCommitments && (
          <section className="result-section">
            <h3>Key Commitments</h3>
            <div className="commitments-grid">
              {analysis.keyCommitments.paymentTerms && (
                <div className="commitment-item">
                  <strong>Payment Terms:</strong>
                  <p>{analysis.keyCommitments.paymentTerms}</p>
                </div>
              )}
              {analysis.keyCommitments.packagingRequirements && (
                <div className="commitment-item">
                  <strong>Packaging Requirements:</strong>
                  <p>{analysis.keyCommitments.packagingRequirements}</p>
                </div>
              )}
              {analysis.keyCommitments.inventoryTargets && (
                <div className="commitment-item">
                  <strong>Inventory Targets:</strong>
                  <p>{analysis.keyCommitments.inventoryTargets}</p>
                </div>
              )}
              {analysis.keyCommitments.labelingSpecifications && (
                <div className="commitment-item">
                  <strong>Labeling Specifications:</strong>
                  <p>{analysis.keyCommitments.labelingSpecifications}</p>
                </div>
              )}
              {analysis.keyCommitments.portalRequirements && (
                <div className="commitment-item">
                  <strong>Portal Requirements:</strong>
                  <p>{analysis.keyCommitments.portalRequirements}</p>
                </div>
              )}
            </div>
          </section>
        )}

        <section className="result-section">
          <h3>Points of Contact</h3>
          <div className="contacts-list">
            {analysis.contacts.map((contact, idx) => (
              <div key={idx} className="contact-card">
                <div><strong>{contact.name}</strong></div>
                <div>{contact.role}</div>
                <div className="contact-info">{contact.contact}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="result-section">
          <h3>Action Items & Deadlines</h3>
          <div className="action-items">
            {analysis.actionItems.map((item, idx) => (
              <div key={idx} className="action-item">
                <div className="action-header">
                  <span className={`priority priority-${item.priority.toLowerCase()}`}>
                    {item.priority}
                  </span>
                  <span className="deadline">{item.deadline}</span>
                </div>
                <div className="action-description">{item.item}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="result-section">
          <h3>Risk Factors</h3>
          <ul className="risk-list">
            {analysis.riskFactors.map((risk, idx) => (
              <li key={idx} className="risk-item">{risk}</li>
            ))}
          </ul>
        </section>
      </div>

      {/* Chatbot Component */}
      <ContractChat contractId={contractId} />
    </div>
  );
}

export default ContractResults;
