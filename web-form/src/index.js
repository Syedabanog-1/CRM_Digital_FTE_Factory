import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const targetId = window.TECHCORP_FORM_TARGET || 'techcorp-support-form';
const target = document.getElementById(targetId);

if (target) {
  const root = ReactDOM.createRoot(target);
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}
