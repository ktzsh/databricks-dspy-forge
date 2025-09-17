import React from 'react';
import { ReactFlowProvider } from 'reactflow';
import WorkflowBuilder from './components/WorkflowBuilder';

import 'reactflow/dist/style.css';
import './index.css';

function App() {
  return (
    <div className="App">
      <ReactFlowProvider>
        <WorkflowBuilder />
      </ReactFlowProvider>
    </div>
  );
}

export default App;