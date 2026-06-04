# HotpotQA 多跳推理链可视化系统

> 基于 **Neo4j 图数据库** 与 **Flask** 的 HotpotQA 多跳支持事实链存储、检索、聚类与交互式可视化工具。  
> 前端采用 **vis‑network** 实现力导向图与网格布局，支持玻璃拟态 / 结构线风格。

## 功能

- **关键词检索**：搜索问题或句子，页面加载自动展示示例问题
- **多跳支持链可视化**：展示某一问题的所有支持句子及其推理路径（有向图）
- **文档聚类**：按被引用次数对文档分组，以网格状色块展示
- **高性能导入**：批量事务、索引优化，支持万级数据快速导入

## 技术栈

| 层次     | 技术 / 工具                            |
| -------- | -------------------------------------- |
| 数据存储 | **Neo4j** 图数据库 (5.x)                |
| 后端 API | Python **Flask** + **neo4j‑driver**     |
| 前端     | HTML5 + JavaScript + **vis‑network**    |
| 样式     | 玻璃拟态 (Glassmorphism) + 结构线背景   |
| 数据格式 | HotpotQA JSON (由 `.parquet` 转换而来)   |

## 项目结构
```
hotpot-multihop/
├── app.py                 # Flask 后端，提供 REST API
├── load_data.py           # 数据导入 Neo4j 脚本
├── requirements.txt       # Python 依赖
├── templates/
│   └── index.html         # 前端可视化页面
└── README.md
```

## 安装与运行

### 1. 环境要求
- **Python 3.8+**
- **Neo4j 数据库** (4.4 版本，本地或远程均可)
- 推荐使用虚拟环境 (venv)

### 2. 启动 Neo4j
如果使用 **Docker**：
```bash
docker run -d \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:5
```
或使用 Neo4j Desktop 创建本地数据库，确保 Bolt 端口 (`7687`) 可访问，并将监听地址设置为 `0.0.0.0`。

### 3. 安装 Python 依赖
bash
pip install -r requirements.txt


requirements.txt 内容：

flask>=2.0
neo4j>=5.0


### 4. 准备数据
将 HotpotQA 数据集（JSON 格式）放置到 `load_data.py` 中指定的路径，或修改脚本中的 `JSON_PATH` 变量。

> 数据集可从 [HotpotQA 官网](https://hotpotqa.github.io/) 下载，或自行从原始 parquet 文件转换。

### 5. 导入数据到 Neo4j
在导入前，建议先进入 Neo4j Browser (`http://localhost:7474`) 创建索引：
```
CREATE INDEX question_id FOR (q:Question) ON (q.id);
CREATE INDEX document_title FOR (d:Document) ON (d.title);
CREATE INDEX sentence_lookup FOR (s:Sentence) ON (s.doc_title, s.index);
```

然后运行导入脚本：
```
bash
python load_data.py
```
脚本采用批量事务（每 200 条提交），并自动创建节点与关系，预期 9 万问题数据约 20 分钟内完成导入。

### 6. 启动后端服务
修改 `app.py` 中的数据库连接地址和密码：
```python
driver = GraphDatabase.driver("bolt://192.168.x.x:7687", auth=("neo4j", "your_password"))
```
运行：
```
bash
python app.py
```
服务默认监听 `http://localhost:5000`。

### 7. 打开前端页面
浏览器访问 [http://localhost:5000](http://localhost:5000)，即可使用搜索、支持链展示和文档聚类功能。

## API 接口

| 端点               | 方法 | 说明                           |
| ------------------ | ---- | ------------------------------ |
| `/`                | GET  | 前端可视化页面                  |
| `/api/search?q=`   | GET  | 关键词搜索问题或句子            |
| `/api/examples`    | GET  | 随机获取 5 个示例问题           |
| `/api/chain?id=`   | GET  | 获取指定问题的多跳支持链数据    |
| `/api/cluster`     | GET  | 获取文档聚类信息（按引用量分桶）|

## 图模型

- **节点**：`Question`、`Document`、`Sentence`
- **关系**：
  - `(:Question)-[:HAS_CONTEXT]->(:Document)`
  - `(:Document)-[:CONTAINS]->(:Sentence)`
  - `(:Sentence)-[:SUPPORTS {q_id}]->(:Sentence)`

多跳支持链由相邻支持句子间的 `SUPPORTS` 有向边构成，查询时直接通过 Cypher 路径匹配获取。

## 注意事项

- **密码与安全**：请勿将真实数据库密码上传至公开仓库。建议修改 `app.py` 和 `load_data.py` 中的密码为占位符，本地运行时再替换。
- **数据路径**：`load_data.py` 中的 JSON 文件路径需要根据实际情况修改。
- **网络配置**：如果 Neo4j 部署在远程虚拟机，请确保防火墙已开放 7687 端口，且 Neo4j 监听地址为 `0.0.0.0`。
- **前端库**：vis‑network 通过 CDN 加载，如果网络不稳定可下载到本地 `static/` 目录并修改引用路径。

## 未来改进

- 集成 Neo4j GDS 实现 Louvain、PageRank 等高级聚类与中心性分析
- 支持用户自定义多跳路径查询（任意实体间路径发现）
- 后端与前端分离，部署至云平台（如 Render、Vercel）
- 使用 `neo4j-admin import` 处理更大规模数据

## 许可证

本项目仅用于学习和演示目的，数据版权归 HotpotQA 数据集作者所有。


*如果在运行过程中遇到问题，欢迎提 Issue 或 Pull Request。*
