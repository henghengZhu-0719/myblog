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
    return <div className="card">请登录以查看您的文章。</div>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
        <h2 style={{ margin: 0 }}>我的文章</h2>
        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <small>共 {total} 篇</small>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              style={{ width: 'auto', marginBottom: 0, padding: '6px 10px' }}
            >
              上一页
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPage, p + 1))}
              disabled={page >= totalPage}
              style={{ width: 'auto', marginBottom: 0, padding: '6px 10px' }}
            >
              下一页
            </button>
          </div>
          <small>
            第 {page} / {totalPage} 页
          </small>
        </div>
      </div>

      {articles.length === 0 ? (
        <div className="card">暂无文章。</div>
      ) : (
        articles.map((article) => (
          <div key={article.id} className="card">
            <h3><Link to={`/article/${article.id}`}>{article.title}</Link></h3>
            <div style={{ maxHeight: '100px', overflow: 'hidden' }}>
              <Markdown remarkPlugins={[remarkGfm]}>{(article.content || '').substring(0, 200)}</Markdown>
            </div>
            <small>阅读量: {article.view_count}</small>
          </div>
        ))
      )}
    </div>
  );
}

export default ArticleList;
