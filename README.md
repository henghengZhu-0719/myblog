# 全栈个人综合管理平台 (Full-Stack Personal Management System)

这是一个集成了博客内容管理、招聘信息聚合、简历投递跟踪与智能记账功能的现代化全栈应用。项目采用前后端分离架构，旨在解决个人信息分散、管理效率低下的问题。

## 🚀 功能特性

### 1. 📝 博客系统
- 文章的发布、编辑、删除与查看。
- 支持 Markdown 格式编辑与实时预览。
- 用户账户管理（注册、登录、个人主页）。

### 2. 🕷️ 招聘信息聚合 (Job Aggregation)
- 自动化爬虫（基于 Playwright）定时抓取特定招聘网站（如南昌人才网）的职位信息。
- 提供可视化的招聘数据看板（基于 ECharts），展示职位发布的周/月度趋势。

### 3. 💼 简历投递助手 (Boss Assistant)
- **批量职位抓取**：支持输入多个职位详情页 URL，系统自动调用爬虫抓取职位标题、地区、详情等信息。
- **投递记录管理**：一键保存抓取到的职位信息，方便后续跟踪投递状态。

### 4. 💰 智能记账 (Intelligent Billing)
- **AI 票据识别**：集成多模态大模型（Qwen-VL），支持上传小票/收据图片。
- **自动结构化**：自动提取消费金额、类别、商家、时间等信息，生成结构化的 JSON 数据并入库。
- **账单统计**：提供多维度的消费统计与查询功能。

## 🛠️ 技术栈

### 后端 (Backend)
- **框架**: Python (FastAPI)
- **数据库**: MySQL + SQLAlchemy (ORM)
- **爬虫**: Playwright, BeautifulSoup4
- **AI集成**: OpenAI SDK (对接阿里云百炼 Qwen-VL)
- **工具**: Uvicorn, Pydantic

### 前端 (Frontend)
- **框架**: React + Vite
- **路由**: React Router DOM
- **UI/可视化**: ECharts
- **HTTP客户端**: Axios

### 部署与运维 (DevOps)
- **容器化**: Docker, Docker Compose
- **反向代理**: Nginx
- **脚本**: Shell (启动脚本)

## 🏁 快速开始

### 方式一：Docker 一键启动（推荐）

确保本地已安装 Docker 和 Docker Compose。

```bash
# 启动所有服务（数据库、后端、前端）
docker-compose up --build -d
```

- **前端访问**: http://localhost
- **后端文档**: http://localhost:8001/docs
- **数据库**: localhost:3306 (用户: root, 密码: 020110)

### 方式二：本地开发运行

#### 1. 启动后端

```bash
cd blog_backend

# 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 启动服务
./start.sh
# 或手动运行: uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

#### 2. 启动前端

```bash
cd blog_frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务通常运行在 `http://localhost:5173`。

## 📂 目录结构

```
.
├── blog_backend/        # 后端代码
│   ├── models/          # 数据库模型
│   ├── routers/         # API 路由
│   ├── schemas/         # Pydantic 数据校验模型
│   ├── utils/           # 工具类（爬虫、AI识别等）
│   ├── main.py          # 入口文件
│   └── dockerfile
├── blog_frontend/       # 前端代码
│   ├── src/             # React 源码
│   ├── nginx.conf       # Nginx 配置文件
│   └── dockerfile
├── docker-compose.yml   # 容器编排配置
└── README.md            # 项目文档
```

## 📝 许可证

[MIT](LICENSE)
