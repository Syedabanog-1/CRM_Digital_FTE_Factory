import React from 'react';
import ReactDOM from 'react-dom/client';
import SupportForm from './SupportForm';

// Render the support form into any target element
const targetId = window.TECHCORP_FORM_TARGET || 'techcorp-support-form';
const target = document.getElementById(targetId);

if (target) {
  const root = ReactDOM.createRoot(target);
  root.render(
    <React.StrictMode>
      <SupportForm />
    </React.StrictMode>
  );
}
