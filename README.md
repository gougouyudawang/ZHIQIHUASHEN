# 智契化身

本仓库包含用户端、信任提供方（TP）审核端、智能体提供方（AP）管理端，以及 Octopus / OpenClaw 智能体相关代码。下面的步骤以 **Windows 本机演示** 为准；三个网页由 Python 服务直接提供，不需要单独启动前端开发服务器。

## 1. 下载后，一键打开网页

在 Windows 电脑上下载 GitHub 仓库的 ZIP 并解压，进入包含 `app/` 的项目目录，**双击 `start_all.bat`**。也可以使用 `git clone https://github.com/gougouyudawang/ZHIQIHUASHEN.git` 下载，再进入克隆目录双击同一个 BAT。首次运行会自动创建 `.venv312`、安装三个网页服务的 Python 依赖、启动 TP/AP/用户端，并在默认浏览器打开用户网址；之后重复双击会复用已运行的服务。需要联网下载依赖，首次启动可能较慢。

脚本会寻找 Python 3.11 或 3.12；若没有 Python 但电脑有 Windows 包管理器 `winget`，会尝试自动安装 Python 3.12。**没有 Python 且没有 winget，或电脑无法联网时，无法保证只双击 BAT 就完成首次安装**：需先手动安装 Python 3.12，并连网运行一次。仓库不包含虚拟环境。只有启动 OpenClaw 执行分支时才需要额外准备 Node.js、npm 和 Git；运行 Octopus 实例会在首次启动时为实例安装其 Python 依赖。

只想启动一个网页，可以分别双击 `start_user_8110.bat`、`start_tp_8111.bat` 或 `start_ap_8112.bat`，它们使用同一套自动环境准备流程。服务会在后台运行；双击 `stop_all.bat` 可停止由启动脚本创建的三端服务。运行日志位于 `local_store/bootstrap_logs/`。脚本不会强制结束占用端口的其他程序；如果端口冲突，会给出错误信息。

## 2. 本机网址

| 页面 | 本机地址 | 演示账号 |
| --- | --- | --- |
| 用户端 | <http://127.0.0.1:8110/user> | `user` / `pa@2026` |
| 用户端简版工作台 | <http://127.0.0.1:8110/user/static/experience/index.html> | 同上 |
| TP 申领与删除审核端 | <http://127.0.0.1:8111/tp> | `tpadmin` / `pa@2026` |
| AP 管理端 | <http://127.0.0.1:8112/ap> | `apadmin` / `pa@2026` |

未登录时会跳转到各自的 `/login` 页面。用户端的“连接与设置”应指向 `http://127.0.0.1:8111` 和 `http://127.0.0.1:8112`。`/user` 使用在线 CDN 加载 Vue 和 Element Plus，浏览器需要能访问这些资源；简版工作台的页面脚本和样式位于仓库内。

如需手动启动，先在项目根目录创建环境并安装依赖：

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install -r requirements-local.txt
```

然后在三个独立终端分别设置 `$env:USE_FIXED_KEYS='1'`，并运行下列命令（每个终端一条）：

```powershell
.\.venv312\Scripts\python.exe -m uvicorn app.tp_app:app --host 127.0.0.1 --port 8111
.\.venv312\Scripts\python.exe -m uvicorn app.ap_app:app --host 127.0.0.1 --port 8112
.\.venv312\Scripts\python.exe -m uvicorn app.experience_app:app --host 127.0.0.1 --port 8110
```

三个启动脚本已经设置了 `USE_FIXED_KEYS=1`，使服务间使用相同的演示密钥。

## 3. 完成申领流程前，还需配置什么

**登录和浏览页面**不需要先申请身份，也不需要 ANP 网关；但**真实提交身份申领**需要可连接的 MySQL，以及表中与申请人对应的照片记录。TP 当前读取环境变量 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DB`、`MYSQL_TABLE`；代码默认分别是 `127.0.0.1`、`3306`、`root`、`1234`、`avatar`、`bi`。请在启动 TP 的 PowerShell 窗口中先设置你自己的值，例如：

```powershell
$env:MYSQL_HOST='127.0.0.1'
$env:MYSQL_PORT='3306'
$env:MYSQL_USER='你的数据库用户'
$env:MYSQL_PASSWORD='你的数据库密码'
$env:MYSQL_DB='avatar'
$env:MYSQL_TABLE='bi'
.\start_tp_8111.bat
```

TP 会按申请中的身份编号查询 `bi.user_id`，并将 `bi.pic_string` 与本次上传照片的数据比较。库中没有该用户、照片数据不一致或数据库不可用时，页面虽能打开，身份核验仍无法通过。演示账号只用于**登录网页**，不代表数据库已准备好，也不保证申领自动通过。通过用户端提交后，在 TP 页面审核申请，再返回用户端查看审批结果。

创建并运行智能体还需要可用的模型服务。本仓库按项目维护者要求包含 `agent_provider/octopus/.env` 与 `agent_provider/openclaw/.env` 中的现有模型配置；如这些密钥失效或不适用于你的环境，可在对应文件中填写自己的 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 和模型名称。Octopus 的字段可参考 `agent_provider/octopus/.env_template`，OpenClaw 可参考 `agent_provider/openclaw/.env.example`。也可以在实例生成后，通过页面的模型配置入口为该实例单独设置。仅启动三个网页不等于模型对话已经可用。

## 4. 常见问题与运行边界

- `.venv312\Scripts\python.exe` 不存在：`start_all.bat` 会自动创建；如果失败，检查 Python/winget 与网络连接。
- 端口 8110、8111、8112 被占用：启动脚本不会结束其他进程，请先关闭冲突程序。
- 申领时报 `db_check_failed` 或照片核验失败：检查 TP 终端的 MySQL 环境变量、数据库连接及 `bi` 表中的 `user_id`/`pic_string`。
- 智能体聊天失败：查看实例运行日志与模型地址、密钥、模型名称；网页显示 Ready 只代表实例服务已启动。
- ANP：系统内的 Octopus 组内通信不要求先手动启动 `anp-proxy`。仓库保留代理源码供需要外部 ANP 网关的场景使用，不是打开网页或进行本地申领的前置步骤。

这些演示脚本只监听本机地址，使用演示账号和固定测试密钥。不要直接把它们作为公网部署配置。`local_store/`、`data/`、身份私钥和日志属于本机数据，不在 GitHub 下载包中；上述两个模型 `.env` 则包含在仓库中。

## 本次运行核验

2026-10-17 除已有环境外，还从空虚拟环境实际运行了 `scripts/start_local.ps1`：脚本创建虚拟环境、在线安装依赖，并启动 TP、AP 和用户服务；三个新服务逐一通过了演示账号登录、受保护主页加载和静态资源请求。身份申领、MySQL 照片比对、外部模型对话与首次安装智能体依赖需要外部服务或数据，本次未作端到端验证。
