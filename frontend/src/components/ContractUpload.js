import React, { useState } from 'react';
import { fetchAuthSession } from 'aws-amplify/auth';
import { uploadData } from 'aws-amplify/storage';
import { awsConfig } from '../aws-config';
import './ContractUpload.css';

const API_ENDPOINT = awsConfig.API.REST.ContractAnalyzer.endpoint.replace(/\/$/, '');

function ContractUpload({ onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [contractId, setContractId] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setError('');
      setMessage('');
    } else {
      setError('Please select a valid PDF file');
      setFile(null);
    }
  };

  const uploadContract = async () => {
    if (!file) return;

    setUploading(true);
    setUploadProgress(0);
    setError('');
    setMessage('');
    setContractId(null);

    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();

      // Step 1: Get S3 upload details
      const response = await fetch(`${API_ENDPOINT}/contracts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token
        },
        body: JSON.stringify({
          fileName: file.name,
          fileSize: file.size
        })
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || 'Failed to initiate upload');
        return;
      }

      // Step 2: Upload directly to S3 using Amplify Storage with progress tracking
      const upload = uploadData({
        path: data.s3Key,
        data: file,
        options: {
          contentType: 'application/pdf',
          onProgress: ({ transferredBytes, totalBytes }) => {
            if (totalBytes) {
              const percentage = Math.round((transferredBytes / totalBytes) * 100);
              setUploadProgress(percentage);
            }
          }
        }
      });

      await upload.result;

      // Upload complete - analysis will happen automatically
      setMessage('Contract uploaded successfully! Analysis will begin automatically.');
      setContractId(data.contractId);
      setFile(null);
      onUploadSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };



  return (
    <div className="card upload-card">
      <h2>Upload Contract</h2>
      
      {error && <div className="error">{error}</div>}
      {message && <div className="success">{message}</div>}
      
      {uploading && uploadProgress > 0 && (
        <div className="progress-container">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <div className="progress-text">{uploadProgress}% uploaded</div>
        </div>
      )}

      <div className="upload-section">
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          disabled={uploading || analyzing}
          className="file-input"
        />
        
        {file && (
          <div className="file-info">
            <p>Selected: {file.name}</p>
            <p>Size: {(file.size / 1024 / 1024).toFixed(2)} MB</p>
          </div>
        )}

        <div className="button-group">
          <button
            onClick={uploadContract}
            disabled={!file || uploading}
            className="btn-primary"
          >
            {uploading ? 'Uploading...' : 'Upload Contract'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ContractUpload;
