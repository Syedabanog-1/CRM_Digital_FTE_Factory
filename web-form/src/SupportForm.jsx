import React, { useState } from 'react';

const API_BASE = window.TECHCORP_API_URL !== undefined ? window.TECHCORP_API_URL : '';

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

export default function SupportForm({ token, user, onLogout }) {
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

  const authHeaders = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

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
        headers: authHeaders,
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
    } catch {
      setErrors({ _form: 'Network error. Please try again.' });
    } finally {
      setSubmitting(false);
    }
  };

  const checkStatus = async () => {
    if (!result?.ticket_id) return;
    try {
      const res = await fetch(`${API_BASE}/support/ticket/${result.ticket_id}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">TechCorp Support</h1>
            {user && <p className="text-sm text-gray-500">Welcome, {user.name}</p>}
          </div>
          {onLogout && (
            <button
              onClick={onLogout}
              className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
            >
              Logout
            </button>
          )}
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        {result ? (
          /* Success state */
          <div className="bg-white rounded-xl shadow-lg overflow-hidden">
            <div className="h-2 bg-gradient-to-r from-green-500 to-green-400" />
            <div className="p-8">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h2 className="text-xl font-bold text-gray-900">Request Received</h2>
              </div>

              <div className="space-y-2 mb-6">
                <p className="text-sm text-gray-600">
                  <span className="font-medium text-gray-900">Ticket ID:</span> {result.ticket_id}
                </p>
                <p className="text-sm text-gray-600">
                  <span className="font-medium text-gray-900">Status:</span> {result.status}
                </p>
                <p className="text-sm text-gray-700">{result.message}</p>
                <p className="text-xs text-gray-400">Estimated response: {result.estimated_response_time}</p>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={checkStatus}
                  className="px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition"
                >
                  Check Status
                </button>
                <button
                  onClick={resetForm}
                  className="px-5 py-2.5 bg-gray-500 text-white text-sm font-semibold rounded-lg hover:bg-gray-600 transition"
                >
                  New Request
                </button>
              </div>
            </div>

            {ticketStatus && (
              <div className="border-t border-gray-200 p-8">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Ticket Status: {ticketStatus.status}
                </h3>
                <div className="space-y-3">
                  {ticketStatus.messages?.map((m, i) => (
                    <div
                      key={i}
                      className={`p-4 rounded-lg ${m.role === 'agent' ? 'bg-blue-50 border border-blue-100' : 'bg-gray-50 border border-gray-100'}`}
                    >
                      <p className="text-sm">
                        <span className="font-medium capitalize">{m.role}:</span> {m.content}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {new Date(m.timestamp).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Form */
          <div className="bg-white rounded-xl shadow-lg overflow-hidden">
            <div className="h-2 bg-gradient-to-r from-blue-600 to-blue-400" />
            <div className="p-8">
              <div className="mb-6">
                <h2 className="text-xl font-bold text-gray-900">Submit a Support Request</h2>
                <p className="text-gray-500 text-sm mt-1">How can we help you today?</p>
              </div>

              {errors._form && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
                  {errors._form}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                    <input
                      type="text"
                      name="name"
                      value={form.name}
                      onChange={handleChange}
                      placeholder="Your name"
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                    />
                    {errors.name && <p className="text-red-600 text-xs mt-1">{errors.name}</p>}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                    <input
                      type="email"
                      name="email"
                      value={form.email}
                      onChange={handleChange}
                      placeholder="you@example.com"
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                    />
                    {errors.email && <p className="text-red-600 text-xs mt-1">{errors.email}</p>}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
                  <input
                    type="text"
                    name="subject"
                    value={form.subject}
                    onChange={handleChange}
                    placeholder="Brief description of your issue"
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                  />
                  {errors.subject && <p className="text-red-600 text-xs mt-1">{errors.subject}</p>}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                    <select
                      name="category"
                      value={form.category}
                      onChange={handleChange}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-white"
                    >
                      {CATEGORIES.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                    {errors.category && <p className="text-red-600 text-xs mt-1">{errors.category}</p>}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                    <select
                      name="priority"
                      value={form.priority}
                      onChange={handleChange}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-white"
                    >
                      {PRIORITIES.map((p) => (
                        <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Message</label>
                  <textarea
                    name="message"
                    value={form.message}
                    onChange={handleChange}
                    rows={5}
                    placeholder="Describe your issue in detail..."
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition resize-y"
                  />
                  {errors.message && <p className="text-red-600 text-xs mt-1">{errors.message}</p>}
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? 'Submitting...' : 'Submit Request'}
                </button>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
