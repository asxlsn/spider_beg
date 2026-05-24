# 闲鱼商品监控 - 自动筛选推送系统

## 项目概述

基于 GitHub Actions 的闲鱼商品监控系统，自动爬取首页推荐商品，通过关键词 + AI 双重筛选，将服务类商品推送到钉钉。

## 核心功能

### 1. 定时爬取
- 北京时间 9:00 / 17:00 / 1:00（每8小时一次）
- 每次爬取3页，约60条商品
- 每页间隔随机3-7秒
- 定时触发前随机延迟1-60分钟

### 2. 智能筛选（双通道，满足任一即推送）

**通道一：关键词匹配（即时命中）**

标题包含以下关键词的商品直接推送：

```
预约、代抢、代拍、代购、代跑、代办、代订、代排、抢购、秒杀、
脚本、自动化、外挂、辅助、定制、开发、接单、门票、车票、挂号、
取号、排队、黄牛、签证、代签、代约、代订票、代注册、代做、代写、
爬虫、逆向、破解、接口、数据采集、批量
```

**通道二：DeepSeek AI 判断（兜底筛选）**

关键词未命中的商品整批发给 DeepSeek，由 AI 判断是否属于：
- 预约服务（门票、挂号、车辆预约等）
- 代跑/代办服务
- 抢购/秒杀服务
- 脚本/自动化定制
- 技术服务（接口对接、逆向等）

### 3. 去重机制
- 已推送的商品ID记录在 `xy_seen_ids.json`
- 自动清理超过3天的记录，防止文件膨胀
- 只推送新商品，不重复通知

### 4. 钉钉推送内容
- 商品标题
- 价格、城市、卖家
- 热度（想要人数）
- 商品链接（可直接点击查看）
- 商品图片

## GitHub Secrets 配置

| Secret 名称 | 说明 | 获取方式 |
|---|---|---|
| `XY_COOKIE` | 闲鱼登录 Cookie 字符串 | 浏览器 F12 → Network → 复制请求的 Cookie |
| `DINGTALK_WEBHOOK` | 钉钉机器人 Webhook 地址 | 钉钉群 → 设置 → 智能群助手 → 添加机器人 |
| `DINGTALK_SECRET` | 钉钉机器人加签密钥 | 创建机器人时的 SEC 开头字符串 |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | https://platform.deepseek.com |

## Cookie 更新方法

Cookie 过期后需要手动更新：

1. 打开 https://www.goofish.com 并登录
2. F12 打开开发者工具 → Network
3. 刷新页面，找到 `h5api.m.goofish.com` 的请求
4. 复制请求头中的 Cookie 值（完整的一行字符串）
5. 去 GitHub 仓库 Settings → Secrets → Actions → 编辑 `XY_COOKIE`，粘贴新值

## 手动触发

1. 打开 https://github.com/asxlsn/spider_beg/actions
2. 点击左侧 "Run xy_feed"
3. 点击右侧 "Run workflow"
4. 手动触发不会有延迟，立即执行

## 文件结构

```
spider_beg/
├── xy_feed.py                      # 主脚本
├── xy_seen_ids.json                # 已推送商品记录（自动维护）
└── .github/workflows/
    └── run_xy_feed.yml             # GitHub Actions 定时任务配置
```

## 费用

- GitHub Actions：公开仓库免费，无限制
- DeepSeek API：约 1元/百万输入token，每次调用约几分钱
- 钉钉机器人：免费
