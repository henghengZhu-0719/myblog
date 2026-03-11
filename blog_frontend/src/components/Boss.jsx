import React, { useState } from 'react';
import { crawlBoss, createBoss } from '../api';
import { useNavigate } from 'react-router-dom';

function Boss() {
  const [urls, setUrls] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleCrawl = async () => {
    if (!urls.trim()) return;
    setLoading(true);
    setError('');
    try {
      const urlList = urls.split('\n').filter(u => u.trim());
      const res = await crawlBoss(urlList);
      if (res.data.success) {
        setResults(res.data.data);
      } else {
        setError(res.data.message || '抓取失败');
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || '抓取失败，请检查链接或稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError('');
    try {
      // Map crawl_time to crawl_date for backend compatibility
      const dataToSave = results.map(item => ({
        ...item,
        crawl_date: item.crawl_time
      }));
      
      // createBoss expects a list or single object. Our API handles both.
      const res = await createBoss(dataToSave);
      if (res.data.success) {
        alert(`成功保存 ${res.data.count || 1} 条记录！`);
        setResults([]);
        setUrls('');
      } else {
        setError(res.data.message || '保存失败');
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || '保存失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = (index) => {
    const newResults = [...results];
    newResults.splice(index, 1);
    setResults(newResults);
  };

  return (
    <div style={{ padding: '20px' }}>
      <h2>投递简历</h2>
      <div style={{ background: '#fff', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>职位链接 (每行一个)</label>
          <textarea
            style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ddd', minHeight: '150px' }}
            value={urls}
            onChange={(e) => setUrls(e.target.value)}
            placeholder="请输入职位链接..."
          />
        </div>
        <button 
          onClick={handleCrawl} 
          disabled={loading || !urls.trim()}
          style={{
            padding: '10px 20px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading || !urls.trim() ? 'not-allowed' : 'pointer',
            opacity: loading || !urls.trim() ? 0.7 : 1
          }}
        >
          {loading ? '处理中...' : '抓取信息'}
        </button>
        {error && <div style={{ color: 'red', marginTop: '10px' }}>{error}</div>}
      </div>

      {results.length > 0 && (
        <div style={{ marginTop: '30px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
            <h3>抓取结果 ({results.length})</h3>
            <button 
              onClick={handleSubmit} 
              disabled={loading}
              style={{
                padding: '10px 20px',
                backgroundColor: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: loading ? 'not-allowed' : 'pointer'
              }}
            >
              保存所有记录
            </button>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {results.map((item, index) => (
              <div key={index} style={{ background: '#fff', padding: '15px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <h4 style={{ margin: 0 }}>{item.title}</h4>
                  <button 
                    onClick={() => handleRemove(index)}
                    style={{ background: 'none', border: 'none', color: '#dc3545', cursor: 'pointer' }}
                  >
                    删除
                  </button>
                </div>
                <div style={{ fontSize: '14px', color: '#666', marginBottom: '10px' }}>
                  <span style={{ marginRight: '15px' }}>地区: {item.dq}</span>
                  <span style={{ marginRight: '15px' }}>时间: {item.crawl_time}</span>
                  <a href={item.url} target="_blank" rel="noreferrer" style={{ color: '#007bff' }}>原始链接</a>
                </div>
                <div style={{ background: '#f8f9fa', padding: '10px', borderRadius: '4px', fontSize: '14px', maxHeight: '100px', overflowY: 'auto' }}>
                  {item.details}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default Boss;
