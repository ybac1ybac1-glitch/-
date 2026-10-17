# P3.1 策略 A V4 首版网页

## 页面与后台任务
打开 `/strategy/a/v4` 只读取最近一次成功快照，不会在 GET 或查看 K 线时扫描全市场。点击“开始复盘”后，浏览器 POST `/strategy/a/v4/start`，任务在后台运行；随后每秒轮询 `/strategy/a/v4/status`，完成后再读取结果。重复启动返回 HTTP 409，`max_stocks` 必须是正整数，否则 HTTP 400。

结果接口为 `GET /strategy/a/v4/results?page=1&page_size=50&rule_id=A03&state=CANDIDATE&code=600`。响应包含 `total_matches`（命中股票数）、`total_signals`（信号行数）、`returned_matches`、`page`、`page_size` 和稳定排序的 `items`。筛选、翻页均在结果 SQLite 中执行，不重新扫描。

## 结果安全
扫描写入独立的 `backend/strategy_a_results.sqlite3`，原始 `market_cache.sqlite3` 不写入。新快照只有在所有信号落盘、持久化数量与验证统计一致且未截断时才切换为有效；失败或中断会回滚并保留旧快照。部分样本会在页面标注“部分样本，不代表全市场”。

## Windows CMD
在项目根目录：
```cmd
set PYTHONPATH=backend
python backend\app.py
```
浏览器访问 `http://127.0.0.1:8000/strategy/a/v4`。若从 `backend` 文件夹启动：
```cmd
cd backend
set PYTHONPATH=.
python app.py
```
两种方式都只监听本机回环地址。真实 K 线详情通过现有 `/stock/<ts_code>` 从本地行情库读取，不调用 Tushare。

## 状态含义
页面区分空状态、RUNNING 进度、COMPLETED 历史快照和 FAILED 错误；候选、确认、失效状态按原策略事件输出，候选不等同于可成交买点。
