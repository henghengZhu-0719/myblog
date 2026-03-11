import React, { useState } from 'react';
import { register } from '../api';
import { useNavigate } from 'react-router-dom';

function Register() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [avatar, setAvatar] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await register(username, password, avatar);
      navigate('/login');
    } catch (err) {
      setError('注册失败，用户名可能已存在。');
    }
  };

  return (
    <div className="card">
      <h2>注册</h2>
      {error && <div className="error">{error}</div>}
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="用户名"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          type="password"
          placeholder="密码"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <input
          type="text"
          placeholder="头像链接 (可选)"
          value={avatar}
          onChange={(e) => setAvatar(e.target.value)}
        />
        <button type="submit">注册</button>
      </form>
    </div>
  );
}

export default Register;
