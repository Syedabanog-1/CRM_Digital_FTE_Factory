import React, { useState } from 'react';

const API_BASE = window.TECHCORP_API_URL || 'http://localhost:8000';

const CATEGORIES = [
  'Technical Support',
  'Billing',
  'Feature Request',
  'Bug Report',
  'General Inquiry',
];

const PRIORITIES = ['low', 'medium', 'high', 'urgent'];

function validate(form) {
  const errors = {};
  if (!form.name || form.name.length < 2) errors.name = 'Name must be at least 2 characters';
  if (!form.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
    errors.email = 'Please enter a valid email address';
  if (!form.subject || form.subject.length < 5) errors.subject = 'Subject must be at least 5 characters';
  if (!form.message || form.message.length < 10) errors.message = 'Message must be at least 10 characters';
  if (!CATEGORIES.includes(form.category)) errors.category = 'Please select a valid category';
  return errors;
}

export default function SupportForm() {
  const [form, setForm] = useState({
    name: '',
    email: '',
    subject: '',
    category: 'General Inquiry',
    priority: 'medium',
    message: '',
  });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [ticketStatus, setTicketStatus] = useState(null);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    if (errors[e.target.name]) {
      setErrors({ ...errors, [e.target.name]: undefined });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const validationErrors = validate(form);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setSubmitting(true);
    setErrors({});

    try {
      const res = await fetch(`${API_BASE}/support/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });

      if (!res.ok) {
        const err = await res.json();
        if (err.detail && Array.isArray(err.detail)) {
          const fieldErrors = {};
          err.detail.forEach((d) => {
            const field = d.loc?.[d.loc.length - 1];
            if (field) fieldErrors[field] = d.msg;
          });
          setErrors(fieldErrors);
        } else {
          setErrors({ _form: err.detail || 'Submission failed' });
        }
        return;
      }

      const data = await res.json();
      setResult(data);
    } catch (err) {
      setErrors({ _form: 'Network error. Please try again.' });
    } finally {
      setSubmitting(false);
    }
  };

  const checkStatus = async () => {
    if (!result?.ticket_id) return;
    try {
      const res = await fetch(`${API_BASE}/support/ticket/${result.ticket_id}`);
      if (res.ok) {
        setTicketStatus(await res.json());
      }
    } catch {
      /* ignore */
    }
  };

  const resetForm = () => {
    setForm({ name: '', email: '', subject: '', category: 'General Inquiry', priority: 'medium', message: '' });
    setResult(null);
    setTicketStatus(null);
    setErrors({});
  };

  if (result) {
    return (
      <div style={{ maxWidth: 480, margin: '0 auto', padding: 24, fontFamily: 'system-ui, sans-serif' }}>
        <div style={{ background: '#f0fdf4', border: '1px solid #86efac', borderRadius: 8, padding: 20 }}>
          <h3 style={{ color: '#166534', margin: '0 0 12px' }}>Request Received!</h3>
          <p><strong>Ticket ID:</strong> {result.ticket_id}</p>
          <p><strong>Status:</strong> {result.status}</p>
          <p>{result.message}</p>
          <p style={{ fontSize: 14, color: '#666' }}>Estimated response: {result.estimated_response_time}</p>
          <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
            <button onClick={checkStatus} style={btnStyle}>Check Status</button>
            <button onClick={resetForm} style={{ ...btnStyle, background: '#6b7280' }}>New Request</button>
          </div>
        </div>
        {ticketStatus && (
          <div style={{ marginTop: 16, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 16 }}>
            <h4 style={{ margin: '0 0 8px' }}>Ticket Status: {ticketStatus.status}</h4>
            {ticketStatus.messages?.map((m, i) => (
              <div key={i} style={{ padding: 8, background: m.role === 'agent' ? '#eff6ff' : '#fff', borderRadius: 4, marginBottom: 4 }}>
                <strong>{m.role}:</strong> {m.content}
                <div style={{ fontSize: 12, color: '#999' }}>{new Date(m.timestamp).toLocaleString()}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 480, margin: '0 auto', padding: 24, fontFamily: 'system-ui, sans-serif' }}>
      <h2 style={{ margin: '0 0 16px', fontSize: 22 }}>TechCorp Support</h2>
      <p style={{ color: '#666', marginBottom: 20 }}>How can we help you today?</p>
      {errors._form && <div style={{ background: '#fef2f2', color: '#991b1b', padding: 12, borderRadius: 6, marginBottom: 16 }}>{errors._form}</div>}
      <form onSubmit={handleSubmit}>
        <Field label="Name" name="name" value={form.name} onChange={handleChange} error={errors.name} placeholder="Your name" />
        <Field label="Email" name="email" type="email" value={form.email} onChange={handleChange} error={errors.email} placeholder="you@example.com" />
        <Field label="Subject" name="subject" value={form.subject} onChange={handleChange} error={errors.subject} placeholder="Brief description" />
        <div style={{ marginBottom: 14 }}>
          <label style={labelStyle}>Category</label>
          <select name="category" value={form.category} onChange={handleChange} style={inputStyle}>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          {errors.category && <span style={errStyle}>{errors.category}</span>}
        </div>
        <div style={{ marginBottom: 14 }}>
          <label style={labelStyle}>Priority</label>
          <select name="priority" value={form.priority} onChange={handleChange} style={inputStyle}>
            {PRIORITIES.map((p) => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
          </select>
        </div>
        <div style={{ marginBottom: 14 }}>
          <label style={labelStyle}>Message</label>
          <textarea name="message" value={form.message} onChange={handleChange} rows={5} style={{ ...inputStyle, resize: 'vertical' }} placeholder="Describe your issue in detail..." />
          {errors.message && <span style={errStyle}>{errors.message}</span>}
        </div>
        <button type="submit" disabled={submitting} style={{ ...btnStyle, width: '100%', opacity: submitting ? 0.6 : 1 }}>
          {submitting ? 'Submitting...' : 'Submit Request'}
        </button>
      </form>
    </div>
  );
}

function Field({ label, name, type = 'text', value, onChange, error, placeholder }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={labelStyle}>{label}</label>
      <input type={type} name={name} value={value} onChange={onChange} placeholder={placeholder} style={inputStyle} />
      {error && <span style={errStyle}>{error}</span>}
    </div>
  );
}

const labelStyle = { display: 'block', fontWeight: 600, marginBottom: 4, fontSize: 14 };
const inputStyle = { width: '100%', padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14, boxSizing: 'border-box' };
const errStyle = { color: '#dc2626', fontSize: 12, marginTop: 2, display: 'block' };
const btnStyle = { padding: '10px 20px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 14, fontWeight: 600 };
