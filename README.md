# DeepSearch: Advanced Search Engine

## Overview

DeepSearch is a powerful search engine that combines traditional information retrieval with AI capabilities. It features a distributed inverted index, boolean search operations, phrase matching, and AI-powered query expansion.

## Installation

### Prerequisites

- Python 3.8+
- MongoDB server
- OpenAI API key
- DeepSeek API key

### Setup Instructions

1. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```
   
   Note: Some packages may need to be added or removed depending on your environment.

2. **Prepare Inverted Index Data**

   Extract the data archive:
   ```bash
   unzip inverted_index.zip
   ```
   
   This contains the base dataset. You can expand it by adding more data in the same format.

   If you do not have the inverted index data and the content data, you can download it from [here](https://huggingface.co/datasets/Luzer0417/search_engine_data/tree/main).
   
3. **Configure Database**

   Edit `database/process_distributed_db.py`:
   - Replace MongoDB server address:
     ```python
     client = MongoClient('mongodb://35.214.XXX.XXX:27017')
     ```
   - Update data directory path:
     ```python
     directory = "/Users/luzer/Downloads/inverted_index"
     ```
     
   Run the database processing script:
   ```bash
   python database/process_distributed_db.py
   ```

4. **Configure API Connections**

   Update MongoDB connection in `test/search_func.py`:
   ```python
   client = pymongo.MongoClient("mongodb://35.214.XXX.XXX:27017")
   ```
   
   Update DeepSeek API key in `test/ds_api.py`:
   ```python
   api_key = "sk-96aaae6a98254cd68403e7ffdf7XXXXX"
   ```
   
   Update OpenAI API key in `test/query_extension.py`:
   ```python
   openai.api_key = "sk-proj-XXX"
   ```

5. **Launch Application**

   Run the application:
   ```bash
   python test/main.py
   ```
   
   The web interface will be available at the configured port (default: 8080).
   You can modify the port in `main.py`.

## Features

- Full-text search with boolean operators (AND, OR)
- Phrase matching for exact quotes
- AI-powered query expansion using GPT
- Dynamic search suggestions
- Keyword highlighting in results
- Dark/light mode toggle
- Fast retrieval using distributed inverted index
- Persistent cache system for improved performance

## Architecture

- **Frontend**: HTML/CSS/JavaScript with Vue.js
- **Backend**: Python FastAPI
- **Database**: MongoDB for inverted index storage
- **AI Integration**: OpenAI GPT and DeepSeek AI

## Search Syntax

- Simple search: `machine learning`
- Phrase search: `"machine learning"`
- Boolean AND: `machine AND learning`
- Boolean OR: `machine OR learning`

## Performance

The system uses a multi-layer caching approach:
- Memory cache for fastest access
- Disk-based persistent cache
- MongoDB as the source of truth

This architecture balances performance and reliability while minimizing database load.

# 中文版说明

## 概述

DeepSearch 是一个功能强大的搜索引擎，结合了传统信息检索与人工智能技术。它具有分布式倒排索引、布尔搜索操作、短语匹配和 AI 驱动的查询扩展功能。

## 安装

### 前提条件

- Python 3.8+
- MongoDB 服务器
- OpenAI API 密钥
- DeepSeek API 密钥

### 安装步骤

1. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```
   
   注意：根据您的环境，可能需要添加或删除某些包。

2. **准备倒排索引数据**

   解压数据存档：
   ```bash
   unzip inverted_index.zip
   ```
   
   这包含基础数据集。您可以按照相同的格式添加更多数据来扩展它。

   如果您没有倒排索引数据和内容数据，可以从 [这里](https://huggingface.co/datasets/Luzer0417/search_engine_data/tree/main) 下载。

3. **配置数据库**

   编辑 `database/process_distributed_db.py`：
   - 替换 MongoDB 服务器地址：
     ```python
     client = MongoClient('mongodb://35.214.XXX.XXX:27017')
     ```
   - 更新数据目录路径：
     ```python
     directory = "/Users/luzer/Downloads/inverted_index"
     ```
     
   运行数据库处理脚本：
   ```bash
   python database/process_distributed_db.py
   ```

4. **配置 API 连接**

   更新 `test/search_func.py` 中的 MongoDB 连接：
   ```python
   client = pymongo.MongoClient("mongodb://35.214.XXX.XXX:27017")
   ```
   
   更新 `test/ds_api.py` 中的 DeepSeek API 密钥：
   ```python
   api_key = "sk-96aaae6a98254cd68403e7ffdf7XXXXX"
   ```
   
   更新 `test/query_extension.py` 中的 OpenAI API 密钥：
   ```python
   openai.api_key = "sk-proj-XXX"
   ```

5. **启动应用程序**

   运行应用程序：
   ```bash
   python test/main.py
   ```
   
   Web 界面将在配置的端口上可用（默认：8080）。
   您可以在 `main.py` 中修改端口。

## 功能

- 支持布尔运算符（AND、OR）的全文搜索
- 精确引用的短语匹配
- 基于 GPT 的 AI 驱动查询扩展
- 动态搜索建议
- 结果中的关键词高亮显示
- 深色/浅色模式切换
- 使用分布式倒排索引实现快速检索
- 持久化缓存系统提升性能

## 架构

- **前端**：HTML/CSS/JavaScript 与 Vue.js
- **后端**：Python FastAPI
- **数据库**：MongoDB 用于倒排索引存储
- **AI 集成**：OpenAI GPT 和 DeepSeek AI

## 搜索语法

- 简单搜索：`machine learning`
- 短语搜索：`"machine learning"`
- 布尔 AND：`machine AND learning`
- 布尔 OR：`machine OR learning`

## 性能

系统使用多层缓存方法：
- 内存缓存实现最快访问
- 基于磁盘的持久化缓存
- MongoDB 作为数据真实来源

这种架构在最小化数据库负载的同时平衡了性能和可靠性。



# UI
![image](./img/5181742913177_.pic.jpg)
![image](./img/5171742912952_.pic.jpg)