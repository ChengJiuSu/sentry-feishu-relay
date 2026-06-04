#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sentry → 飞书消息格式转换服务
"""
import os
import hashlib
import hmac
import time
import base64
import logging
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FEISHU_WEBHOOK_URL = os.environ["FEISHU_WEBHOOK_URL"]
FEISHU_SECRET = os.environ.get("FEISHU_SECRET", "")  # 飞书签名校验密钥（可选）

def buildFeishuSign(secret: str, timestamp: str) -> str:
    """生成飞书签名"""
    content = f"{timestamp}\n{secret}"
    mac = hmac.new(content.encode("utf-8"), digestmod=hashlib.sha256)
    return base64.b64encode(mac.digest()).decode("utf-8")

@app.route("/webhook/sentry", methods=["POST"])
def sentryWebhook():
    payload = request.get_json(force=True)
    logger.info("收到 Sentry payload: %s", payload)

    resource = request.headers.get("Sentry-Hook-Resource", "")
    data = payload.get("data", {})

    # 解析消息内容
    if resource == "event_alert":
        # Alert Rule 触发的 Issue 告警
        event = data.get("event", {})
        title = event.get("title", "未知错误")
        level = event.get("level", "error")
        project = event.get("project", "")
        web_url = event.get("web_url", "")
        rule_label = data.get("triggered_rule", "")
        env = event.get("environment", "production")
    elif resource == "metric_alert":
        # Metric Alert
        alert = data.get("metric_alert", {})
        title = alert.get("title", "指标告警")
        level = "critical" if data.get("alert_rule_trigger", {}).get("label") == "critical" else "warning"
        project = ""
        web_url = alert.get("web_url", "")
        rule_label = alert.get("title", "")
        env = ""
    else:
        # Issue 状态变更（created/resolved等）
        issue = data.get("issue", {})
        title = issue.get("title", "未知问题")
        level = issue.get("level", "error")
        project = issue.get("project", {}).get("slug", "")
        web_url = issue.get("permalink", "")
        rule_label = payload.get("action", "")
        env = ""

    # 颜色映射
    COLOR_MAP = {"fatal": "red", "error": "red", "warning": "yellow", "info": "blue"}
    card_color = COLOR_MAP.get(level, "red")
    level_emoji = {"fatal": "💀", "error": "🔴", "warning": "🟡", "info": "🔵"}.get(level, "🔴")

    # 构造飞书消息卡片
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"**问题：** {title}\n"
                    f"**项目：** {project or '-'}\n"
                    f"**环境：** {env or '-'}\n"
                    f"**规则：** {rule_label or '-'}"
                )
            }
        }
    ]
    if web_url:
        elements.append({
            "tag": "action",
            "actions": [{
                "tag": "button",
                "text": {"tag": "plain_text", "content": "查看详情"},
                "url": web_url,
                "type": "primary"
            }]
        })

    feishu_body = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"{level_emoji} Sentry 告警 [{level.upper()}]"},
                "template": card_color
            },
            "elements": elements
        }
    }

    # 飞书签名（如果配置了 Secret）
    if FEISHU_SECRET:
        timestamp = str(int(time.time()))
        feishu_body["timestamp"] = timestamp
        feishu_body["sign"] = buildFeishuSign(FEISHU_SECRET, timestamp)

    resp = requests.post(FEISHU_WEBHOOK_URL, json=feishu_body, timeout=5)
    logger.info("飞书响应: %s %s", resp.status_code, resp.text)
    return jsonify({"status": "ok"})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)