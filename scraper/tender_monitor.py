#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政府采购招标信息监控器
监控目标：中国政府采购网、广东省政府采购网
"""

import os
import json
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 飞书Webhook
FEISHU_WEBHOOK = os.environ.get('FEISHU_WEBHOOK', '')

# 监控配置
KEYWORDS = ['园区运营', '资产管理', '产业服务', '城投', '产业园招商', '招商引资']
REGIONS = ['深圳', '广州', '东莞', '佛山', '珠海']

class TenderMonitor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.results = []
    
    def fetch_ccgp_guangdong(self):
        """抓取广东省政府采购网"""
        url = 'http://www.ccgp-guangdong.gov.cn/queryMoreInfoList.do'
        params = {
            'channelCode': '0005',
            'page': '1',
            'pageSize': '20'
        }
        
        try:
            logger.info("Fetching CCGP Guangdong...")
            response = self.session.get(url, params=params, timeout=30)
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('li', class_='li')[:10]
            
            for item in items:
                try:
                    title_elem = item.find('a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '')
                    
                    # 检查关键词匹配
                    matched_keywords = [k for k in KEYWORDS if k in title]
                    if not matched_keywords:
                        continue
                    
                    # 检查地区匹配
                    matched_region = None
                    for region in REGIONS:
                        if region in title:
                            matched_region = region
                            break
                    
                    date_elem = item.find('span', class_='date')
                    pub_date = date_elem.get_text(strip=True) if date_elem else ''
                    
                    self.results.append({
                        'source': '广东省政府采购网',
                        'title': title,
                        'link': link if link.startswith('http') else f'http://www.ccgp-guangdong.gov.cn{link}',
                        'date': pub_date,
                        'keywords': matched_keywords,
                        'region': matched_region,
                        'priority': '高' if matched_region == '深圳' else '中'
                    })
                    
                except Exception as e:
                    logger.error(f"Parse item error: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Fetch CCGP Guangdong error: {e}")
    
    def fetch_szggzy(self):
        """抓取深圳公共资源交易中心"""
        url = 'https://www.szggzy.com/globalSearch/search.html'
        
        try:
            logger.info("Fetching Shenzhen GGZY...")
            # 简化版，实际可能需要更复杂的处理
            response = self.session.get(url, timeout=30)
            # 这里简化处理，实际需要根据页面结构调整
            logger.info("Shenzhen GGZY fetch completed")
        except Exception as e:
            logger.error(f"Fetch Shenzhen GGZY error: {e}")
    
    def analyze_priority(self):
        """分析优先级"""
        high_priority = []
        medium_priority = []
        
        for item in self.results:
            # 高优先级：深圳+含多个关键词
            if item['region'] == '深圳' and len(item['keywords']) >= 2:
                item['priority'] = '高'
                high_priority.append(item)
            # 中优先级：含关键词
            elif item['keywords']:
                item['priority'] = '中'
                medium_priority.append(item)
        
        return high_priority, medium_priority
    
    def format_feishu_message(self, high_priority, medium_priority):
        """格式化飞书消息"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        message = f"🎯 **每日情报推送（{today}）**\n\n"
        
        if high_priority:
            message += "**🔴 高优先级（建议立即联系）**\n"
            for i, item in enumerate(high_priority[:5], 1):
                message += f"\n{i}. **{item['title']}**\n"
                message += f"   📍 {item['region']} | 💰 需点击查看 | 📅 {item['date']}\n"
                message += f"   🔗 [查看详情]({item['link']})\n"
                message += f"   🏷️ 关键词：{', '.join(item['keywords'])}\n"
        
        if medium_priority:
            message += f"\n**🟡 中优先级（值得关注）**\n"
            for i, item in enumerate(medium_priority[:5], 1):
                message += f"\n{i}. {item['title']}\n"
                message += f"   📍 {item['region'] or '未知'} | 📅 {item['date']}\n"
                message += f"   🔗 [查看详情]({item['link']})\n"
        
        if not high_priority and not medium_priority:
            message += "\n📭 今日暂无匹配情报，建议关注以下渠道：\n"
            message += "- 直接联系目标城投公司资产管理部\n"
            message += "- 参加产业园区行业沙龙\n"
        
        message += "\n---\n"
        message += "💡 **建议行动**：\n"
        message += "1. 高优先级项目建议在3个工作日内联系\n"
        message += "2. 话术参考：「看到贵司招标，我有15年园区操盘经验，曾帮3个园区实现从0到1...」\n"
        message += "3. 需要定制化话术请@AoKen\n"
        
        return message
    
    def send_to_feishu(self, message):
        """发送到飞书"""
        if not FEISHU_WEBHOOK:
            logger.error("FEISHU_WEBHOOK not set")
            return
        
        payload = {
            "msg_type": "markdown",
            "content": {
                "markdown": message
            }
        }
        
        try:
            response = requests.post(
                FEISHU_WEBHOOK,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            logger.info("Message sent to Feishu successfully")
        except Exception as e:
            logger.error(f"Send to Feishu error: {e}")
    
    def run(self):
        """主运行函数"""
        logger.info("=" * 50)
        logger.info("Starting daily intel scrape...")
        logger.info(f"Keywords: {KEYWORDS}")
        logger.info(f"Regions: {REGIONS}")
        
        # 创建logs目录
        os.makedirs('logs', exist_ok=True)
        
        # 抓取数据
        self.fetch_ccgp_guangdong()
        self.fetch_szggzy()
        
        # 分析优先级
        high_priority, medium_priority = self.analyze_priority()
        
        logger.info(f"Found {len(high_priority)} high priority, {len(medium_priority)} medium priority")
        
        # 格式化消息
        message = self.format_feishu_message(high_priority, medium_priority)
        
        # 保存结果
        with open('logs/daily_result.json', 'w', encoding='utf-8') as f:
            json.dump({
                'date': datetime.now().isoformat(),
                'high_priority': high_priority,
                'medium_priority': medium_priority
            }, f, ensure_ascii=False, indent=2)
        
        # 发送到飞书
        self.send_to_feishu(message)
        
        logger.info("Daily intel scrape completed")

if __name__ == '__main__':
    monitor = TenderMonitor()
    monitor.run()