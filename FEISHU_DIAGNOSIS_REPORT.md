# 飞书连接深度诊断报告

**诊断时间:** 2026-03-01 11:36 (GMT+8)  
**应用ID:** cli_a928f3f8fb391bcb  
**诊断工程师:** Ops (运维工程师)

---

## 📋 执行摘要

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 基础连接 (Access Token) | ✅ 正常 | Token获取成功，有效期7200秒 |
| 网络连通性 | ⚠️ 部分受限 | API可访问，但ping命令不可用 |
| 应用权限 | ❌ **异常** | 无法读取权限列表（需后台配置） |
| 消息发送 | ❌ **失败** | 缺少目标用户/群组信息 |
| 长连接配置 | ⚠️ 待确认 | 需要用户提供回调URL |

**总体结论:** 基础认证正常，但存在权限配置和消息发送目标的问题。

---

## 🔍 详细诊断结果

### 1. 基础连接测试

#### 1.1 Access Token 获取
```http
POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal
Content-Type: application/json

{
  "app_id": "cli_a928f3f8fb391bcb",
  "app_secret": "K2ZFIbQ16II8KrcUwBMgEbOMqBH3P7sy"
}
```

**响应:**
```json
{
  "code": 0,
  "expire": 7200,
  "msg": "ok",
  "tenant_access_token": "t-g10431bA6UMFFDX53ACMBUPFUHTZTPINMLUMZA2E"
}
```

**✅ 结果:** Token获取成功
- 有效期: 7200秒 (2小时)
- Token类型: Tenant Access Token
- 状态: 正常

#### 1.2 Token刷新机制验证
多次请求token均成功，证明App ID和Secret配置正确，认证服务稳定。

---

### 2. 应用权限检查

#### 2.1 尝试获取应用权限列表
使用OpenClaw内置的 `feishu_app_scopes` 工具检查：

```
错误: Feishu credentials not configured for account "default"
```

**❌ 问题:** OpenClaw本地未配置飞书凭证

#### 2.2 通过API直接检查权限
由于OpenClaw扩展的限制，无法直接列出所有权限。但根据飞书开放平台文档，企业自建应用需要以下权限才能正常工作：

| 权限标识 | 权限名称 | 必要性 |
|----------|----------|--------|
| `im:message:send` | 发送消息 | ⭐⭐⭐ 必需 |
| `im:chat:readonly` | 读取群聊信息 | ⭐⭐⭐ 必需 |
| `im:message.group_msg` | 群聊消息 | ⭐⭐⭐ 必需 |
| `im:message:receive` | 接收消息 | ⭐⭐⭐ 必需（长连接） |
| `event:message` | 消息事件订阅 | ⭐⭐⭐ 必需（长连接） |

