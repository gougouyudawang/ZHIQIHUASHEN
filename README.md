# 信锚 Agent-Anchor

## 下载与本地配置

可以直接下载 GitHub 仓库的 ZIP，或运行 `git clone https://github.com/gougouyudawang/ZHIQIHUASHEN.git`。仓库中的 `anp-proxy/` 已包含项目使用的代理源码，无需另行拉取子模块。

本机 API Key、身份私钥、申请记录、运行日志和虚拟环境不会上传。配置 OpenClaw 时，可复制 `agent_provider/openclaw/.env.example` 为同目录下的 `.env`，再填入自己的密钥；Octopus 的配置参考 `agent_provider/octopus/.env_template`。Windows 下可使用根目录的 `start_user_8110.bat`、`start_tp_8111.bat`、`start_ap_8112.bat` 分别启动三个服务。

本项目是一个完整的个人智能体系统实现，集成了去中心化身份 (DID)、可验证凭证 (PHC/PA) 以及安全的智能体通信协议 (ANP)。

## 项目概览

系统由以下几个核心组件构成：
- **Trust Provider (TP)**: 信任提供方。负责验证真人身份并签发 Personhood Credentials (PHC)。
- **Agent Provider (AP)**: 智能体提供方。负责签发 Personal Agent (PA) 凭证，并管理智能体的代码模板。
- **User Service**: 用户服务。管理用户身份，代理用户申请凭证，并负责在本地构建和部署智能体。
- **Gateway**: 网关服务。提供 WebSocket/HTTP 接口，支持智能体之间的安全通信 (ANP)。

## 目录结构

- `agent_provider/`: AP 服务的源代码以及 Octopus 智能体模板代码。
- `trust_provider/`: TP 服务的源代码（身份验证逻辑）。
- `user/`: User 服务的核心逻辑（凭证管理、加密运算）。
- `app/`: FastAPI 应用入口和 Web 前端界面。
- `gateway/`: ANP 网关的实现。
- `local_store/`: 本地存储目录，用于存放生成的智能体、密钥和数据库文件。

## 运行指南

### 前置要求

- Python 3.10 或更高版本
- `uv` 包管理器 (推荐) 或 pip



### 启动服务

**1. 启动网关 (Gateway)**
```bash
cd anp-proxy
uv run anp-proxy --mode gateway --gateway-port 8080 --wss-port 8765
```
**2. 启动用户端**
```bash
python -m uvicorn app.user_app:app --host your_ip --port 8000 --reload
```

**3. 启动信任提供方 (TP)**
```bash
python -m uvicorn app.tp_app:app --host your_ip --port 8001 --reload
```

**4. 启动智能体提供方 (AP)**
```bash
python -m uvicorn app.ap_app:app --host your_ip --port 8002 --reload
```

## 用户使用指南：创建您的第一个智能体
1.  **配置数据库**: 在 `trust_provider/issue_phc.py` 中配置数据库连接信息。在配置的mysql数据库中上传user信息。（pic_string可以通过先上传一张照片，通过F12开发者工具抓包获取）
2.  **打开用户控制台** (`http://localhost:8000/user`)。
3.  **申请 PHC**: 上传一张照片（和配置好的mysql数据库中的user信息匹配），点击 "请求 PHC"。这一步模拟了身份验证过程。
4.  **加载配置**: 点击 "加载配置"，从 AP 获取可选的智能体模块列表。
5.  **选择模块**: 勾选您希望智能体具备的能力（例如 "文本处理"、"联网搜索"）。
6.  **提交并创建**: 提交您的选择。系统会自动下载代码、裁剪配置并生成启动脚本。
7.  **启动智能体**:
    - 进入目录 `d:\program\personal-agent\local_store\agents\<您的phc_id>\`。
    - 双击运行 `launch_octopus_personal.bat`。
    - 您的个人智能体将在 9527 端口启动。请访问 `http://localhost:9527` 与它对话。
    （如果要进行多实例测试，启动其他智能体实例时，需要手动在 `launch_octopus_personal.bat` 中修改端口号。）
