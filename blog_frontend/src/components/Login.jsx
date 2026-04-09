import React, { useState } from 'react';
import { login } from '../api';
import { useNavigate, Link } from 'react-router-dom';

function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const data = await login(username, password);
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('username', username);
      navigate('/');
    } catch (err) {
      setError('用户名或密码错误');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '80vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem 1rem'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '440px',
        background: 'var(--bg-main)',
        border: '1px solid var(--border)',
        borderRadius: '16px',
        padding: '2.5rem 2rem',
        boxShadow: 'var(--shadow)',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '4px',
          background: 'var(--primary-gradient)'
        }}></div>

        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h2 style={{
            fontSize: '1.875rem',
            fontWeight: 700,
            background: 'var(--primary-gradient)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: '0.5rem'
          }}>
            欢迎回来
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
            登录到你的博客账号
          </p>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{
              display: 'block',
              marginBottom: '0.5rem',
              color: 'var(--text-primary)',
              fontWeight: 600,
              fontSize: '0.9rem'
            }}>
              用户名
            </label>
            <input
              type="text"
              placeholder="输入你的用户名"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '0.875rem 1rem',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '1rem',
                transition: 'var(--transition)',
                background: 'var(--bg-main)'
              }}
            />
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{
              display: 'block',
              marginBottom: '0.5rem',
              color: 'var(--text-primary)',
              fontWeight: 600,
              fontSize: '0.9rem'
            }}>
              密码
            </label>
            <input
              type="password"
              placeholder="输入你的密码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '0.875rem 1rem',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '1rem',
                transition: 'var(--transition)',
                background: 'var(--bg-main)'
              }}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '0.875rem',
              background: isLoading ? 'var(--primary-light)' : 'var(--primary)',
              color: 'white',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              fontSize: '1rem',
              fontWeight: 600,
              cursor: isLoading ? 'not-allowed' : 'pointer',
              transition: 'var(--transition)',
              opacity: isLoading ? 0.7 : 1
            }}
          >
            {isLoading ? '登录中...' : '登录'}
          </button>
        </form>

        <div style={{
          textAlign: 'center',
          marginTop: '1.5rem',
          paddingTop: '1.5rem',
          borderTop: '1px solid var(--border)',
          color: 'var(--text-secondary)',
          fontSize: '0.95rem'
        }}>
          还没有账号？{' '}
          <Link to="/register" style={{
            color: 'var(--primary)',
            fontWeight: 600,
            textDecoration: 'none'
          }}>
            立即注册
          </Link>
        </div>
      </div>
    </div>
  );
}

export default Login;
