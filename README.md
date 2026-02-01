# Jacky 情报推送机器人

## 功能
每日自动抓取政府采购招标信息，筛选关键词后推送到飞书。

## 监控目标
- 广东省政府采购网
- 深圳公共资源交易中心
- （可扩展更多源）

## 关键词
园区运营、资产管理、产业服务、城投、产业园招商、招商引资

## 推送时间
每天上午9:00（北京时间）

## 配置
在GitHub Secrets中设置：`FEISHU_WEBHOOK`

## 手动触发
进入Actions → Daily Intel Scraper → Run workflow