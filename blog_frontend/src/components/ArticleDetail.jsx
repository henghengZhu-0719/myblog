import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getArticleDetail, deleteArticle } from '../api';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import '../markdown.css';
import './ArticleDetail.css';

function ArticleDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [articleData, setArticleData] = useState(null);
  const currentUser = localStorage.getItem('username');

  useEffect(() => {
    getArticleDetail(id)
      .then(response => setArticleData(response.data))
      .catch(error => console.error('Error fetching article detail:', error));
  }, [id]);

  const handleDelete = async () => {
    if (window.confirm('确定要删除这篇文章吗？')) {
      try {
        await deleteArticle(id);
        alert('删除成功');
        navigate('/');
      } catch (error) {
        console.error('Failed to delete article:', error);
        alert('删除失败');
      }
    }
  };

  if (!articleData) return <div>加载中...</div>;

  const { article, author } = articleData;

  return (
    <div className="article-detail-container">
      <div className="card">
        <div className="article-header">
          <h1>{article.title}</h1>
          {currentUser === author && (
            <div className="article-actions">
              <Link to={`/edit/${article.id}`} style={{textDecoration: 'none', color: '#007bff'}}>编辑</Link>
              <button onClick={handleDelete} style={{background: '#dc3545', padding: '5px 10px', fontSize: '14px', width: 'auto'}}>删除</button>
            </div>
          )}
        </div>
        <p><small>作者: {author} | 阅读量: {article.view_count} | 时间: {new Date(article.create_time || article.created_at).toLocaleDateString()}</small></p>
        
        {article.cover && <img src={article.cover} alt="Cover" style={{maxWidth: '100%', marginBottom: '20px', borderRadius: '4px'}} />}
        
        <div className="markdown-content">
          <Markdown 
            remarkPlugins={[remarkGfm]}
          >
            {article.content}
          </Markdown>
        </div>
      </div>
    </div>
  );
}

export default ArticleDetail;
