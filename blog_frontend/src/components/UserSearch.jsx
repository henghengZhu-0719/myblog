import React, { useState } from 'react';
import { searchUsers } from '../api';
import { Link } from 'react-router-dom';

function UserSearch() {
  const [searchname, setSearchname] = useState('');
  const [users, setUsers] = useState([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);

  const handleSearch = async (e, newPage = 1) => {
    if (e) e.preventDefault();
    if (!searchname.trim()) return;

    setLoading(true);
    setError('');
    
    try {
      const response = await searchUsers(searchname, newPage);
      const data = response.data;
      setUsers(data.users || []);
      setPage(data.page);
      setHasMore(data.has_more);
      setSearched(true);
    } catch (err) {
      console.error('Search error:', err);
      setError('查询失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (newPage) => {
    handleSearch(null, newPage);
  };

  return (
    <div>
      <div className="card">
        <h2>搜索用户</h2>
        <form onSubmit={(e) => handleSearch(e, 1)} style={{display: 'flex', gap: '10px'}}>
          <input
            type="text"
            placeholder="输入用户名关键字..."
            value={searchname}
            onChange={(e) => setSearchname(e.target.value)}
            style={{flex: 1, marginBottom: 0}}
          />
          <button type="submit" disabled={loading} style={{width: 'auto'}}>
            {loading ? '搜索中...' : '搜索'}
          </button>
        </form>
        {error && <div className="error" style={{marginTop: '10px'}}>{error}</div>}
      </div>

      {searched && (
        <div className="card">
          <h3>搜索结果</h3>
          {users.length === 0 ? (
            <p>未找到匹配的用户。</p>
          ) : (
            <div>
              {users.map(user => (
                <div key={user.id} style={{
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center', 
                  padding: '15px 0', 
                  borderBottom: '1px solid #eee'
                }}>
                  <div style={{display: 'flex', alignItems: 'center', gap: '15px'}}>
                    <div style={{
                      width: '50px', 
                      height: '50px', 
                      borderRadius: '50%', 
                      background: '#ccc', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      color: 'white',
                      fontWeight: 'bold'
                    }}>
                      {user.username[0].toUpperCase()}
                    </div>
                    <div>
                      <h4 style={{margin: '0 0 5px 0'}}>
                        <Link to={`/user/${user.id}`} style={{textDecoration: 'none', color: '#333'}}>
                          {user.username}
                        </Link>
                      </h4>
                      <small style={{color: '#666'}}>
                        加入时间: {new Date(user.create_time).toLocaleDateString()}
                      </small>
                    </div>
                  </div>
                  <Link to={`/user/${user.id}`} className="button" style={{
                    padding: '5px 15px', 
                    fontSize: '14px', 
                    textDecoration: 'none',
                    backgroundColor: '#007bff',
                    color: 'white',
                    borderRadius: '4px'
                  }}>
                    查看主页
                  </Link>
                </div>
              ))}
            </div>
          )}

          {users.length > 0 && (
            <div style={{display: 'flex', justifyContent: 'center', gap: '10px', marginTop: '20px'}}>
              <button 
                onClick={() => handlePageChange(page - 1)} 
                disabled={page <= 1 || loading}
                style={{width: 'auto'}}
              >
                上一页
              </button>
              <span style={{lineHeight: '38px'}}>第 {page} 页</span>
              <button 
                onClick={() => handlePageChange(page + 1)} 
                disabled={!hasMore || loading}
                style={{width: 'auto'}}
              >
                下一页
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default UserSearch;
