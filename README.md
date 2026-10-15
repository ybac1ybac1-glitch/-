# 威科夫 A 股盘后研究系统 V3

基于 Flask、Tushare 和 pandas 的 A 股盘后复盘原型，包含威科夫结构评分、市场环境、K 线详情、公告与新闻情绪模块。

## 启动

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
export TUSHARE_TOKEN="你的 Tushare Token"  # Windows PowerShell: $env:TUSHARE_TOKEN="..."
python backend/app.py
```

浏览器打开 `http://127.0.0.1:8000`。Tushare 接口不可用时，系统使用空数据兜底；公告/新闻数据源也可能因权限或接口限制为空。

## 目录

- `backend/app.py`：Flask 路由
- `backend/data.py`：股票池和 daily/weekly/monthly 数据
- `backend/wyckoff.py`：Spring、SOS、LPS、吸筹结构分析
- `backend/market.py`：进攻/震荡/防守市场环境
- `backend/announcement.py`、`backend/news.py`：情绪和关键词分析
- `backend/templates/`：首页和详情页
