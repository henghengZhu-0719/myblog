import React, { useState } from 'react';
import { Search, Sliders, ToggleLeft, ToggleRight, FileText, Bookmark, Loader, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { searchRag } from '../api';

function RagSearch() {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [useReranker, setUseReranker] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [expandedIndex, setExpandedIndex] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    setResult(null);
    setExpandedIndex(null);

    try {
      const res = await searchRag(query, topK, useReranker);
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.error || err.message || '检索失败');
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (i) => {
    setExpandedIndex(expandedIndex === i ? null : i);
  };

  const preview = (text, len = 200) =>
    text.length > len ? text.slice(0, len) + '...' : text;

  return (
    <div className="rag-search">
      <h1 className="page-title">
        <Search size={24} /> 召回测试
      </h1>
      <p className="page-subtitle">检索 Qdrant 向量库，测试双路召回 + 重排序效果</p>

      <form className="search-form" onSubmit={handleSearch}>
        <div className="search-input-row">
          <input
            className="search-input"
            type="text"
            placeholder="输入检索关键词…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button className="btn-search" type="submit" disabled={loading || !query.trim()}>
            {loading ? <Loader size={18} className="spin" /> : <Search size={18} />}
            {loading ? '检索中…' : '检索'}
          </button>
        </div>

        <div className="search-options">
          <div className="option-group">
            <Sliders size={16} />
            <label>返回条数：{topK}</label>
            <input
              type="range"
              min="1"
              max="20"
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="range-slider"
            />
          </div>

          <div className="option-group">
            <span className="toggle-label">
              {useReranker ? <ToggleRight size={18} color="var(--primary)" /> : <ToggleLeft size={18} />}
              重排序（gte-rerank）
            </span>
            <button
              type="button"
              className={`toggle-btn ${useReranker ? 'active' : ''}`}
              onClick={() => setUseReranker(!useReranker)}
            >
              {useReranker ? '开启' : '关闭'}
            </button>
          </div>
        </div>
      </form>

      {loading && (
        <div className="loading-bar">
          <div className="loading-bar-inner" />
        </div>
      )}

      {error && (
        <div className="result-error">
          <AlertCircle size={20} /> {error}
        </div>
      )}

      {result && !error && (
        <div className="result-section">
          <div className="result-meta">
            <span>查询：<strong>"{result.query}"</strong></span>
            <span className="meta-badge">共 {result.total} 条结果</span>
            <span className={`meta-badge ${result.use_reranker ? 'rerank-on' : 'rerank-off'}`}>
              {result.use_reranker ? '重排序已开启' : '仅 RRF 融合'}
            </span>
          </div>

          {result.results.length === 0 ? (
            <div className="empty-state">
              <AlertCircle size={24} />
              <p>未找到相关结果，请尝试其他关键词</p>
            </div>
          ) : (
            result.results.map((r, i) => (
              <div key={i} className="result-card">
                <div className="result-rank">{i + 1}</div>
                <div className="result-body">
                  <div className="result-top">
                    <div className="result-score">
                      <span className="score-bar" style={{ width: `${Math.min(r.score * 100, 100)}%` }} />
                      <span className="score-text">{(r.score * 100).toFixed(1)}%</span>
                    </div>
                    {r.source_file && (
                      <span className="result-source">
                        <FileText size={14} /> {r.source_file.split('/').pop()}
                      </span>
                    )}
                  </div>
                  {r.headings && r.headings.length > 0 && (
                    <div className="result-headings">
                      <Bookmark size={14} />
                      {r.headings.join('  ›  ')}
                    </div>
                  )}
                  <div className="result-content">
                    {expandedIndex === i ? r.content : preview(r.content)}
                    {r.content.length > 200 && (
                      <button className="expand-btn" onClick={() => toggleExpand(i)}>
                        {expandedIndex === i ? '收起' : '展开全部'} {expandedIndex === i ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      <style>{`
        .rag-search {
          max-width: 800px;
          margin: 0 auto;
        }

        .page-title {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 1.6rem;
          margin-bottom: 0.5rem;
        }

        .page-subtitle {
          color: var(--text-secondary);
          margin-bottom: 2rem;
        }

        .search-form {
          margin-bottom: 2rem;
        }

        .search-input-row {
          display: flex;
          gap: 0.75rem;
        }

        .search-input {
          flex: 1;
          padding: 0.9rem 1.2rem;
          border: 2px solid var(--border);
          border-radius: var(--radius-sm);
          font-size: 1.05rem;
          outline: none;
          transition: var(--transition);
          background: var(--bg-main);
          color: var(--text-primary);
        }

        .search-input:focus {
          border-color: var(--primary);
          box-shadow: 0 0 0 3px rgba(254, 44, 85, 0.1);
        }

        .btn-search {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 0.75rem 1.8rem;
          background: var(--primary-gradient);
          color: white;
          border: none;
          border-radius: var(--radius-sm);
          font-weight: 600;
          font-size: 1rem;
          cursor: pointer;
          transition: var(--transition);
          white-space: nowrap;
        }

        .btn-search:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(254, 44, 85, 0.3);
        }

        .btn-search:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .spin {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .search-options {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 1rem;
          padding: 0.8rem 1rem;
          background: var(--bg-card);
          border-radius: var(--radius-sm);
          flex-wrap: wrap;
          gap: 1rem;
        }

        .option-group {
          display: flex;
          align-items: center;
          gap: 10px;
          color: var(--text-secondary);
          font-size: 0.9rem;
        }

        .option-group label {
          font-weight: 500;
          min-width: 80px;
        }

        .range-slider {
          width: 120px;
          accent-color: var(--primary);
          cursor: pointer;
        }

        .toggle-label {
          display: flex;
          align-items: center;
          gap: 6px;
          font-weight: 500;
        }

        .toggle-btn {
          padding: 4px 14px;
          border-radius: 20px;
          border: 1px solid var(--border);
          background: var(--bg-main);
          color: var(--text-secondary);
          cursor: pointer;
          font-size: 0.85rem;
          font-weight: 600;
          transition: var(--transition);
        }

        .toggle-btn.active {
          background: rgba(254, 44, 85, 0.1);
          border-color: var(--primary);
          color: var(--primary);
        }

        .loading-bar {
          margin: 0.5rem 0 1.5rem;
          height: 4px;
          background: var(--border);
          border-radius: 2px;
          overflow: hidden;
        }

        .loading-bar-inner {
          height: 100%;
          width: 30%;
          background: var(--primary-gradient);
          border-radius: 2px;
          animation: loading 1.5s ease infinite;
        }

        @keyframes loading {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(400%); }
        }

        .result-error {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 1rem;
          background: rgba(254, 44, 85, 0.08);
          border: 1px solid rgba(254, 44, 85, 0.2);
          border-radius: var(--radius-sm);
          color: var(--primary);
        }

        .result-section {
          margin-top: 1.5rem;
        }

        .result-meta {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 1rem;
          padding: 0.8rem 1rem;
          background: var(--bg-card);
          border-radius: var(--radius-sm);
          flex-wrap: wrap;
        }

        .meta-badge {
          padding: 3px 12px;
          border-radius: 20px;
          font-size: 0.85rem;
          font-weight: 600;
        }

        .meta-badge.rerank-on {
          background: rgba(254, 44, 85, 0.1);
          color: var(--primary);
        }

        .meta-badge.rerank-off {
          background: rgba(155, 155, 155, 0.1);
          color: var(--text-secondary);
        }

        .empty-state {
          text-align: center;
          padding: 3rem;
          color: var(--text-secondary);
        }

        .empty-state p {
          margin-top: 0.5rem;
        }

        .result-card {
          display: flex;
          gap: 1rem;
          padding: 1rem;
          margin-bottom: 0.75rem;
          background: var(--bg-main);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          transition: var(--transition);
        }

        .result-card:hover {
          border-color: rgba(254, 44, 85, 0.2);
          box-shadow: var(--shadow);
        }

        .result-rank {
          flex-shrink: 0;
          width: 36px;
          height: 36px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
          background: var(--primary-gradient);
          color: white;
          font-weight: 700;
          font-size: 0.9rem;
        }

        .result-body {
          flex: 1;
          min-width: 0;
        }

        .result-top {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 6px;
        }

        .result-score {
          position: relative;
          height: 20px;
          flex: 1;
          max-width: 200px;
          background: var(--bg-card);
          border-radius: 10px;
          overflow: hidden;
        }

        .score-bar {
          display: block;
          height: 100%;
          background: var(--primary-gradient);
          border-radius: 10px;
          transition: width 0.5s ease;
          opacity: 0.8;
        }

        .score-text {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          font-size: 0.75rem;
          font-weight: 700;
          color: var(--text-primary);
          white-space: nowrap;
        }

        .result-source {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 0.8rem;
          color: var(--text-secondary);
          white-space: nowrap;
        }

        .result-headings {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 0.85rem;
          color: var(--primary);
          font-weight: 500;
          margin-bottom: 6px;
          padding: 4px 8px;
          background: rgba(254, 44, 85, 0.04);
          border-radius: 6px;
        }

        .result-content {
          font-size: 0.95rem;
          line-height: 1.6;
          color: var(--text-primary);
          word-break: break-word;
        }

        .expand-btn {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          margin-left: 6px;
          background: none;
          border: none;
          color: var(--primary);
          font-size: 0.85rem;
          font-weight: 600;
          cursor: pointer;
          padding: 0;
        }

        .expand-btn:hover {
          text-decoration: underline;
        }
      `}</style>
    </div>
  );
}

export default RagSearch;