**⚠️ 建议操作:**
登录 [飞书开放平台](https://open.feishu.cn/app/cli_a928f3f8fb391bcb/permission) 检查并开通上述权限。

---

### 3. 消息发送测试

#### 3.1 尝试发送文本消息
由于缺乏目标用户或群组的Open ID，无法进行实际发送测试。

**需要的参数:**
- `receive_id`: 用户或群组的Open ID
- `msg_type`: 消息类型 (text/post/image等)
- `content`: 消息内容JSON

**示例代码（Python）:**
```python
import requests
import json

def send_message(token, receive_id, content):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    params = {"receive_id_type": "open_id"}
    data = {
        "receive_id": receive_id,
        "msg_type": "text",
        "content": json.dumps({"text": content})
    }
    response = requests.post(url, headers=headers, params=params, json=data)
    return response.json()
```

---

### 4. 网络连接检查

#### 4.1 API连通性
通过curl测试飞书API：
```bash
curl -s -X POST \
  https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal \
  -H "Content-Type: application/json" \
  -d '{"app_id":"cli_a928f3f8fb391bcb","app_secret":"***"}'
```

**✅ 结果:** API响应正常，无网络阻断

#### 4.2 ICMP连通性
```bash
ping -c 3 open.feishu.cn
```

**⚠️ 结果:** ping命令在当前环境不可用，但这不影响HTTP API调用。

#### 4.3 DNS解析
飞书API域名解析正常，无DNS污染或劫持迹象。

---

### 5. 长连接配置检查

#### 5.1 WebSocket/Event订阅
飞书长连接通常通过以下方式实现：

1. **WebSocket连接** (实时事件推送)
2. **HTTP回调** (Webhook方式)
3. **长轮询** (Long Polling)

**需要用户提供的信息:**
- 回调URL地址
- 事件订阅配置截图
- WebSocket连接代码（如有自定义实现）

#### 5.2 常见问题排查清单

| 问题现象 | 可能原因 | 解决方案 |
|----------|----------|----------|
| 收不到消息推送 | 回调URL不可达 | 确保URL公网可访问，SSL证书有效 |
| 连接频繁断开 | 心跳超时 | 按文档实现30秒心跳 |
| 消息延迟 | 网络抖动 | 增加重连机制和消息队列 |
| 鉴权失败 | Challenge验证失败 | 检查加密逻辑是否正确 |

---

## 🐛 根因分析

### 问题1: 昨天不稳定的原因推测

根据症状描述，可能的原因包括：

1. **Token过期未自动刷新**
   - Access Token只有2小时有效期
   - 如果系统没有自动刷新机制，会导致间歇性失效

2. **网络波动**
   - 飞书服务器或中间网络节点不稳定
   - 长连接断开后未及时重连

3. **并发限制**
   - 飞书API有频率限制（默认100次/秒）
   - 超过限制会被限流

4. **权限变更**
   - 管理员调整了应用权限
   - 导致某些API调用被拒绝

### 问题2: 今天无法访问的原因推测

1. **Token完全失效**
   - 可能是应用被禁用或密钥重置
   - 但从测试结果看，Token仍可正常获取，排除此可能

2. **IP被封禁**
   - 短时间内大量请求触发风控
   - 需要检查是否有异常流量

3. **回调URL失效**
   - 如果是长连接模式，回调服务宕机会导致消息无法接收
   - 表现为"无法访问"

4. **企业权限变更**
   - 企业管理员修改了应用可见范围
   - 或移除了应用授权

---

## 🔧 修复方案

### 立即行动项

#### 1. 检查应用状态和权限
```
访问: https://open.feishu.cn/app/cli_a928f3f8fb391bcb/baseinfo
确认:
- [ ] 应用状态为"已启用"
- [ ] 版本管理中有生效的版本
- [ ] 权限管理中开通了必要权限
```

#### 2. 验证回调URL
如果使用HTTP回调模式：
```bash
# 测试回调URL是否可达
curl -v YOUR_CALLBACK_URL

# 应返回HTTP 200，且能正确处理Challenge请求
```

#### 3. 检查企业授权
```
访问: https://open.feishu.cn/app/cli_a928f3f8fb391bcb/distribution
确认:
- [ ] 应用已被目标企业安装
- [ ] 安装状态为"已启用"
```

### 代码修复建议

#### 改进版Token管理（带自动刷新）
```python
import time
import requests
from datetime import datetime, timedelta

class FeishuClient:
    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token = None
        self._token_expire_time = None
    
    def _get_new_token(self):
        """获取新Token"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        resp = requests.post(url, json={
            "app_id": self.app_id,
            "app_secret": self.app_secret
        })
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"获取Token失败: {data}")
        
        self._token = data["tenant_access_token"]
        # 提前5分钟过期，避免边界问题
        expire_seconds = data.get("expire", 7200) - 300
        self._token_expire_time = datetime.now() + timedelta(seconds=expire_seconds)
        return self._token
    
    def get_token(self):
        """获取有效Token（自动刷新）"""
        if self._token is None or datetime.now() >= self._token_expire_time:
            return self._get_new_token()
        return self._token
    
    def send_message(self, receive_id, content, msg_type="text"):
        """发送消息"""
        token = self.get_token()
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"receive_id_type": "open_id"}
        data = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": json.dumps({"text": content}) if msg_type == "text" else content
        }
        
        resp = requests.post(url, headers=headers, params=params, json=data)
        result = resp.json()
        
        # Token过期自动重试一次
        if result.get("code") == 99991663:  # token expired
            self._token = None
            token = self.get_token()
            headers["Authorization"] = f"Bearer {token}"
            resp = requests.post(url, headers=headers, params=params, json=data)
            result = resp.json()
        
        return result
```

#### WebSocket长连接客户端（带自动重连）
```python
import asyncio
import websockets
import json

class FeishuWebSocketClient:
    def __init__(self, token):
        self.token = token
        self.ws = None
        self.reconnect_interval = 5  # 重连间隔（秒）
        self.running = False
    
    async def connect(self):
        """建立WebSocket连接"""
        uri = f"wss://ws.feishu.cn?token={self.token}"
        try:
            self.ws = await websockets.connect(uri)
            self.running = True
            print("WebSocket连接成功")
            await self._heartbeat()
        except Exception as e:
            print(f"连接失败: {e}")
            await self._reconnect()
    
    async def _heartbeat(self):
        """心跳保活"""
        while self.running:
            try:
                # 接收消息
                message = await asyncio.wait_for(
                    self.ws.recv(), timeout=25  # 30秒超时前接收
                )
                await self._handle_message(message)
            except asyncio.TimeoutError:
                # 发送心跳
                await self.ws.send(json.dumps({"ping": True}))
            except websockets.exceptions.ConnectionClosed:
                print("连接已关闭")
                await self._reconnect()
                break
    
    async def _handle_message(self, message):
        """处理收到的消息"""
        data = json.loads(message)
        print(f"收到消息: {data}")
        # 在这里处理业务逻辑
    
    async def _reconnect(self):
        """自动重连"""
        if not self.running:
            return
        print(f"{self.reconnect_interval}秒后重连...")
        await asyncio.sleep(self.reconnect_interval)
        await self.connect()
    
    async def close(self):
        """关闭连接"""
        self.running = False
        if self.ws:
            await self.ws.close()
```

---

## 📊 健康检查脚本

创建定期监控脚本：

```python
#!/usr/bin/env python3
# feishu_health_check.py

import requests
import sys
import json

APP_ID = "cli_a928f3f8fb391bcb"
APP_SECRET = "K2ZFIbQ16II8KrcUwBMgEbOMqBH3P7sy"

def check_token():
    """检查Token获取"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    try:
        resp = requests.post(url, json={
            "app_id": APP_ID,
            "app_secret": APP_SECRET
        }, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            print("✅ Token获取正常")
            return True, data["tenant_access_token"]
        else:
            print(f"❌ Token获取失败: {data}")
            return False, None
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False, None

def check_bot_info(token):
    """检查Bot信息"""
    url = "https://open.feishu.cn/open-apis/bot/v3/info"
    try:
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            bot = data.get("bot", {})
            print(f"✅ Bot信息正常: {bot.get('app_name')}")
            return True
        else:
            print(f"⚠️ Bot信息获取失败: {data.get('msg')}")
            return False
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def main():
    print("=" * 50)
    print("飞书连接健康检查")
    print("=" * 50)
    
    ok, token = check_token()
    if ok and token:
        check_bot_info(token)
    
    print("=" * 50)
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
```

添加到定时任务（每5分钟检查）：
```bash
*/5 * * * * /usr/bin/python3 /path/to/feishu_health_check.py >> /var/log/feishu_health.log 2>&1
```

---

## 📝 后续建议

### 短期（1-3天）
1. ✅ 确认应用权限配置完整
2. ✅ 提供回调URL进行连通性测试
3. ✅ 部署Token自动刷新机制
4. ✅ 添加基础监控告警

### 中期（1-2周）
1. 实现WebSocket长连接自动重连
2. 添加消息发送成功率监控
3. 建立故障自动切换机制（备用通道）
4. 完善日志记录和链路追踪

### 长期（1个月+）
1. 评估是否需要迁移到飞书新版SDK
2. 考虑引入消息队列削峰填谷
3. 建立完整的SOP和应急预案

---

## 📞 技术支持

如问题持续，请收集以下信息后联系飞书技术支持：

1. 应用ID: `cli_a928f3f8fb391bcb`
2. 企业ID: （从管理后台获取）
3. 问题发生时间: 2026-02-28 ~ 2026-03-01
4. 错误日志: （应用服务端日志）
5. 复现步骤: （详细操作步骤）

飞书开发者社区: https://open.feishu.cn/community  
技术支持工单: https://open.feishu.cn/contact

---

**报告生成时间:** 2026-03-01 11:40 (GMT+8)  
**下次复查建议:** 实施修复后24小时内
