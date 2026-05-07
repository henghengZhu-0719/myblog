import React, { useState, useRef, useCallback, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { Upload, File, X, CheckCircle, AlertCircle, Loader, FileText, Search, Database, XCircle, ChevronRight } from 'lucide-react';
import { uploadRagFiles } from '../api';

const ACCEPTED_TYPES = '.md,.pdf,.txt';

function RagUpload() {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState(null);
  const [storeInQdrant, setStoreInQdrant] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [selectedChunk, setSelectedChunk] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (selectedChunk) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [selectedChunk]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setSelectedChunk(null);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const addFiles = useCallback((newFiles) => {
    const valid = Array.from(newFiles).filter(
      (f) => ACCEPTED_TYPES.includes(f.name.match(/\.\w+$/)?.[0]?.toLowerCase() ?? '')
    );
    setFiles((prev) => {
      const names = new Set(prev.map((f) => f.name));
      return [...prev, ...valid.filter((f) => !names.has(f.name))];
    });
  }, []);

  const removeFile = (name) => {
    setFiles((prev) => prev.filter((f) => f.name !== name));
  };

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragOver(false);
      addFiles(e.dataTransfer.files);
    },
    [addFiles]
  );

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };
  const handleDragLeave = () => setDragOver(false);

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setResults(null);

    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    formData.append('store_in_qdrant', storeInQdrant);
    formData.append('chunk_size', '500');
    formData.append('overlap', '100');

    try {
      const res = await uploadRagFiles(formData);
      setResults(res.data.results);
      setFiles([]);
    } catch (err) {
      console.error('Upload failed:', err);
      setResults({ error: err.message || '上传失败' });
    } finally {
      setUploading(false);
    }
  };

  const totalChunks = results && !results.error
    ? results.reduce((s, r) => s + r.chunk_count, 0)
    : 0;

  return (
    <div className="rag-upload">
      <h1 className="page-title">
        <FileText size={24} /> 文档解析
      </h1>
      <p className="page-subtitle">上传 Markdown / PDF / 文本文件，自动解析并存入向量知识库</p>

      <div
        className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
      >
        <Upload size={40} className="drop-icon" />
        <p className="drop-text">拖拽文件到此处，或点击选择文件</p>
        <p className="drop-hint">支持 .md .pdf .txt 格式</p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_TYPES}
          onChange={(e) => addFiles(e.target.files)}
          style={{ display: 'none' }}
        />
      </div>

      {files.length > 0 && (
        <div className="file-list">
          <h3>已选择 {files.length} 个文件</h3>
          {files.map((f) => (
            <div key={f.name} className="file-item">
              <File size={18} />
              <span className="file-name">{f.name}</span>
              <span className="file-size">{(f.size / 1024).toFixed(1)} KB</span>
              <button className="btn-icon" onClick={() => removeFile(f.name)} title="移除">
                <X size={16} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="upload-actions">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={storeInQdrant}
            onChange={(e) => setStoreInQdrant(e.target.checked)}
          />
          <span>解析后存入 Qdrant 向量库（可检索）</span>
        </label>

        <button
          className="btn-upload"
          onClick={handleUpload}
          disabled={files.length === 0 || uploading}
        >
          {uploading ? (
            <><Loader size={18} className="spin" /> 解析中...</>
          ) : (
            <><Search size={18} /> 开始解析</>
          )}
        </button>
      </div>

      {uploading && (
        <div className="loading-bar">
          <div className="loading-bar-inner" />
        </div>
      )}

      {results && (
        <div className="results">
          {results.error ? (
            <div className="result-error">
              <AlertCircle size={20} /> {results.error}
            </div>
          ) : (
            <>
              <h2 className="result-summary">
                <CheckCircle size={22} color="var(--primary)" />
                解析完成 — 共 {results.length} 个文件，{totalChunks} 个片段
              </h2>
              {results.map((r) => (
                <div key={r.filename} className="result-card">
                  <div className="result-header">
                    <FileText size={18} />
                    <span className="result-filename">{r.filename}</span>
                    <span className="result-count">{r.chunk_count} 个片段</span>
                    {r.qdrant_stored !== undefined && (
                      <span className={`qdrant-badge ${r.qdrant_stored ? 'stored' : 'failed'}`}>
                        {r.qdrant_stored ? (
                          <><Database size={14} /> 已入库</>
                        ) : (
                          <><XCircle size={14} /> 入库失败</>
                        )}
                      </span>
                    )}
                  </div>
                  {r.qdrant_error && (
                    <div className="qdrant-error">
                      <AlertCircle size={14} /> {r.qdrant_error}
                    </div>
                  )}
                  {r.distribution && (
                    <div className="dist-overview">
                      <div className="dist-row">
                        <div className="dist-stat">
                          <span className="dist-value">{r.distribution.total_chunks}</span>
                          <span className="dist-label">chunks</span>
                        </div>
                        <div className="dist-stat">
                          <span className="dist-value">{r.distribution.total_tokens.toLocaleString()}</span>
                          <span className="dist-label">总 tokens</span>
                        </div>
                        <div className="dist-stat">
                          <span className="dist-value">{r.distribution.total_chars.toLocaleString()}</span>
                          <span className="dist-label">总字符</span>
                        </div>
                        <div className="dist-stat">
                          <span className="dist-value">{r.distribution.token_mean}</span>
                          <span className="dist-label">平均 token/chunk</span>
                        </div>
                      </div>
                      <div className="dist-row">
                        <div className="dist-stat">
                          <span className="dist-value">{r.distribution.token_median}</span>
                          <span className="dist-label">中位数</span>
                        </div>
                        <div className="dist-stat">
                          <span className="dist-value">{r.distribution.token_min}–{r.distribution.token_max}</span>
                          <span className="dist-label">范围</span>
                        </div>
                        <div className="dist-stat">
                          <span className="dist-value">{r.distribution.token_p25} / {r.distribution.token_p75}</span>
                          <span className="dist-label">P25 / P75</span>
                        </div>
                        <div className="dist-stat">
                          <span className="dist-value">{r.distribution.token_p95}</span>
                          <span className="dist-label">P95 上限</span>
                        </div>
                      </div>
                      {r.distribution.type_counts && Object.keys(r.distribution.type_counts).length > 0 && (
                        <div className="dist-row">
                          <span className="dist-type-label">内容类型分布：</span>
                          {Object.entries(r.distribution.type_counts).map(([type, count]) => (
                            <span key={type} className="dist-type-tag">{type} <small>x{count}</small></span>
                          ))}
                        </div>
                      )}
                      {(r.distribution.empty_chunks > 0 || r.distribution.too_small_chunks > 0 || r.distribution.too_large_chunks > 0 || r.distribution.orphan_chunks > 0) && (
                        <div className="dist-warnings">
                          {r.distribution.empty_chunks > 0 && <span className="dist-warn">⚠ 空 chunk: {r.distribution.empty_chunks} 个</span>}
                          {r.distribution.too_small_chunks > 0 && <span className="dist-warn">⚠ 过小: {r.distribution.too_small_chunks} 个</span>}
                          {r.distribution.too_large_chunks > 0 && <span className="dist-warn">⚠ 过大: {r.distribution.too_large_chunks} 个</span>}
                          {r.distribution.orphan_chunks > 0 && <span className="dist-warn">⚠ 无标题路径: {r.distribution.orphan_chunks} 个</span>}
                        </div>
                      )}
                    </div>
                  )}
                  <div className="result-chunks">
                    {r.chunks.map((c, i) => (
                      <div key={i} className="chunk-item" onClick={() => {
                        console.log('点击 chunk:', { content_len: c.content?.length, preview: c.content_preview, keys: Object.keys(c) });
                        setSelectedChunk({ ...c, filename: r.filename, index: i });
                      }}>
                        <div className="chunk-item-header">
                          <span className="chunk-index">#{i + 1}</span>
                          {c.headings.length > 0 && (
                            <span className="chunk-headings">
                              {'> '}{c.headings.join(' > ')}
                            </span>
                          )}
                          <ChevronRight size={14} className="chunk-arrow" />
                        </div>
                        <div className="chunk-content">{c.content}</div>
                        <div className="chunk-meta">
                          <span>{c.length} 字符</span>
                          {c.token_count > 0 && <span> · {c.token_count} tokens</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {selectedChunk && ReactDOM.createPortal(
        <div className="modal-overlay" onClick={() => setSelectedChunk(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                <FileText size={18} />
                <span>{selectedChunk.filename}</span>
                <span className="modal-chunk-label">片段 #{selectedChunk.index + 1}</span>
              </div>
              <button className="btn-icon" onClick={() => setSelectedChunk(null)}>
                <X size={20} />
              </button>
            </div>

            {selectedChunk.headings?.length > 0 && (
              <div className="modal-headings">
                {selectedChunk.headings.map((h, i) => (
                  <span key={i} className="modal-heading-tag">{h}</span>
                ))}
              </div>
            )}

            <div className="modal-stats">
              <span className="modal-stat-content-length">
                <strong>{selectedChunk.length ?? 0}</strong> 字符
                {selectedChunk.token_count > 0 && (
                  <span className="modal-stat-full"> · 完整内容</span>
                )}
              </span>
              {selectedChunk.token_count > 0 && (
                <span><strong>{selectedChunk.token_count}</strong> tokens</span>
              )}
              {selectedChunk.line_start > 0 && (
                <span>行 {selectedChunk.line_start} – {selectedChunk.line_end}</span>
              )}
            </div>

            <div className="modal-body">
              <pre className="modal-content-text">{selectedChunk.content}</pre>
            </div>
          </div>
        </div>,
        document.body
      )}

      <style>{`
        .rag-upload {
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

        .drop-zone {
          border: 2px dashed var(--border);
          border-radius: var(--radius);
          padding: 3rem 2rem;
          text-align: center;
          cursor: pointer;
          transition: var(--transition);
          background: var(--bg-card);
        }

        .drop-zone:hover,
        .drop-zone.drag-over {
          border-color: var(--primary);
          background: rgba(254, 44, 85, 0.03);
        }

        .drop-icon {
          color: var(--text-secondary);
          margin-bottom: 1rem;
        }

        .drag-over .drop-icon {
          color: var(--primary);
        }

        .drop-text {
          font-size: 1.1rem;
          font-weight: 500;
          margin-bottom: 0.3rem;
        }

        .drop-hint {
          color: var(--text-secondary);
          font-size: 0.9rem;
        }

        .file-list {
          margin-top: 1.5rem;
        }

        .file-list h3 {
          margin-bottom: 0.75rem;
          font-size: 1rem;
        }

        .file-item {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 0.6rem 0.8rem;
          background: var(--bg-card);
          border-radius: var(--radius-sm);
          margin-bottom: 0.5rem;
          color: var(--text-primary);
        }

        .file-name {
          flex: 1;
          font-weight: 500;
        }

        .file-size {
          color: var(--text-secondary);
          font-size: 0.85rem;
        }

        .btn-icon {
          background: none;
          border: none;
          color: var(--text-secondary);
          cursor: pointer;
          padding: 4px;
          border-radius: 4px;
        }

        .btn-icon:hover {
          background: rgba(254, 44, 85, 0.1);
          color: var(--primary);
        }

        .upload-actions {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 1.5rem;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
          font-size: 0.95rem;
          color: var(--text-secondary);
        }

        .checkbox-label input {
          width: 18px;
          height: 18px;
          accent-color: var(--primary);
          cursor: pointer;
        }

        .btn-upload {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 0.75rem 2rem;
          background: var(--primary);
          color: white;
          border: none;
          border-radius: var(--radius-sm);
          font-weight: 600;
          font-size: 1rem;
          cursor: pointer;
          transition: var(--transition);
        }

        .btn-upload:hover:not(:disabled) {
          background: var(--primary-light);
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(254, 44, 85, 0.3);
        }

        .btn-upload:disabled {
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

        .loading-bar {
          margin-top: 1.5rem;
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

        .results {
          margin-top: 2rem;
        }

        .result-summary {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 1.1rem;
          margin-bottom: 1.5rem;
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

        .result-card {
          border: 1px solid var(--border);
          border-radius: var(--radius);
          margin-bottom: 1rem;
          overflow: hidden;
        }

        .result-header {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 0.8rem 1rem;
          background: var(--bg-card);
          border-bottom: 1px solid var(--border);
        }

        .result-filename {
          flex: 1;
          font-weight: 600;
        }

        .result-count {
          color: var(--text-secondary);
          font-size: 0.9rem;
        }

        .qdrant-badge {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 3px 10px;
          border-radius: 20px;
          font-size: 0.8rem;
          font-weight: 600;
          margin-left: 8px;
        }

        .qdrant-badge.stored {
          background: rgba(52, 199, 89, 0.12);
          color: #34c759;
        }

        .qdrant-badge.failed {
          background: rgba(254, 44, 85, 0.1);
          color: var(--primary);
        }

        .qdrant-error {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 16px;
          font-size: 0.85rem;
          color: var(--primary);
          background: rgba(254, 44, 85, 0.04);
          border-bottom: 1px solid var(--border);
        }

        /* Distribution Overview */
        .dist-overview {
          padding: 0.75rem 1rem;
          border-bottom: 1px solid var(--border);
          background: var(--bg-card);
        }

        .dist-row {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem 1.5rem;
          margin-bottom: 0.4rem;
        }

        .dist-row:last-child {
          margin-bottom: 0;
        }

        .dist-stat {
          display: flex;
          flex-direction: column;
          gap: 1px;
          min-width: 80px;
        }

        .dist-value {
          font-size: 1.05rem;
          font-weight: 700;
          color: var(--text-primary);
          font-variant-numeric: tabular-nums;
        }

        .dist-label {
          font-size: 0.75rem;
          color: var(--text-secondary);
          text-transform: uppercase;
          letter-spacing: 0.3px;
        }

        .dist-type-label {
          font-size: 0.8rem;
          color: var(--text-secondary);
          margin-right: 4px;
        }

        .dist-type-tag {
          font-size: 0.78rem;
          background: rgba(254, 44, 85, 0.06);
          color: var(--primary);
          padding: 2px 8px;
          border-radius: 8px;
          font-weight: 500;
        }

        .dist-type-tag small {
          font-weight: 400;
          opacity: 0.7;
        }

        .dist-warnings {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 6px;
          padding-top: 6px;
          border-top: 1px dashed var(--border);
        }

        .dist-warn {
          font-size: 0.78rem;
          color: #e67e22;
          background: rgba(230, 126, 34, 0.08);
          padding: 2px 8px;
          border-radius: 6px;
        }

        .result-chunks {
          padding: 0.5rem;
        }

        .chunk-item {
          padding: 0.6rem 0.8rem;
          margin: 0.3rem 0;
          background: var(--bg-card);
          border-radius: var(--radius-sm);
          border-left: 3px solid var(--primary);
          cursor: pointer;
          transition: var(--transition);
        }

        .chunk-item:hover {
          background: rgba(254, 44, 85, 0.04);
          border-left-color: var(--primary-light);
          transform: translateX(2px);
        }

        .chunk-item-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 4px;
        }

        .chunk-index {
          font-size: 0.75rem;
          font-weight: 700;
          color: var(--primary);
          background: rgba(254, 44, 85, 0.1);
          padding: 1px 6px;
          border-radius: 4px;
          flex-shrink: 0;
        }

        .chunk-arrow {
          margin-left: auto;
          color: var(--text-secondary);
          flex-shrink: 0;
          opacity: 0.5;
          transition: var(--transition);
        }

        .chunk-item:hover .chunk-arrow {
          opacity: 1;
          color: var(--primary);
          transform: translateX(2px);
        }

        .chunk-headings {
          font-size: 0.85rem;
          color: var(--primary);
          font-weight: 500;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .chunk-content {
          font-size: 0.9rem;
          color: var(--text-primary);
          line-height: 1.7;
          white-space: pre-wrap;
          word-break: break-word;
          max-height: 120px;
          overflow-y: auto;
          scrollbar-width: thin;
        }

        .chunk-content::-webkit-scrollbar {
          width: 4px;
        }

        .chunk-content::-webkit-scrollbar-thumb {
          background: var(--border);
          border-radius: 2px;
        }

        .chunk-meta {
          font-size: 0.8rem;
          color: var(--text-secondary);
          margin-top: 4px;
        }

        /* Modal */
        .modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.5);
          backdrop-filter: blur(4px);
          z-index: 9999;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 2rem;
          animation: fadeIn 0.2s ease;
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        .modal-content {
          background: var(--bg-primary);
          border-radius: var(--radius);
          width: 100%;
          max-width: 900px;
          max-height: 90vh;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
          animation: slideUp 0.25s ease;
        }

        @keyframes slideUp {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }

        .modal-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 1rem 1.25rem;
          border-bottom: 1px solid var(--border);
          flex-shrink: 0;
        }

        .modal-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 600;
          font-size: 1rem;
        }

        .modal-chunk-label {
          color: var(--primary);
          background: rgba(254, 44, 85, 0.1);
          padding: 2px 8px;
          border-radius: 6px;
          font-size: 0.8rem;
          margin-left: 4px;
        }

        .modal-headings {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          padding: 0.75rem 1.25rem;
          border-bottom: 1px solid var(--border);
          background: var(--bg-card);
        }

        .modal-heading-tag {
          font-size: 0.8rem;
          color: var(--primary);
          background: rgba(254, 44, 85, 0.06);
          padding: 2px 10px;
          border-radius: 12px;
          font-weight: 500;
        }

        .modal-stats {
          display: flex;
          gap: 16px;
          padding: 0.6rem 1.25rem;
          border-bottom: 1px solid var(--border);
          font-size: 0.85rem;
          color: var(--text-secondary);
          background: var(--bg-card);
          flex-shrink: 0;
        }

        .modal-stat-content-length {
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .modal-stat-full {
          color: var(--primary);
          font-weight: 500;
          font-size: 0.8rem;
        }

        .modal-body {
          flex: 1;
          min-height: 0;
          overflow-y: auto;
          padding: 1.25rem;
          scrollbar-width: thin;
        }

        .modal-body::-webkit-scrollbar {
          width: 6px;
        }

        .modal-body::-webkit-scrollbar-track {
          background: transparent;
        }

        .modal-body::-webkit-scrollbar-thumb {
          background: var(--border);
          border-radius: 3px;
        }

        .modal-content-text {
          font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
          font-size: 0.85rem;
          line-height: 1.7;
          white-space: pre-wrap;
          word-break: break-word;
          color: var(--text-primary);
          margin: 0;
          user-select: text;
        }

        .chunk-more {
          text-align: center;
          padding: 0.5rem;
          color: var(--text-secondary);
          font-size: 0.9rem;
        }
      `}</style>
    </div>
  );
}

export default RagUpload;
