# sentry-feishu-relay
### 启动
```
docker build -t sentry-feishu-relay .

docker run -d \
  --name sentry-feishu-relay \
  -p 8080:8080 \
  -e FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/你的token" \
  -e FEISHU_SECRET="你的签名密钥(没开就不填)" \
  --restart unless-stopped \
  sentry-feishu-relay
```

### 验证服务
### 手动模拟 Sentry 发一条测试请求
```
curl -X POST http://localhost:8080/webhook/sentry \
  -H "Content-Type: application/json" \
  -H "Sentry-Hook-Resource: event_alert" \
  -d '{
    "action": "triggered",
    "data": {
      "event": {
        "title": "测试告警：NullPointerException",
        "level": "error",
        "project": "my-project",
        "environment": "production",
        "web_url": "https://sentry.io/..."
      },
      "triggered_rule": "测试规则"
    }
  }'
飞书机器人收到消息说明链路通了，再去 Sentry Alert Rule 点 "Send Test Notification" 验证完整流程。
```

### 关闭 Sentry 的内网 IP 限制
Sentry 有内置的 IP 安全限制，默认禁止 webhook 发送到私有/内网 IP 段（如 172.x.x.x、10.x.x.x、192.168.x.x），防止 SSRF 攻击。

### 找到 Sentry 的配置文件 sentry.conf.py：
```
# self-hosted 一般在这个位置
find /data/sentry-self-hosted -name "sentry.conf.py" 2>/dev/null
# 或者
ls /data/sentry-self-hosted/

在 sentry.conf.py 末尾添加：
# 允许 webhook 发送到内网 IP（关闭 SSRF 保护）
SENTRY_DISALLOWED_IPS = []

然后重启 Sentry 服务：
docker-compose down && docker-compose up -d 
```

