import React, { useEffect, useState } from 'react';
import { getArticles } from '../api';
import { Link } from 'react-router-dom';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function ArticleList() {
  const [articles, setArticles] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPage, setTotalPage] = useState(1);
  const [total, setTotal] = useState(0);
  const username = localStorage.getItem('username');

  useEffect(() => {
    if (username) {
      getArticles(username, page, 10)
        .then(response => {
          const data = response.data;
          setArticles(data.articles || []);
          setTotal(data.total || 0);
          setTotalPage(data.total_page || 1);
        })
        .catch(error => console.error('Error fetching articles:', error));
    }
  }, [username, page]);

  if (!username) {
    return (
      <div className="card" style={{
        textAlign: 'center',
        padding: '4rem 2rem'
      }}>
        <div style={{
          fontSize: '3rem',
          marginBottom: '1rem'
        }}>
          ✍️
        </div>
        <h2 style={{
          background: 'var(--primary-gradient)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          marginBottom: '1rem'
        }}>
          开始您的创作之旅
        </h2>
        <p style={{ color: '#666', marginBottom: '2rem' }}>
          登录后即可查看和发布您的文章
        </p>
        <Link to="/login" className="btn">
          立即登录
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1rem',
        marginBottom: '2rem'
      }}>
        <div>
          <h2 style={{
            fontSize: '2rem',
            fontWeight: 700,
            background: 'var(--primary-gradient)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            margin: 0,
            marginBottom: '0.5rem'
          }}>
            我的文章
          </h2>
          <p style={{ color: '#666', fontSize: '0.95rem', margin: 0 }}>
            共 <strong style={{ color: '#667eea' }}>{total}</strong> 篇精彩内容
          </p>
        </div>
        
        <div style={{
          display: 'flex',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          background: 'white',
          padding: '12px 20px',
          borderRadius: '12px',
          boxShadow: 'var(--card-shadow)'
        }}>
          <span style={{ color: '#666', fontSize: '0.9rem' }}>
            第 <strong>{page}</strong> / {totalPage} 页
          </span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              style={{
                width: 'auto',
                marginBottom: 0,
                padding: '10px 16px',
                fontSize: '0.9rem'
              }}
            >
              ← 上一页
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPage, p + 1))}
              disabled={page >= totalPage}
              style={{
                width: 'auto',
                marginBottom: 0,
                padding: '10px 16px',
                fontSize: '0.9rem'
              }}
            >
              下一页 →
            </button>
          </div>
        </div>
      </div>

      {articles.length === 0 ? (
        <div className="card" style={{
          textAlign: 'center',
          padding: '4rem 2rem'
        }}>
          <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>📝</div>
          <h3 style={{
            color: '#2c3e50',
            marginBottom: '1rem'
          }}>
            还没有文章
          </h3>
          <p style={{ color: '#666', marginBottom: '2rem' }}>
            开始创作您的第一篇文章吧！
          </p>
          <Link to="/publish" className="btn">
            ✍️ 写文章
          </Link>
        </div>
      ) : (
        <div className="article-grid">
          {articles.map((article, index) => (
            <div key={article.id} className="article-card" style={{
              animation: `fadeInUp 0.5s ease ${index * 0.1}s both`
            }}>
              {article.cover && (
                <div style={{
                  marginTop: '-28px',
                  marginLeft: '-28px',
                  marginRight: '-28px',
                  marginBottom: '20px',
                  overflow: 'hidden',
                  borderRadius: '16px 16px 0 0'
                }}>
                  <img 
                    src={article.cover} 
                    alt={article.title}
                    style={{
                      width: '100%',
                      height: '180px',
                      objectFit: 'cover',
                      transition: 'transform 0.3s ease'
                    }}
                    onMouseOver={(e) => e.target.style.transform = 'scale(1.05)'}
                    onMouseOut={(e) => e.target.style.transform = 'scale(1)'}
                  />
                </div>
              )}
              
              <h3>
                <Link to={`/article/${article.id}`}>{article.title}</Link>
              </h3>
              
              <div className="article-card-content">
                <Markdown remarkPlugins={[remarkGfm]}>
                  {(article.content || '').substring(0, 300)}
                </Markdown>
              </div>
              
              <div className="article-card-footer">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '1.2rem' }}>👁️</span>
                  <span>{article.view_count || 0} 次阅读</span>
                </div>
                <Link to={`/article/${article.id}`}>
                  阅读全文 →
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {articles.length > 0 && totalPage > 1 && (
        <div className="pagination">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
          >
            ← 上一页
          </button>
          <span style={{ color: '#666', fontSize: '0.95rem' }}>
            第 {page} / {totalPage} 页
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPage, p + 1))}
            disabled={page >= totalPage}
          >
            下一页 →
          </button>
        </div>
      )}

      <style>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}

export default ArticleList;
