import React, { useState } from 'react';
import { publishArticle } from '../api';
import { useNavigate } from 'react-router-dom';

function Publish() {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [cover, setCover] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await publishArticle({ title, content, cover });
      navigate('/');
    } catch (error) {
      console.error('Failed to publish article:', error);
      alert('发布文章失败');
    }
  };

  return (
    <div className="card">
      <h2>发布新文章</h2>
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
        <button type="submit">发布</button>
      </form>
    </div>
  );
}

export default Publish;
