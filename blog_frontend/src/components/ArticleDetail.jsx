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
  const [headings, setHeadings] = useState([]);
  const [showToc, setShowToc] = useState(false);
  const currentUser = localStorage.getItem('username');

  useEffect(() => {
    getArticleDetail(id)
      .then(response => setArticleData(response.data))
      .catch(error => console.error('Error fetching article detail:', error));
  }, [id]);

  useEffect(() => {
    if (articleData?.article?.content) {
      const headingRegex = /^(#{1,6})\s+(.+)$/gm;
      const headingList = [];
      let match;
      while ((match = headingRegex.exec(articleData.article.content)) !== null) {
        headingList.push({
          level: match[1].length,
          text: match[2],
          id: match[2].toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-')
        });
      }
      setHeadings(headingList);
    }
  }, [articleData]);

  const scrollToHeading = (id) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
      setShowToc(false);
    }
  };

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
      <button 
        className="mobile-toc-toggle"
        onClick={() => setShowToc(!showToc)}
      >
        {showToc ? '收起目录' : '展开目录'}
      </button>
      
      <div className={`article-layout ${showToc ? 'toc-visible' : ''}`}>
        <aside className="toc-sidebar">
          <div className="toc-content">
            <h4>目录</h4>
            {headings.length > 0 ? (
              <nav className="toc-nav">
                {headings.map((heading, index) => (
                  <a
                    key={index}
                    href={`#${heading.id}`}
                    className={`toc-item level-${heading.level}`}
                    onClick={(e) => {
                      e.preventDefault();
                      scrollToHeading(heading.id);
                    }}
                  >
                    {heading.text}
                  </a>
                ))}
              </nav>
            ) : (
              <p className="toc-empty">暂无目录</p>
            )}
          </div>
        </aside>
        
        <div className="article-main">
          <div className="card">
            <div className="article-header">
              <h1 id={article.title.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-')}>{article.title}</h1>
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
                components={{
                  h1: ({node, ...props}) => {
                    const text = node.children?.[0]?.value || '';
                    const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
                    return <h1 id={id} {...props} />;
                  },
                  h2: ({node, ...props}) => {
                    const text = node.children?.[0]?.value || '';
                    const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
                    return <h2 id={id} {...props} />;
                  },
                  h3: ({node, ...props}) => {
                    const text = node.children?.[0]?.value || '';
                    const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
                    return <h3 id={id} {...props} />;
                  },
                  h4: ({node, ...props}) => {
                    const text = node.children?.[0]?.value || '';
                    const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
                    return <h4 id={id} {...props} />;
                  },
                  h5: ({node, ...props}) => {
                    const text = node.children?.[0]?.value || '';
                    const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
                    return <h5 id={id} {...props} />;
                  },
                  h6: ({node, ...props}) => {
                    const text = node.children?.[0]?.value || '';
                    const id = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-');
                    return <h6 id={id} {...props} />;
                  }
                }}
              >
                {article.content}
              </Markdown>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ArticleDetail;
