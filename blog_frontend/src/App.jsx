import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom';
import { Sparkles, Bot, PenLine, Menu, X, Users, Briefcase, Wallet, Send, LogOut, User } from 'lucide-react';
import Login from './components/Login';
import Register from './components/Register';
import ArticleList from './components/ArticleList';
import Publish from './components/Publish';
import ArticleDetail from './components/ArticleDetail';
import UserSearch from './components/UserSearch';
import UserHome from './components/UserHome';
import ArticleEdit from './components/ArticleEdit';
import Jobs from './components/Jobs';
import Bills from './components/Bills';
import Boss from './components/Boss';
import AIChat from './components/AIChat';

function Navigation() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const username = localStorage.getItem('username');
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    navigate('/login');
    setIsMenuOpen(false);
  };

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  const handleLinkClick = () => {
    setIsMenuOpen(false);
  };

  return (
    <nav>
      <div className="nav-container">
        <Link to="/" className="nav-brand" onClick={handleLinkClick}>
          <Sparkles size={18} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '6px' }} />
          我的博客
        </Link>

        <div className="nav-right">
          <Link to="/ai" className="btn-ai" onClick={handleLinkClick} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <Bot size={16} /> AI助手
          </Link>

          {token ? (
            <>
              <Link to="/publish" className="btn-publish" onClick={handleLinkClick} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <PenLine size={16} /> 发布
              </Link>
              <div className="dropdown">
                <button className="dropdown-btn" onClick={toggleMenu} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  {isMenuOpen ? <><X size={16} /> 关闭</> : <><Menu size={16} /> 更多</>}
                </button>
                <div className={`dropdown-menu ${isMenuOpen ? 'active' : ''}`}>
                  <Link to="/search" className="dropdown-item" onClick={handleLinkClick} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Users size={15} /> 搜索用户</Link>
                  <Link to="/jobs" className="dropdown-item" onClick={handleLinkClick} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Briefcase size={15} /> 招聘信息</Link>
                  <Link to="/bills" className="dropdown-item" onClick={handleLinkClick} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Wallet size={15} /> 智能记账</Link>
                  <Link to="/boss" className="dropdown-item" onClick={handleLinkClick} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Send size={15} /> 投递简历</Link>
                  <div className="dropdown-divider"></div>
                  <div className="dropdown-user">
                    <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}><User size={14} /> {username}</span>
                    <button className="btn-logout-small" onClick={handleLogout} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <LogOut size={13} /> 退出
                    </button>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <>
              <Link to="/login" className="btn-login" onClick={handleLinkClick}>
                登录
              </Link>
              <Link to="/register" className="btn-register" onClick={handleLinkClick}>
                注册
              </Link>
            </>
          )}
        </div>
      </div>
      
      <style>{`
        .nav-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 0 1.5rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
          min-height: 60px;
          gap: 1rem;
        }

        .nav-brand {
          font-size: 1.4rem;
          font-weight: 700;
          background: var(--primary-gradient);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          text-decoration: none;
          transition: var(--transition);
          padding: 0.5rem 0;
          flex-shrink: 0;
        }

        .nav-brand:hover {
          transform: scale(1.05);
        }

        .nav-right {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .btn-ai {
          padding: 0.6rem 1rem;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: var(--radius-sm);
          color: white !important;
          text-decoration: none;
          font-weight: 500;
          font-size: 0.9rem;
          transition: var(--transition);
          white-space: nowrap;
        }

        .btn-ai:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .btn-publish {
          padding: 0.6rem 1rem;
          background: var(--primary);
          border-radius: var(--radius-sm);
          color: white !important;
          text-decoration: none;
          font-weight: 600;
          font-size: 0.9rem;
          transition: var(--transition);
          white-space: nowrap;
        }

        .btn-publish:hover {
          background: var(--primary-light);
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(254, 44, 85, 0.3);
        }

        .dropdown {
          position: relative;
        }

        .dropdown-btn {
          padding: 0.6rem 1rem;
          background: var(--bg-card);
          border: 1px solid var(--border);
          color: var(--text-primary);
          border-radius: var(--radius-sm);
          cursor: pointer;
          font-weight: 500;
          font-size: 0.9rem;
          transition: var(--transition);
          white-space: nowrap;
        }

        .dropdown-btn:hover {
          background: var(--bg-hover);
          border-color: var(--primary);
          color: var(--primary);
        }

        .dropdown-menu {
          position: absolute;
          top: calc(100% + 0.5rem);
          right: 0;
          background: var(--bg-main);
          border-radius: var(--radius);
          padding: 0.75rem;
          min-width: 180px;
          box-shadow: var(--shadow-hover);
          border: 1px solid var(--border);
          display: none;
          z-index: 1000;
        }

        .dropdown-menu.active {
          display: block;
          animation: fadeIn 0.2s ease;
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .dropdown-item {
          display: block;
          padding: 0.75rem 1rem;
          color: var(--text-primary);
          text-decoration: none;
          border-radius: var(--radius-sm);
          transition: var(--transition);
          font-size: 0.95rem;
        }

        .dropdown-item:hover {
          background: rgba(254, 44, 85, 0.08);
          color: var(--primary);
        }

        .dropdown-divider {
          height: 1px;
          background: var(--border);
          margin: 0.5rem 0;
        }

        .dropdown-user {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.5rem 1rem;
          color: var(--text-secondary);
          font-size: 0.9rem;
        }

        .btn-logout-small {
          padding: 0.3rem 0.75rem;
          background: rgba(254, 44, 85, 0.08);
          border: 1px solid rgba(254, 44, 85, 0.2);
          color: var(--primary);
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          font-size: 0.85rem;
          transition: var(--transition);
        }

        .btn-logout-small:hover {
          background: var(--primary);
          color: white;
          border-color: var(--primary);
        }

        .btn-login {
          padding: 0.6rem 1rem;
          color: var(--primary);
          text-decoration: none;
          font-weight: 600;
          border: 2px solid var(--primary);
          border-radius: var(--radius-sm);
          font-size: 0.9rem;
          transition: var(--transition);
          white-space: nowrap;
        }

        .btn-login:hover {
          background: rgba(254, 44, 85, 0.08);
        }

        .btn-register {
          padding: 0.6rem 1rem;
          background: var(--primary);
          color: white !important;
          text-decoration: none;
          font-weight: 600;
          border-radius: var(--radius-sm);
          font-size: 0.9rem;
          transition: var(--transition);
          white-space: nowrap;
        }

        .btn-register:hover {
          background: var(--primary-light);
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(254, 44, 85, 0.3);
        }

        /* 移动端适配 */
        @media (max-width: 600px) {
          .nav-container {
            padding: 0 1rem;
            gap: 0.5rem;
          }

          .nav-brand {
            font-size: 1.2rem;
          }

          .nav-right {
            gap: 0.4rem;
          }

          .btn-ai, .btn-publish, .btn-login, .btn-register {
            padding: 0.5rem 0.7rem;
            font-size: 0.85rem;
          }

          .dropdown-btn {
            padding: 0.5rem 0.7rem;
            font-size: 0.85rem;
          }

          .dropdown-menu {
            right: -0.5rem;
            min-width: 160px;
          }

          .dropdown-item {
            padding: 0.65rem 0.875rem;
            font-size: 0.9rem;
          }
        }
      `}</style>
    </nav>
  );
}

function App() {
  return (
    <Router>
      <Navigation />
      <div className="container">
        <Routes>
          <Route path="/" element={<ArticleList />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/publish" element={<Publish />} />
          <Route path="/search" element={<UserSearch />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/bills" element={<Bills />} />
          <Route path="/boss" element={<Boss />} />
          <Route path="/ai" element={<AIChat />} />
          <Route path="/user/:id" element={<UserHome />} />
          <Route path="/article/:id" element={<ArticleDetail />} />
          <Route path="/edit/:id" element={<ArticleEdit />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
