import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getArticleDetail, editArticle } from '../api';

function ArticleEdit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [cover, setCover] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getArticleDetail(id)
      .then(response => {
        const { article } = response.data;
        setTitle(article.title);
        setContent(article.content);
        setCover(article.cover || '');
        setLoading(false);
      })
      .catch(error => {
        console.error('Error fetching article detail:', error);
        alert('获取文章详情失败');
        navigate('/');
      });
  }, [id, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await editArticle(id, { title, content, cover });
      alert('修改成功');
      navigate(`/article/${id}`);
    } catch (error) {
      console.error('Failed to update article:', error);
      alert('修改文章失败');
    }
  };

  if (loading) return <div>加载中...</div>;

  return (
    <div className="card">
      <h2>编辑文章</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="标题"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <textarea
          placeholder="内容"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows="10"
          required
        />
        <input
          type="text"
          placeholder="封面图片链接 (可选)"
          value={cover}
          onChange={(e) => setCover(e.target.value)}
        />
        <button type="submit">保存修改</button>
      </form>
    </div>
  );
}

export default ArticleEdit;
