# 治疗方案管理系统

一个用于管理和搜索医疗治疗方案的Web应用程序，支持Excel文件上传、数据分析和治疗卡片生成。

## 功能特点

- 用户认证与授权系统
- Excel模板下载与上传
- 治疗方案数据提取与分析
- 治疗卡片自动生成
- 基于关键词的搜索功能（支持按疾病、方案名称等搜索）
- 风险分级与评估
- 响应式Web界面

## 技术栈

- **后端**: Python, Flask, Flask-RESTful, PyMongo
- **数据库**: MongoDB
- **认证**: JWT (JSON Web Tokens)
- **前端**: HTML, CSS, JavaScript, Bootstrap
- **数据处理**: Pandas, Openpyxl

## 环境要求

- Python 3.8+
- MongoDB 4.4+
- 现代浏览器

## 安装与设置

### 使用Git克隆

```bash
git clone https://github.com/your-username/therapy-management-system.git
cd therapy-management-system
```

### 创建虚拟环境并安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 环境变量配置

创建一个`.env`文件，包含以下内容：

```
MONGO_URI=mongodb://localhost:27017/therapy_db
JWT_SECRET_KEY=your_secret_key
TEMPLATES_FOLDER=templates
UPLOADS_FOLDER=uploads
DEBUG=True
```

### 数据库准备

确保MongoDB服务已启动，系统会自动创建必要的数据库和集合。

## 运行应用

```bash
# 使用自动启动脚本(推荐)
bash start_server.sh

# 或直接运行
python app.py
```

服务默认运行在 http://localhost:5000

## API接口说明

### 1. 用户注册
- **URL**: `/api/register`
- **方法**: POST
- **数据格式**: JSON
```json
{
    "username": "用户名",
    "password": "密码",
    "email": "邮箱"
}
```

### 2. 用户登录
- **URL**: `/api/login`
- **方法**: POST
- **数据格式**: JSON
```json
{
    "username": "用户名",
    "password": "密码"
}
```

### 3. 下载模板
- **URL**: `/api/template`
- **方法**: GET
- **认证**: 不需要

### 4. 上传文件
- **URL**: `/api/upload`
- **方法**: POST
- **认证**: 需要JWT Token
- **数据格式**: Form-data
  - key: file
  - value: Excel文件数据

### 5. 生成治疗卡片
- **URL**: `/api/generate-card`
- **方法**: POST
- **认证**: 需要JWT Token
- **数据格式**: JSON
```json
{
    "file_id": "文件ID"
}
```

### 6. 搜索治疗卡片
- **URL**: `/api/search-cards`
- **方法**: GET
- **认证**: 需要JWT Token
- **参数**:
  - keyword: 搜索关键词（方案名称、疾病名称等）
  - page: 页码（默认1）
  - limit: 每页数量（默认10）

## 认证说明

除了注册和登录接口，其他所有接口都需要在请求头中包含JWT Token：

```
Authorization: Bearer <your_token>
```

## 模板说明

系统使用Excel模板收集治疗方案信息，包括以下字段：

- 基础信息: 来源、疾病、方案名称、方案简介、治疗时间、费用范围
- 疗效数据: 总人数、有效人数、临床治愈人数、未复发人数、有效率、临床治愈率、未复发率
- 风险信息: 一级风险表现、二级风险表现、三级风险表现、风险概率和、风险评级
- 评分信息: 受益评级、便利度评级、受益评分、风险评分、便利度评分

## 开发指南

### 目录结构

- `app.py`: 主应用程序入口和API实现
- `templates/`: 前端HTML模板
- `static/`: 静态资源(CSS, JavaScript等)
- `uploads/`: 用户上传的文件存储位置
- `venv/`: Python虚拟环境
- `requirements.txt`: Python依赖列表

### 添加新功能

1. 在`app.py`中添加新的API路由
2. 更新前端HTML模板
3. 更新测试脚本
4. 更新文档

## 贡献指南

1. Fork本仓库
2. 创建你的功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交你的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建一个Pull Request

## 许可证

本项目采用MIT许可证 - 详见 [LICENSE.md](LICENSE.md) 文件 