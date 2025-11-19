# Daily Paper RSS AI Enhance

**基于 RSS 订阅的智能学术论文推荐系统**

> 📚 通过 AI 增强和 Zotero 文献库智能排序,自动发现与你研究兴趣相关的最新学术论文

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-package%20manager-orange.svg)](https://github.com/astral-sh/uv)

---

## 💡 项目简介

<p align="center">
  <img src="assets/logo.png" alt="logo" width="100"/>
</p>

这是一个**本地化运行**的学术论文推荐系统,集成了 RSS 订阅、AI 智能摘要生成和基于 Zotero 文献库的个性化排序功能。系统能够:

- 📡 **自动抓取**多个学术期刊的最新论文(arXiv、Nature 等)
- 🤖 **AI 增强**:使用大语言模型生成结构化中/英文摘要
- 🎯 **智能排序**:基于你的 Zotero 文献库,通过嵌入向量相似度计算推荐最相关的论文
- 💾 **本地处理**:所有数据在本地存储和处理,完全可控,仅当使用本地AI时,如果使用线上供应商时部分数据会上传到供应商服务器处理
- 🌐 **Web 界面**:提供美观的响应式界面,支持搜索、筛选和收藏功能

### ⚠️ 开发状态

**RSS 源限制**: 
- 目前完全支持的源: **arXiv** 和 **Nature 系列**(通过官方 API)
- 实验性支持: Science、Optica、APS(网页抓取,稳定性不佳)
- 大部分学术期刊的 RSS 不包含摘要,需要额外抓取网页
- Science 和 APS 网站易受拦截,抓取稳定性极差,本人非cs方向,不知道有什么好的方案,欢迎提出解决方案

**法律提醒**: 
本项目仅作学习交流用途,请注意遵守所在地法律法规,尤其是数据爬取相关规定。

这是本人第一次在 GitHub 上传代码,如有不当之处,欢迎指正! 🙏

---

## ✨ 核心功能

### 🎯 本地化处理 (支持本地 AI 提供商如 Ollama)
- ✅ 所有数据在本地机器上抓取和处理
- ✅ 无云服务依赖 - 完全掌控你的数据
- ✅ 基于 JSONL 格式存储,透明且易于迁移

### 🤖 AI 智能增强
- ✅ 使用兼容 OpenAI 的大语言模型进行结构化摘要
- ✅ 生成内容:核心要点(TL;DR)、研究动机、研究方法、研究结果、结论
- ✅ **高性价比**:借助 Zotero 推荐,仅对相关论文生成 AI 内容
- ✅ 可配置模型(默认: qwen3-30b-a3b-instruct-2507、deepseek-chat 等)
- ✅ 支持中英文输出,可在设置页面切换

### 📚 智能 Zotero 集成
- ✅ 基于你现有 Zotero 文献库的相似度排序论文
- ✅ 使用嵌入向量模型进行语义匹配(默认: Qwen3-Embedding-8B)
- ✅ 对最近添加的文献进行时间衰减加权
- ✅ 自动检测文献夹并重新排序

### 📡 多源 RSS 订阅支持
- ✅ **arXiv**: 物理学、量子物理、凝聚态物理、非线性科学、AI、CV 等
- ✅ **Nature 系列**: Nature、Nature Photonics、Nature Physics、Nature Communications 等
- ✅ 可扩展架构,支持添加更多来源

### 🌐 精美 Web 界面
- ✅ 按文献夹搜索和筛选
- ✅ 日期范围筛选
- ✅ 永久收藏夹系统(支持多文件夹管理)
- ✅ 收藏数据本地持久化存储
- ✅ 响应式设计,支持桌面和移动端

---

## 📸 界面截图

### 🏠 主页
显示最近的更新信息和系统状态

![主页](assets/home_page.png)

### 📚 论文页面
- 支持按日期、期刊、Zotero 文献夹筛选
- 每个论文卡片显示清晰的 Zotero 文献夹标签

![论文页面 1](assets/papers_page.png)

![论文页面 2](assets/paper_page2.png)

### 📑 论文详情页
显示完整的 AI 生成摘要,包括研究动机、方法、结果和结论
<p align="center">
  <img src="assets/paper_details.png" alt="论文详情" width="300"/>
</p>


### ⭐ 永久收藏夹系统
支持多文件夹分类管理,所有收藏数据永久保存在本地,重启浏览器后依然保留

![收藏夹系统](assets/favorites_system.png)

---

## 🚀 快速开始

### 💻 环境要求

- **Python 3.12+**
- **[uv](https://github.com/astral-sh/uv)** 包管理器
- **OpenAI 兼容 API** 访问权限(或本地 LLM 如 Ollama)
- **Zotero** 账户及 API 密钥

### 📥 安装步骤

#### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/Daily_Paper_RSS_AI_Enhance.git
cd Daily_Paper_RSS_AI_Enhance
```

#### 2. 安装依赖

```bash
uv sync
```

> **注意**: 首次安装可能需要下载 PyTorch 等大型包,请耐心等待。

#### 3. 配置环境变量

在系统环境变量中设置以下内容:

```bash
# 任何 OpenAI 兼容的提供商(必选), 可选:项目通过New-API网关关联本地LMStudio 
NEWAPI_KEY_AD=your_newapi_key
NEWAPI_BASE_URL=https://127.0.0.1:yourport/v1

# Zotero API (必选)
ZOTERO_KEY_AD=your_zotero_api_key
ZOTERO_ID=your_zotero_user_id

# Nature API (可选,仅当抓取 Nature 论文时需要)
NATURE_API_KEY=your_nature_api_key
```

**获取密钥指引:**

- **New-API 密钥和基础 URL**: (使用 OpenAI 兼容的提供商时仅需提供对应Base URL和密钥), 访问 [https://github.com/QuantumNous/new-api](https://github.com/QuantumNous/new-api) 生成。New-API 是一个开源 AI 网关,提供对多个 AI 提供商的访问(*在线*: OpenAI, Gemini, DeepSeek, Qwen, SiliconFlow; *本地*: Ollama, LMstudio 等)
- **Zotero 用户 ID**: 从 [https://www.zotero.org/settings/keys](https://www.zotero.org/settings/keys) 获取
- **Zotero API 密钥**: 在 [https://www.zotero.org/settings/keys/new](https://www.zotero.org/settings/keys/new) 生成(需要读取权限)
- **Nature API 密钥**: 在 [Springer Nature API Portal](https://dev.springernature.com/) 申请

#### 4. 自定义配置(可选)

运行 `main.py` 时可以自定义以下参数:

```bash
--sources           # RSS 来源和分类
--model_name        # 生成 AI 内容的模型名称
--embedding_model   # 生成嵌入向量的模型名称
--language          # 输出语言 (Chinese 或 English)
--max_workers       # 并行工作线程数
```

---

## 🎮 使用方法

### 运行模式

项目支持两种运行模式:

#### 1️⃣ 定时任务模式(推荐)

```bash
uv run main.py
```

程序将持续运行,按以下计划自动执行任务:
- **每日 08:00**: 抓取新论文、排序并生成 AI 摘要
- **每周日 10:00**: 重新排序所有论文并补充缺失的 AI 内容

#### 2️⃣ 立即执行模式

如需立即执行一次任务,可修改 `main.py` 底部代码:

```python
# 注释掉定时任务代码
# schedule.every().day.at("08:00").do(main, args=args).tag('daily-tasks')
# schedule.every().sunday.at("10:00").do(main_week_check, args=args).tag('weekly-tasks')
# while True:
#     schedule.run_pending()
#     time.sleep(60)

# 添加立即执行代码
main(args)
```

### 可选参数:

```bash
--sources "arxiv:physics+quant-ph+cond-mat+nlin,nature:nature+nphoton+ncomms"
  # RSS 来源和分类 (例如: arxiv:physics+quant-ph,nature:nature+nphoton)

--model_name "qwen3-30b-a3b-instruct-2507"
  # 生成 AI 内容的模型名称

--embedding_model "qwen3-embedding-8b"
  # 生成嵌入向量的模型名称

--language "Chinese"
  # 输出语言 (Chinese 或 English)

--max_workers 4
  # 并行工作线程数,增加可加快 AI 处理速度

--output-dir "data"
  # 输出文件目录 (默认: data)
```

### 执行流程:

 📅 **每日任务** (08:00 自动执行)

1. 从配置的 RSS 源抓取最新论文
2. 使用 Zotero 文献库嵌入向量对论文排序
3. 为相关论文生成 AI 摘要
4. 更新文件列表供 Web 界面使用

📊 **每周检查** (每周日 10:00 自动执行)

1. 根据最新的 Zotero 文献夹重排全部文章
2. 检查并补充缺失的 AI 生成内容

### 🌐 查看结果

#### 启动 API 服务器(推荐)

为了使用**永久收藏夹**功能,推荐使用内置的 Flask API 服务器:

```bash
uv run api_server.py
```

默认在 `http://127.0.0.1:8000` 启动服务器,然后在浏览器中访问该地址。

**自定义端口和主机**:

```bash
# 指定主机和端口
uv run api_server.py --host 0.0.0.0:8080
```

**功能特性**:
- ✅ 收藏数据永久保存在 `data/cache/favorites.json`
- ✅ 文件夹配置保存在 `data/cache/favorites_folders.json`
- ✅ 支持跨设备访问(修改 host 为 0.0.0.0)
- ✅ 数据自动持久化,无需手动保存

## 📁 项目结构

```
Daily_Paper_RSS_AI_Enhance/
├── ai/                          # AI 增强和排序模块
│   ├── enhance.py               # 基于 LLM 的论文摘要生成
│   ├── structure.py             # AI 输出的数据结构
│   ├── system.txt               # 系统提示词模板
│   ├── template.txt             # 用户提示词模板
│   └── zotero_recommender.py    # 基于嵌入向量的 Zotero 排序
├── fetcher/                     # RSS 抓取模块
│   └── rss_fetcher.py           # 通用多源 RSS 抓取器
├── data/                        # 论文数据存储 (JSONL 格式)
│   └── cache/                   # RSS 缓存、更新日志和收藏数据
│       ├── favorites.json       # 永久收藏数据
│       └── favorites_folders.json # 收藏夹文件夹列表
├── css/                         # 样式表
│   └── style.css                # 主样式文件
├── js/                          # JavaScript 脚本
│   └── app.js                   # 主应用逻辑
├── index.html                   # 主 Web 界面
├── api_server.py                # Flask API 服务器(收藏夹持久化)
├── main.py                      # 主程序入口点(定时任务调度)
├── logger_config.py             # 日志配置
├── test.py                      # 测试文件
├── pyproject.toml               # 项目依赖
├── uv.lock                      # 依赖锁文件
├── .gitignore                   # Git 忽略规则
├── DISCLAIMER.md                # 免责声明
├── LICENSE                      # AGPL-3.0 许可证
└── README.md                    # 本文件
```

---

## 🔧 配置详解

### 📡 RSS 来源配置

目前支持的 RSS 源:
- ✅ **arXiv**: 完全支持,包含摘要
- ✅ **Nature 系列**: 通过官方 API 支持,包含摘要
- ⚠️ **Science**: 实验性支持,易受拦截,稳定性较差
- ⚠️ **Optica**: 实验性支持,网页抓取可用
- ⚠️ **APS (Physical Review)**: 实验性支持,易受拦截,稳定性较差
- **注意**: 实验性支持项目需要将fetcher/rss_fetcher.py中的对应代码取消注释以启用，具体使用方法参阅[crawl4ai](https://github.com/unclecode/crawl4ai)
```python
# 766-770
################## Not Finished yet
# # # Extract the abstract by a crawler implemented with crawl4ai
# if source != 'arxiv':
#     new_papers = fill_abstracts(source, new_papers)
################## Not Finished yet
```


修改 `main.py` 中的 `--sources` 参数:

```bash
--sources "arxiv:physics+quant-ph+cond-mat+nlin,nature:nature+nphoton+ncomms"
```

**格式**: `来源:分类1+分类2+分类3,来源2:分类1+分类2`

#### 可用的 arXiv 分类:

| 分类代码 | 说明 |
|---------|------|
| `physics` | 物理学 |
| `quant-ph` | 量子物理 |
| `cond-mat` | 凝聚态物理 |
| `nlin` | 非线性科学 |
| `cs.AI` | 人工智能 |
| `cs.CV` | 计算机视觉 |
| `cs.CL` | 计算与语言 |
| `cs.LG` | 机器学习 |

完整列表见: [arXiv 分类目录](https://arxiv.org/category_taxonomy)

#### 可用的 Nature 期刊:

| 期刊代码 | 期刊名称 |
|---------|---------|
| `nature` | Nature |
| `nphoton` | Nature Photonics |
| `nphys` | Nature Physics |
| `ncomms` | Nature Communications |
| `natrevphys` | Nature Reviews Physics |
| `lsa` | Light: Science & Applications |
| `natmachintell` | Nature Machine Intelligence |

完整列表见: [Nature Portfolio](https://www.nature.com/siteindex)

#### 可用的 Science 期刊 (实验性，不稳定):

| 期刊代码 | 期刊名称 |
|---------|----------|
| `science` | Science |
| `sciadv` | Science Advances |

#### 可用的 Optica 期刊 (实验性):

| 期刊代码 | 期刊名称 |
|---------|----------|
| `optica` | Optica |

#### 可用的 APS 期刊 (实验性，不稳定):

| 期刊代码 | 期刊名称 |
|---------|----------|
| `prl` | Physical Review Letters |
| `prx` | Physical Review X |

### 🤖 LLM 模型配置

修改 `--model_name` 参数:

```bash
--model_name "qwen3-30b-a3b-instruct-2507"
# 或
--model_name "deepseek-chat"
# 或
--model_name "gpt-4o"
# 或任何 OpenAI 兼容的模型
```

**注意**: DeepSeek 模型会使用 `langchain_deepseek` 库,其他模型使用 `langchain_openai` 库。

### 🔢 嵌入向量模型配置

修改 `--embedding_model` 参数:

```bash
--embedding_model "qwen3-embedding-8b"
# 或
--embedding_model "text-embedding-3-small"
# 或任何 OpenAI 兼容的嵌入模型
```

### 🌍 输出语言配置

修改 `--language` 参数:

```bash
--language "Chinese"
# 或
--language "English"
```

你也可以在 Web 界面的设置页面中切换语言,系统会自动加载对应语言的数据文件。

### ⚙️ 并行处理配置

修改 `--max_workers` 参数来控制 AI 处理的并行度:

```bash
--max_workers 4  # 使用 4 个并行线程
```

**注意**: 
- 增加并行线程数可以显著加快处理速度
- 但也会增加 API 调用频率和成本
- 建议根据 API 限率和预算谨慎设置

### 🎯 智能筛选配置

项目会自动根据 Zotero 相似度评分筛选论文:

- **评分阈值**: 3.6 分(满分 10 分)
- **处理策略**: 仅对评分 ≥ 3.6 的论文生成 AI 摘要
- **成本优化**: 避免为不相关论文消耗 API 额度

如需修改阈值,请编辑 `ai/enhance.py` 中的条件:

```python
if item and item["score"]["max"] < 3.6:  # 修改此数值
    logger.debug(f"[{source}] Skipping irrelevant item: {item['id']}")
    item['AI'] = 'Skip'
    return item
```

### ⚡ 运行方式说明

项目默认使用 `schedule` 库实现定时任务,需要程序持续运行。

**修改定时任务时间**: 编辑 `main.py` 文件底部:

```python
# 修改每日任务时间(默认 08:00)
schedule.every().day.at("08:00").do(main, args=args).tag('daily-tasks')

# 修改每周任务时间(默认周日 10:00)
schedule.every().sunday.at("10:00").do(main_week_check, args=args).tag('weekly-tasks')
```

---

## 📊 数据格式说明

论文数据以 JSONL 格式存储,每行一个 JSON 对象,结构如下:

```json
{
  "journal": "Nature Photonics",
  "id": "10.1038/s41566-024-01234-5",
  "pdf": "https://www.nature.com/articles/s41566-024-01234-5.pdf",
  "abs": "https://doi.org/10.1038/s41566-024-01234-5",
  "title": "论文标题",
  "summary": "论文摘要文本...",
  "authors": ["作者1", "作者2"],
  "published": "2025-11-03",
  "category": "量子光学",
  "score": {
    "文献夹1": 8.5,
    "文献夹2": 6.2,
    "max": 8.5
  },
  "collection": ["文献夹1"],
  "AI": {
    "tldr": "一句话总结",
    "motivation": "研究动机...",
    "method": "研究方法...",
    "result": "研究结果...",
    "conclusion": "结论..."
  }
}
```

### 字段说明:

- **journal**: 期刊名称
- **id**: 论文唯一标识符 (arXiv ID 或 DOI)
- **pdf**: PDF 下载链接
- **abs**: 摘要页面链接
- **title**: 论文标题
- **summary**: 论文原始摘要
- **authors**: 作者列表
- **published**: 发表日期
- **category**: 分类/主题
- **score**: 与各 Zotero 文献夹的相关性评分
- **collection**: 推荐的 Zotero 文献夹列表
- **AI**: AI 生成的结构化摘要

---

## 📋 待办事项 (TODO)

- [ ] **改进稳定性**: 解决 Science 和 APS 被拦截的问题
- [ ] **添加更多 RSS 源**: PNAS、Physical Review Letters、JACS 等
- [ ] **添加数据分析页面**: 论文趋势分析和可视化
- [ ] **Web UI 改进**: 添加论文导出、标签管理等功能

---

## 🐛 已知问题

- **稳定性**: Science 和 APS 网站会被拦截,抓取成功率不稳定
- **RSS 源限制**: 大部分学术期刊的 RSS 不包含摘要,需要额外抓取

---

## 📝 开源许可

本项目采用 **GNU Affero General Public License v3.0 (AGPL-3.0)** 许可证发布。详见 [LICENSE](LICENSE) 文件。

### 为什么选择 AGPL-3.0?

AGPL-3.0 确保:
- ✅ 自由使用、修改和分发的权利
- ✅ 要求分享修改内容 (即使通过网络服务提供)
- ✅ 防止闭源分支
- ✅ 与上游依赖项兼容

---

## 🙏 致谢

本项目构建并集成了以下优秀开源项目的代码:

### 主要来源

1. **[daily-arXiv-ai-enhanced](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced)** by [@dw-dengwei](https://github.com/dw-dengwei)
   - 启发了 RSS 抓取和 AI 摘要生成工作流
   - 提供了 Web 界面设计基础
   - LLM 集成的参考实现

2. **[zotero-arxiv-daily](https://github.com/TideDra/zotero-arxiv-daily)** by [@TideDra](https://github.com/TideDra)
   - 采用 AGPL-3.0 许可证
   - 基于 Zotero 的论文排序核心算法
   - 嵌入向量相似度计算和时间衰减加权
   - 推荐系统的基础架构

### 核心依赖

- [pyzotero](https://github.com/urschrei/pyzotero) - Zotero API 客户端
- [feedparser](https://github.com/kurtmckee/feedparser) - RSS/Atom 订阅解析器
- [langchain](https://github.com/langchain-ai/langchain) - LLM 框架
- [langchain-openai](https://github.com/langchain-ai/langchain) - OpenAI LLM 集成
- [langchain-deepseek](https://github.com/langchain-ai/langchain-deepseek) - DeepSeek LLM 集成
- [OpenAI Python SDK](https://github.com/openai/openai-python) - API 客户端
- [sentence-transformers](https://github.com/UKPLab/sentence-transformers) - 嵌入向量模型
- [PyTorch](https://pytorch.org/) - 机器学习框架
- [Flask](https://github.com/pallets/flask) - Web 框架(用于 API 服务器)
- [Flask-CORS](https://github.com/corydolphin/flask-cors) - Flask 跨域资源共享支持
- [requests](https://github.com/psf/requests) - HTTP 库
- [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/) - HTML 解析库
- [numpy](https://github.com/numpy/numpy) - 数值计算库
- [crawl4ai](https://github.com/unclecode/crawl4ai) - 爬虫工具(实验性)
- [schedule](https://github.com/dbader/schedule) - 定时任务调度库
- [tqdm](https://github.com/tqdm/tqdm) - 进度条库

### AI 网关

- [new-api](https://github.com/QuantumNous/new-api) - 开源 AI 网关

### AI 编码助手

- [Qoder](https://qoder.com/) - 本项目借助 Qoder 和 Qoder CLI 的辅助完成
---

## ⚠️ 免责声明

### 一般性免责声明

本软件按"原样"提供,不提供任何明示或暗示的保证。本项目的开发者和贡献者不对软件的准确性、完整性、可靠性或适用性作任何陈述或保证。

### [详情](DISCLAIMER.md)

---

**最后更新**: 2025-11-19

---

**如果本项目对你有帮助,欢迎 Star! ⭐**
