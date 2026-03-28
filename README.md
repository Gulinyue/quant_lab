# Quant Lab v0.1

面向 Windows 本地环境的 A 股低频量化研究框架。当前版本保留原有 6 层分层架构与脚本链路，并新增了一个单页本地控制面板。

## 默认启动方式

以后默认从控制面板启动：

```powershell
D:\anaconda\envs\alpha_lab\python.exe -m streamlit run app.py
```

## Windows PowerShell 安装步骤

1. 确认固定解释器存在：

```powershell
D:\anaconda\envs\alpha_lab\python.exe -c "import sys; print(sys.executable); print(sys.version)"
```

2. 安装依赖：

```powershell
D:\anaconda\envs\alpha_lab\python.exe -m pip install -r requirements.txt
```

3. 配置环境变量：

```powershell
Copy-Item .env.example .env
notepad .env
```

## 固定解释器

本仓库所有默认命令统一使用：

```powershell
D:\anaconda\envs\alpha_lab\python.exe
```

不要使用裸 `python`、`py`、其他 conda 环境或 repo-local venv 作为默认示例。

## .env 配置方式

`.env` 示例：

```env
TUSHARE_TOKEN=your_tushare_token_here
```

若未配置 `TUSHARE_TOKEN`，控制面板与 `scripts/update_data.py` 会回退到样例合成数据，便于本地 smoke test。

## 控制面板功能

`app.py` 提供单页控制面板，可完成：

- 更新数据
- 构建市场面板
- 构建因子
- 运行策略
- 运行回测
- 生成报告
- 全流程运行

页面还会显示：

- 当前 Python executable 和 Python version
- 日志区域
- 运行状态
- 关键产物存在性
- `reports/figures/nav.png` 图片预览

## 高级用法：保留旧脚本方式

旧脚本式运行仍然兼容：

```powershell
D:\anaconda\envs\alpha_lab\python.exe scripts\update_data.py
D:\anaconda\envs\alpha_lab\python.exe scripts\build_market_panel.py
D:\anaconda\envs\alpha_lab\python.exe scripts\build_factors.py
D:\anaconda\envs\alpha_lab\python.exe scripts\run_strategy.py
D:\anaconda\envs\alpha_lab\python.exe scripts\run_backtest.py
D:\anaconda\envs\alpha_lab\python.exe scripts\run_analysis.py
D:\anaconda\envs\alpha_lab\python.exe scripts\build_report.py
```

## 全流程运行顺序

控制面板中的 `Run All` 顺序为：

1. 更新数据
2. 构建市场面板
3. 构建因子
4. 运行策略
5. 运行回测
6. 生成分析结果
7. 生成报告

## 常见报错排查

- `ModuleNotFoundError`：执行 `D:\anaconda\envs\alpha_lab\python.exe -m pip install -r requirements.txt`
- `No module named streamlit`：说明控制面板依赖未安装
- `TUSHARE_TOKEN is not configured`：检查 `.env` 是否存在且字段名正确
- `ImportError: Unable to find a usable engine`：通常是 `pyarrow` 未安装
- TuShare 拉数失败：先确认 token 权限，再确认是否已回退到样例数据

## 如何确认当前实际使用的 Python 解释器

```powershell
D:\anaconda\envs\alpha_lab\python.exe -c "import sys; print(sys.executable)"
```

如果输出不是 `D:\anaconda\envs\alpha_lab\python.exe`，说明当前没有按项目要求运行。
