# 智契化身

本仓库包含用户端、信任提供方（TP）审核端、智能体提供方（AP）管理端，以及 Octopus / OpenClaw 智能体相关代码。下面的步骤以 **Windows 本机演示** 为准；三个网页由 Python 服务直接提供，不需要单独启动前端开发服务器。

## 1. 下载并安装基础依赖

安装 Python 3.12。然后在 PowerShell 中运行：

```powershell
git clone https://github.com/gougouyudawang/ZHIQIHUASHEN.git
cd ZHIQIHUASHEN
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install -r requirements-local.txt
```

也可以从 GitHub 下载 ZIP 并解压，之后在解压后的**项目根目录**运行后三条命令。根目录是包含 `app/` 和三个 `start_*.bat` 的目录。安装依赖需要联网；仓库不包含虚拟环境。只有启动 OpenClaw 执行分支时才需要额外准备 Node.js、npm 和 Git；运行 Octopus 实例会在首次启动时为实例安装其 Python 依赖。

## 2. 启动本地网页

分别打开三个 PowerShell 窗口，都先进入项目根目录，再各运行一条命令：

```powershell
.\start_tp_8111.bat
```

```powershell
.\start_ap_8112.bat
```

```powershell
.\start_user_8110.bat
```

启动顺序建议 TP → AP → 用户端。脚本使用 `.venv312\Scripts\python.exe`，并将三个服务只绑定到 `127.0.0.1`。保持三个终端窗口开启；关闭窗口即停止对应服务。**脚本启动前会强制结束占用其目标端口的进程**，如果端口上有其他程序，请先确认再运行。

| 页面 | 本机地址 | 演示账号 |
| --- | --- | --- |
| 用户端 | <http://127.0.0.1:8110/user> | `user` / `pa@2026` |
| 用户端简版工作台 | <http://127.0.0.1:8110/user/static/experience/index.html> | 同上 |
| TP 申领与删除审核端 | <http://127.0.0.1:8111/tp> | `tpadmin` / `pa@2026` |
| AP 管理端 | <http://127.0.0.1:8112/ap> | `apadmin` / `pa@2026` |

未登录时会跳转到各自的 `/login` 页面。用户端的“连接与设置”应指向 `http://127.0.0.1:8111` 和 `http://127.0.0.1:8112`。`/user` 使用在线 CDN 加载 Vue 和 Element Plus，浏览器需要能访问这些资源；简版工作台的页面脚本和样式位于仓库内。

如果不使用 `.bat`，可在已进入项目根目录且已设置 `USE_FIXED_KEYS=1` 的三个终端中分别运行：

```powershell
.\.venv312\Scripts\python.exe -m uvicorn app.tp_app:app --host 127.0.0.1 --port 8111
.\.venv312\Scripts\python.exe -m uvicorn app.ap_app:app --host 127.0.0.1 --port 8112
.\.venv312\Scripts\python.exe -m uvicorn app.experience_app:app --host 127.0.0.1 --port 8110
```

上面每条命令必须在**不同终端**运行，不能在一个终端里依次等待执行。三个启动脚本已经设置了 `USE_FIXED_KEYS=1`，手动启动时请在每个终端先执行 `$env:USE_FIXED_KEYS='1'`，使服务间使用相同的演示密钥。

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

- `.venv312\Scripts\python.exe` 不存在：先完成第 1 步创建虚拟环境，或检查 Python 3.12 是否安装。
- 端口 8110、8111、8112 被占用：启动脚本会结束占用对应端口的进程；如不希望这样，请先关闭冲突程序并使用手动启动命令。
- 申领时报 `db_check_failed` 或照片核验失败：检查 TP 终端的 MySQL 环境变量、数据库连接及 `bi` 表中的 `user_id`/`pic_string`。
- 智能体聊天失败：查看实例运行日志与模型地址、密钥、模型名称；网页显示 Ready 只代表实例服务已启动。
- ANP：系统内的 Octopus 组内通信不要求先手动启动 `anp-proxy`。仓库保留代理源码供需要外部 ANP 网关的场景使用，不是打开网页或进行本地申领的前置步骤。

这些演示脚本只监听本机地址，使用演示账号和固定测试密钥。不要直接把它们作为公网部署配置。`local_store/`、`data/`、身份私钥和日志属于本机数据，不在 GitHub 下载包中；上述两个模型 `.env` 则包含在仓库中。

## 本次运行核验

2026-10-17 使用项目的 `.venv312` 在独立本机端口实际启动了 TP、AP 和用户服务，逐一通过了演示账号登录、受保护主页加载和静态资源请求；同时检查了 TP 公钥及 AP 能力接口。身份申领、MySQL 照片比对、外部模型对话与首次安装智能体依赖需要外部服务或数据，本次未作端到端验证。
