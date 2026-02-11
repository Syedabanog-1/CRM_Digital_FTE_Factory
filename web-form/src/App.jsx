import React, { useState, useEffect } from 'react';
import LoginForm from './LoginForm';
import SignupForm from './SignupForm';
import SupportForm from './SupportForm';

export default function App() {
  const [page, setPage] = useState('login');
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const saved = localStorage.getItem('techcorp_token');
    const savedUser = localStorage.getItem('techcorp_user');
    if (saved && savedUser) {
      setToken(saved);
      setUser(JSON.parse(savedUser));
      setPage('support');
    }
  }, []);

  const handleLogin = (accessToken, userName) => {
    setToken(accessToken);
    const userData = { name: userName };
    setUser(userData);
    localStorage.setItem('techcorp_token', accessToken);
    localStorage.setItem('techcorp_user', JSON.stringify(userData));
    setPage('support');
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('techcorp_token');
    localStorage.removeItem('techcorp_user');
    setPage('login');
  };

  const handleSignupSuccess = () => {
    setPage('login');
  };

  if (page === 'signup') {
    return (
      <SignupForm
        onSignupSuccess={handleSignupSuccess}
        onSwitchToLogin={() => setPage('login')}
      />
    );
  }

  if (page === 'support' && token && user) {
    return <SupportForm token={token} user={user} onLogout={handleLogout} />;
  }

  return (
    <LoginForm
      onLogin={handleLogin}
      onSwitchToSignup={() => setPage('signup')}
    />
  );
}
