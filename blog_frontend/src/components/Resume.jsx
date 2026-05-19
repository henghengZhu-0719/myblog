import React from 'react';

function Resume() {
  return (
    <div className="resume-page">
      <div className="resume-content">
        {/* 个人信息 */}
        <section className="resume-section personal-header">
          <div className="personal-info">
            <h1 className="name">朱永强</h1>
            <div className="contact-row">
              <span>📧 Zhuyq0719@foxmail.com</span>
              <span>📱 15870018742</span>
            </div>
            <div className="job-intent">
              求职意向：<strong>AI Agent 开发</strong>
            </div>
          </div>
        </section>

        {/* 教育背景 */}
        <section className="resume-section">
          <h2 className="section-title">教育背景</h2>
          <div className="edu-item">
            <div className="edu-row">
              <span className="edu-school">上海对外经贸大学 · 硕士 · 应用统计专业</span>
              <span className="edu-date">2024.09 - 2026.07</span>
            </div>
            <div className="edu-detail">GPA 3.4</div>
          </div>
          <div className="edu-item">
            <div className="edu-row">
              <span className="edu-school">东华理工大学 · 本科 · 统计学专业</span>
              <span className="edu-date">2019.09 - 2023.07</span>
            </div>
            <div className="edu-detail">GPA 3.1</div>
          </div>
          <div className="edu-honors">
            <span className="honor-badge">校三等奖学金</span>
            <span className="honor-badge">2022 美国大学生数学建模大赛 M奖</span>
            <span className="honor-badge">第九届"泰迪杯"数据挖掘挑战赛 全国三等奖</span>
          </div>
        </section>

        {/* 专业技能 */}
        <section className="resume-section">
          <h2 className="section-title">专业技能</h2>
          <ul className="skill-list">
            <li><strong>Agent 开发与架构：</strong>熟练使用 LangGraph、LangChain 工作流编排；熟悉 ReAct、Plan-and-Execute 等推理范式；具备复杂工作流设计能力</li>
            <li><strong>RAG 开发：</strong>掌握文档切块、向量索引构建与多阶段检索 Pipeline 设计，熟悉混合检索（Dense+BM25）、RRF 融合排序及 Cross-Encoder 精排方法</li>
            <li><strong>数据处理：</strong>熟悉 Python 爬虫开发，基于 Requests 与 Playwright 实现静态与动态页面采集及数据解析入库</li>
            <li><strong>后端开发与数据库：</strong>熟悉 FastAPI 后端开发；熟练使用 Qdrant、FAISS 等向量数据库及 MySQL 关系型数据库</li>
            <li><strong>工程化与部署：</strong>熟悉 Docker 容器化部署，具备服务镜像构建与多容器编排（Docker Compose）能力；掌握常用 Linux 运维操作</li>
          </ul>
        </section>

        {/* 实习经历 */}
        <section className="resume-section">
          <h2 className="section-title">实习经历</h2>
          <div className="exp-item">
            <div className="exp-header">
              <div>
                <span className="exp-company">中碳普惠云科技有限公司</span>
                <span className="exp-role">Agent 应用开发实习生</span>
              </div>
              <span className="exp-date">2025.05 - 2025.10</span>
            </div>
            <p className="exp-bg">面向企业碳中和政策咨询场景，参与构建碳中和领域智能问答 Agent，解决政策信息分散和人工清洗效率低等问题。</p>
            <ul className="exp-duties">
              <li>构建约 8000 条碳中和政策语料，基于 LoRA 对 Qwen-14B 模型进行指令微调，使模型在领域问答任务中的语义相似度提升约 15%；同时分析微调带来的泛化能力下降问题（约 4%）</li>
              <li>优化问答系统检索模块，将固定长度切分重构为语义切分策略以保障上下文完整性；引入向量检索与 BM25 混合检索与重排序机制</li>
              <li>基于 FastMCP 封装标准化工具接口，将外部业务数据（如仓库、发票等）接入 Agent 工作流，实现结构化数据查询与问答能力扩展</li>
              <li>构建数据采集模块，编写爬虫脚本抓取碳中和政策数据，支持静态页面解析（Requests）与动态页面渲染（Playwright），并进行数据清洗与去重，持续扩充高质量知识库语料</li>
            </ul>
          </div>
        </section>

        {/* 项目经历 */}
        <section className="resume-section">
          <h2 className="section-title">项目经历</h2>

          <div className="exp-item">
            <div className="exp-header">
              <span className="exp-company">基于 RAG 的私域知识库问答系统</span>
              <span className="exp-date">2025.12 - 2026.01</span>
            </div>
            <p className="exp-bg">面向个人/企业非结构化文档管理场景，针对知识分散、检索困难的问题，构建 RAG 知识库系统，实现文档解析、语义检索与智能问答闭环。</p>
            <ul className="exp-duties">
              <li>基于 AST 设计层级化 Markdown 切块模块：保留标题路径上下文链，对代码块/表格做原子保护，结合 LLM 代码摘要与 VLM 图像描述将非文本转为可检索语义，16 篇长文本（总计 35 万 token）上实测平均 chunk 405 token，小于 50 token 碎片 chunk &lt; 3%</li>
              <li>基于 Qdrant 构建混合检索体系（Dense + BM25 Sparse），设计"向量召回、关键词召回、RRF 融合和 Cross-Encoder 重排序"的三阶段 Pipeline，相比纯向量检索 Precision@5 提升 11.2%</li>
              <li>基于 LangGraph 构建 RAG 工作流，在传统检索流程基础上引入意图识别与 Query Rewrite，对用户查询进行预处理，并结合检索评估与自适应重试机制，构建多阶段优化的检索流程</li>
            </ul>
          </div>

          <div className="exp-item">
            <div className="exp-header">
              <span className="exp-company">DeepResearch Agent 系统</span>
              <span className="exp-date">2026.02 - 2026.04</span>
            </div>
            <p className="exp-bg">针对通用 LLM 在复杂研究任务中存在的上下文遗忘相关痛点，设计并落地一套支持自主规划、多轮反思与结构化产出的多智能体研究系统，覆盖"任务拆解→信息检索→反思迭代→报告生成"全链路。</p>
            <ul className="exp-duties">
              <li>设计并实现了一个基于 LangChain 的多智能体研究系统，支持主 Agent 自主规划、委派子任务、生成结构化研究报告</li>
              <li>构建分层记忆系统（MemoryManager）：包含工作记忆（短期上下文）和解析记忆（结构化规则），支持 Qdrant 向量数据库双重检索，自动注入相关记忆到对话上下文</li>
              <li>实现研究型子 Agent 的"搜索-反思-再搜索"，结合 Tavily 搜索引擎和思维反思工具，确保研究质量和深度，同时通过工具调用预算控制防止过度搜索</li>
              <li>实现 RAG 检索子 Agent，支持对分层记忆（历史工作记忆+解析记忆）的跨层语义检索，同时具备对历史研究报告的相似度召回能力，实现研究知识的跨任务复用</li>
            </ul>
          </div>
        </section>
      </div>

      <style>{`
        .resume-page {
          max-width: 1000px;
          margin: 0 auto;
          padding: 0 1rem 3rem;
        }

        .resume-content {
          background: var(--bg-main);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          box-shadow: var(--shadow-hover);
          padding: 2.5rem 3rem;
        }

        /* 个人信息头部 */
        .personal-header {
          text-align: center;
          padding-bottom: 2rem;
          border-bottom: 2px solid var(--border);
          margin-bottom: 2rem;
        }

        .name {
          font-size: 2.2rem;
          font-weight: 700;
          margin: 0 0 0.75rem;
          background: var(--primary-gradient);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .contact-row {
          display: flex;
          justify-content: center;
          gap: 2rem;
          font-size: 1rem;
          color: var(--text-secondary);
          margin-bottom: 0.75rem;
          flex-wrap: wrap;
        }

        .job-intent {
          font-size: 1.1rem;
          color: var(--text-primary);
        }

        .job-intent strong {
          color: var(--primary);
        }

        /* 通用章节 */
        .resume-section {
          margin-bottom: 2rem;
        }

        .section-title {
          font-size: 1.3rem;
          font-weight: 700;
          color: var(--text-primary);
          padding-bottom: 0.5rem;
          border-bottom: 2px solid var(--primary);
          margin-bottom: 1.25rem;
          position: relative;
        }

        .section-title::after {
          content: '';
          position: absolute;
          bottom: -2px;
          left: 0;
          width: 60px;
          height: 2px;
          background: var(--primary);
        }

        /* 教育背景 */
        .edu-item {
          margin-bottom: 0.75rem;
        }

        .edu-row {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .edu-school {
          font-weight: 600;
          font-size: 1.05rem;
        }

        .edu-date {
          color: var(--text-secondary);
          font-size: 0.9rem;
          white-space: nowrap;
        }

        .edu-detail {
          color: var(--text-secondary);
          font-size: 0.95rem;
          margin-top: 0.15rem;
        }

        .edu-honors {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-top: 0.75rem;
        }

        .honor-badge {
          display: inline-block;
          padding: 0.3rem 0.8rem;
          background: rgba(254, 44, 85, 0.08);
          color: var(--primary);
          border-radius: 20px;
          font-size: 0.85rem;
          font-weight: 500;
        }

        /* 专业技能 */
        .skill-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .skill-list li {
          padding: 0.5rem 0;
          padding-left: 1.2rem;
          position: relative;
          line-height: 1.7;
          color: var(--text-primary);
        }

        .skill-list li::before {
          content: '▸';
          position: absolute;
          left: 0;
          color: var(--primary);
          font-weight: bold;
        }

        /* 经历卡片（实习+项目） */
        .exp-item {
          margin-bottom: 1.5rem;
        }

        .exp-item:last-child {
          margin-bottom: 0;
        }

        .exp-header {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-bottom: 0.5rem;
        }

        .exp-company {
          font-weight: 700;
          font-size: 1.1rem;
          color: var(--text-primary);
        }

        .exp-role {
          font-size: 0.95rem;
          color: var(--text-secondary);
          margin-left: 0.75rem;
        }

        .exp-date {
          color: var(--text-secondary);
          font-size: 0.9rem;
          white-space: nowrap;
        }

        .exp-bg {
          color: var(--text-secondary);
          font-size: 0.95rem;
          line-height: 1.7;
          margin: 0.5rem 0;
        }

        .exp-duties {
          list-style: none;
          padding: 0;
          margin: 0.25rem 0 0;
        }

        .exp-duties li {
          padding: 0.35rem 0;
          padding-left: 1.2rem;
          position: relative;
          line-height: 1.7;
          font-size: 0.95rem;
          color: var(--text-primary);
        }

        .exp-duties li::before {
          content: '•';
          position: absolute;
          left: 0;
          color: var(--primary);
          font-weight: bold;
        }

        /* 打印样式 */
        @media print {
          .resume-content {
            box-shadow: none;
            border: none;
            padding: 0;
          }
          .personal-header {
            border-bottom-color: #ccc;
          }
        }

        /* 移动端适配 */
        @media (max-width: 600px) {
          .resume-page {
            padding: 0 0.5rem 2rem;
          }
          .resume-content {
            padding: 1.5rem 1.25rem;
          }
          .name {
            font-size: 1.7rem;
          }
          .contact-row {
            gap: 1rem;
            font-size: 0.9rem;
          }
          .section-title {
            font-size: 1.1rem;
          }
          .exp-header {
            flex-direction: column;
          }
          .exp-date {
            font-size: 0.85rem;
          }
          .edu-row {
            flex-direction: column;
          }
        }
      `}</style>
    </div>
  );
}

export default Resume;
