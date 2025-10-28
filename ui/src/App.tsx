import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ReactFlowProvider } from 'reactflow';
import Dashboard from './components/Dashboard';
import WorkflowBuilder from './components/WorkflowBuilder';
import { LMConfigProvider } from './contexts/LMConfigContext';
import { GlobalToolsProvider } from './contexts/GlobalToolsContext';

import 'reactflow/dist/style.css';
import './index.css';

function App() {
  return (
    <LMConfigProvider>
      <GlobalToolsProvider>
        <Router>
          <div className="App bg-slate-50">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route
                path="/workflow/:id"
                element={
                  <ReactFlowProvider>
                    <WorkflowBuilder />
                  </ReactFlowProvider>
                }
              />
            </Routes>
          </div>
        </Router>
      </GlobalToolsProvider>
    </LMConfigProvider>
  );
}

export default App;