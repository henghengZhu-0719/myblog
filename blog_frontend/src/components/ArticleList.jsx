import React, { useEffect, useState, useRef, useCallback } from 'react';
import { getArticles } from '../api';
import { Link } from 'react-router-dom';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { PenLine, Eye, FileText, Loader2 } from 'lucide-react';

function ArticleList() {
  const [articles, setArticles] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPage, setTotalPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const username = localStorage.getItem('username');
  const observerRef = useRef(null);
  const sentinelRef = useRef(null);

  const loadArticles = useCallback((pageNum) => {
    if (!username || loading) return;
    setLoading(true);
    getArticles(username, pageNum, 10)
      .then(response => {
        const data = response.data;
        const newArticles = data.articles || [];
        const tp = data.total_page || 1;
        setArticles(prev => pageNum === 1 ? newArticles : [...prev, ...newArticles]);
        setTotal(data.total || 0);
        setTotalPage(tp);
        setHasMore(pageNum < tp);
      })
      .catch(error => console.error('Error fetching articles:', error))
      .finally(() => setLoading(false));
  }, [username]);

  useEffect(() => {
    loadArticles(1);
  }, [username]);

  useEffect(() => {
    if (!hasMore || loading) return;
    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loading) {
          setPage(prev => {
            const next = prev + 1;
            loadArticles(next);
            return next;
          });
        }
      },
      { threshold: 0.1 }
    );
    if (sentinelRef.current) observerRef.current.observe(sentinelRef.current);
    return () => observerRef.current?.disconnect();
  }, [hasMore, loading, loadArticles]);

  if (!username) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
        <PenLine size={48} style={{ color: 'var(--primary)', marginBottom: '1rem' }} />
        <h2 style={{
          background: 'var(--primary-gradient)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          marginBottom: '1rem'
        }}>
          开始您的创作之旅
        </h2>
        <p style={{ color: '#666', marginBottom: '2rem' }}>登录后即可查看和发布您的文章</p>
        <Link to="/login" className="btn">立即登录</Link>
      </div>
    );
  }

  return (
    <div>
      {articles.length === 0 && !loading ? (
        <div className="card" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
          <FileText size={56} style={{ color: 'var(--text-secondary)', marginBottom: '1rem', opacity: 0.5 }} />
          <h3 style={{ color: '#2c3e50', marginBottom: '1rem' }}>还没有文章</h3>
          <p style={{ color: '#666', marginBottom: '2rem' }}>开始创作您的第一篇文章吧！</p>
          <Link to="/publish" className="btn" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <PenLine size={16} /> 写文章
          </Link>
        </div>
      ) : (
        <div className="article-grid">
          {articles.map((article, index) => (
            <Link
              key={article.id}
              to={`/article/${article.id}`}
              className="article-card"
              style={{ animation: `fadeInUp 0.5s ease ${(index % 10) * 0.05}s both`, textDecoration: 'none', display: 'block' }}
            >
              {article.cover && (
                <div style={{ overflow: 'hidden', borderRadius: '12px 12px 0 0' }}>
                  <img
                    src={article.cover}
                    alt={article.title}
                    style={{ width: '100%', height: '180px', objectFit: 'cover', transition: 'transform 0.3s ease', borderRadius: 0 }}
                    onMouseOver={(e) => e.target.style.transform = 'scale(1.05)'}
                    onMouseOut={(e) => e.target.style.transform = 'scale(1)'}
                  />
                </div>
              )}
              <div style={{ padding: '1.5rem' }}>
                <h3 style={{ marginBottom: '0.75rem', color: 'var(--text-primary)', fontWeight: 600, fontSize: '1.1rem', lineHeight: 1.4 }}>
                  {article.title}
                </h3>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.6, marginBottom: '1rem', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  <Markdown remarkPlugins={[remarkGfm]}>
                    {(article.content || '').substring(0, 300)}
                  </Markdown>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '0.875rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border)' }}>
                  <Eye size={15} />
                  <span>{article.view_count || 0} 次阅读</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* 哨兵元素 + 加载状态 */}
      <div ref={sentinelRef} style={{ height: '1px' }} />
      {loading && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
          <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
        </div>
      )}
      {!hasMore && articles.length > 0 && (
        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          — 已经到底了 —
        </div>
      )}

      <style>{`
        .article-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
          gap: 1.5rem;
        }
        .article-card {
          background: var(--bg-main);
          border: 1px solid var(--border);
          border-radius: 12px;
          overflow: hidden;
          transition: var(--transition);
          box-shadow: var(--shadow);
          cursor: pointer;
        }
        .article-card:hover {
          transform: translateY(-4px);
          box-shadow: var(--shadow-hover);
          border-color: var(--primary);
        }
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(30px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export default ArticleList;
