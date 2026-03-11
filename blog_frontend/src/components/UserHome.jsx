import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getUserById, getArticles } from '../api';

function UserHome() {
  const { id } = useParams();
  const [user, setUser] = useState(null);
  const [articles, setArticles] = useState([]);
  const [articlePage, setArticlePage] = useState(1);
  const [articleTotalPage, setArticleTotalPage] = useState(1);
  const [articleTotal, setArticleTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchUserArticles = async (username, page) => {
    try {
      const articlesResponse = await getArticles(username, page, 10);
      const data = articlesResponse.data;
      setArticles(data.articles || []);
      setArticleTotal(data.total || 0);
      setArticleTotalPage(data.total_page || 1);
      setArticlePage(page);
    } catch (err) {
      console.error('Error fetching articles:', err);
    }
  };

  useEffect(() => {
    const fetchUserData = async () => {
      setLoading(true);
      setError('');
      try {
        const userResponse = await getUserById(id);
        const userData = userResponse.data;
        setUser(userData);
        
        // Fetch articles using username
        if (userData && userData.username) {
          await fetchUserArticles(userData.username, 1);
        }
      } catch (err) {
        if (err.response && err.response.status === 404) {
          setError('用户不存在');
        } else {
          setError('获取用户信息失败');
        }
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchUserData();
    }
  }, [id]);

  if (loading) return <div>加载中...</div>;
  if (error) return <div className="error">{error}</div>;
  if (!user) return <div>未找到用户</div>;

  return (
    <div>
      <div className="card">
        <div style={{display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '20px'}}>
          {user.avatar ? (
            <img 
              src={user.avatar} 
              alt={user.username} 
              style={{width: '80px', height: '80px', borderRadius: '50%', objectFit: 'cover'}} 
            />
          ) : (
            <div style={{width: '80px', height: '80px', borderRadius: '50%', background: '#ccc', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '24px', color: 'white'}}>
              {user.username && user.username[0] ? user.username[0].toUpperCase() : '?'}
            </div>
          )}
          <div>
            <h3>{user.username}</h3>
            <p>加入时间: {new Date(user.create_time).toLocaleDateString()}</p>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <h4 style={{ margin: 0 }}>发布的文章（共 {articleTotal} 篇）</h4>
          <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={() => fetchUserArticles(user.username, Math.max(1, articlePage - 1))}
                disabled={articlePage <= 1}
                style={{ width: 'auto', marginBottom: 0, padding: '6px 10px' }}
              >
                上一页
              </button>
              <button
                onClick={() => fetchUserArticles(user.username, Math.min(articleTotalPage, articlePage + 1))}
                disabled={articlePage >= articleTotalPage}
                style={{ width: 'auto', marginBottom: 0, padding: '6px 10px' }}
              >
                下一页
              </button>
            </div>
            <small>
              第 {articlePage} / {articleTotalPage} 页
            </small>
          </div>
        </div>

        {articles.length === 0 ? (
          <p>该用户暂无文章。</p>
        ) : (
          <div>
            {articles.map(article => (
              <div key={article.id} style={{borderBottom: '1px solid #eee', padding: '10px 0'}}>
                <h5 style={{margin: '0 0 5px 0'}}>
                  <Link to={`/article/${article.id}`}>{article.title}</Link>
                </h5>
                <small>
                  阅读量: {article.view_count} | 发布于: {new Date(article.created_at || article.create_time).toLocaleDateString()}
                </small>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default UserHome;
