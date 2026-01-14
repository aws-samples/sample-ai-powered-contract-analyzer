import React, { useState } from 'react';
import { Amplify } from 'aws-amplify';
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import { awsConfig } from './aws-config';
import ContractUpload from './components/ContractUpload';
import ContractList from './components/ContractList';
import ContractResults from './components/ContractResults';
import './App.css';

Amplify.configure(awsConfig);

function App() {
  const [selectedContractId, setSelectedContractId] = useState(null);
  const [refreshList, setRefreshList] = useState(0);

  const handleUploadSuccess = () => {
    // Refresh the contract list after successful upload
    setRefreshList(prev => prev + 1);
    setSelectedContractId(null);
  };

  const handleSelectContract = (contractId) => {
    setSelectedContractId(contractId);
  };

  const handleBackToList = () => {
    setSelectedContractId(null);
  };

  return (
    <Authenticator>
      {({ signOut, user }) => (
        <div className="app">
          <header className="app-header">
            <h1>AI Powered Contract Analyzer</h1>
            <div className="user-info">
              <span>Welcome, {user.signInDetails?.loginId}</span>
              <button onClick={signOut} className="btn-secondary">Sign Out</button>
            </div>
          </header>
          
          <main className="app-main">
            <div className="container">
              {!selectedContractId ? (
                <>
                  <ContractUpload onUploadSuccess={handleUploadSuccess} />
                  <ContractList 
                    key={refreshList}
                    onSelectContract={handleSelectContract} 
                  />
                </>
              ) : (
                <>
                  <button onClick={handleBackToList} className="btn-back">
                    ← Back to List
                  </button>
                  <ContractResults contractId={selectedContractId} />
                </>
              )}
            </div>
          </main>
        </div>
      )}
    </Authenticator>
  );
}

export default App;
