# 治疗卡片管理系统 API

这是一个基于 Flask 的治疗卡片管理系统后端 API。

## 环境要求

- Python 3.8+
- MongoDB
- 其他依赖见 requirements.txt

## 安装步骤

1. 克隆代码库
2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 确保 MongoDB 服务已启动并可访问

4. 运行应用：
```bash
python app.py
```

## API 接口说明

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
- **认证**: 需要 JWT Token
- **数据格式**: Form-data
  - key: file
  - value: 文件数据

### 5. 生成治疗卡片
- **URL**: `/api/generate-card`
- **方法**: POST
- **认证**: 需要 JWT Token
- **数据格式**: JSON
```json
{
    "file_id": "文件ID"
}
```

### 6. 搜索治疗卡片
- **URL**: `/api/search-cards`
- **方法**: GET
- **认证**: 需要 JWT Token
- **参数**:
  - keyword: 搜索关键词（可选）
  - page: 页码（可选，默认1）
  - limit: 每页数量（可选，默认10）

## 认证说明

除了注册和登录接口，其他所有接口都需要在请求头中包含 JWT Token：

```
Authorization: Bearer <your_token>
```

## 错误处理

所有错误响应都会包含一个 error 字段，说明具体的错误信息。例如：

```json
{
    "error": "Invalid username or password"
}
``` 