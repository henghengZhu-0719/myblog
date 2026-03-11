import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom';
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

function Navigation() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const username = localStorage.getItem('username');

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    navigate('/login');
  };

  return (
    <nav>
      <div className="container" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
        <div>
          <Link to="/"><strong>博客</strong></Link>
          <Link to="/search" style={{marginLeft: '20px', color: 'white', textDecoration: 'none'}}>搜索用户</Link>
          <Link to="/jobs" style={{marginLeft: '20px', color: 'white', textDecoration: 'none'}}>招聘信息</Link>
          <Link to="/bills" style={{marginLeft: '20px', color: 'white', textDecoration: 'none'}}>智能记账</Link>
          <Link to="/boss" style={{marginLeft: '20px', color: 'white', textDecoration: 'none'}}>投递简历</Link>
        </div>
        <div>
          {token ? (
            <>
              <span style={{marginRight: '15px'}}>欢迎, {username}</span>
              <Link to="/publish">发布文章</Link>
              <button onClick={handleLogout} style={{background: 'none', border: '1px solid white', padding: '5px 10px'}}>退出登录</button>
            </>
          ) : (
            <>
              <Link to="/login">登录</Link>
              <Link to="/register">注册</Link>
            </>
          )}
        </div>
      </div>
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
          <Route path="/user/:id" element={<UserHome />} />
          <Route path="/article/:id" element={<ArticleDetail />} />
          <Route path="/edit/:id" element={<ArticleEdit />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
