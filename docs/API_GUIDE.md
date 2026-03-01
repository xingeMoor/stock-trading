# Q脑系统 API 设计规范

## 1. RESTful API 设计原则

### 1.1 核心原则

1. **资源导向**: URL 表示资源，HTTP 方法表示操作
2. **无状态**: 每个请求包含所有必要信息
3. **统一接口**: 一致的命名、格式、错误处理
4. **可发现性**: 完善的文档和 HATEOAS 链接
5. **版本控制**: URL 中包含版本号

### 1.2 URL 设计规范

**格式**:
```
https://api.qbrain.io/v1/{resource}/{id}/{sub-resource}
```

**命名规则**:
- 使用小写字母
- 单词间用连字符 `-` 分隔
- 使用复数名词表示资源集合
- 避免动词，用 HTTP 方法表达动作

**示例**:
```
✅ GET    /v1/strategies              # 获取策略列表
✅ GET    /v1/strategies/{id}         # 获取单个策略
✅ POST   /v1/strategies              # 创建策略
✅ PUT    /v1/strategies/{id}         # 更新策略
✅ DELETE /v1/strategies/{id}         # 删除策略
✅ GET    /v1/strategies/{id}/signals # 获取策略信号

❌ GET    /v1/getStrategies           # 包含动词
❌ GET    /v1/strategy/{id}           # 应该用复数
❌ POST   /v1/strategies/create       # 动词冗余
```

### 1.3 HTTP 方法语义

| 方法 | 用途 | 幂等 | 安全 |
|-----|------|------|------|
| GET | 获取资源 | ✅ | ✅ |
| POST | 创建资源 | ❌ | ❌ |
| PUT | 全量更新 | ✅ | ❌ |
| PATCH | 部分更新 | ❌ | ❌ |
| DELETE | 删除资源 | ✅ | ❌ |

---

## 2. 统一返回格式

### 2.1 成功响应

**单资源**:
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "操作成功",
  "data": {
    "id": "strat_001",
    "name": "MA Cross Strategy",
    "status": "active",
    "created_at": "2026-03-01T10:00:00Z",
    "updated_at": "2026-03-01T10:00:00Z"
  },
  "meta": {
    "request_id": "req_123456789",
    "timestamp": "2026-03-01T10:00:00Z"
  }
}
```

**资源列表**:
```json
{
  "success": true,
  "code": "SUCCESS",
  "message": "查询成功",
  "data": {
    "items": [
      {
        "id": "strat_001",
        "name": "MA Cross Strategy",
        "status": "active"
      },
      {
        "id": "strat_002",
        "name": "RSI Strategy",
        "status": "inactive"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 150,
      "total_pages": 8,
      "has_next": true,
      "has_prev": false
    }
  },
  "meta": {
    "request_id": "req_123456789",
    "timestamp": "2026-03-01T10:00:00Z"
  }
}
```

### 2.2 错误响应

**通用错误格式**:
```json
{
  "success": false,
  "code": "ERROR_CODE",
  "message": "人类可读的错误描述",
  "data": null,
  "error": {
    "type": "validation_error",
    "field": "symbol",
    "details": [
      {
        "field": "symbol",
        "message": "标的代码不能为空",
        "code": "required"
      }
    ]
  },
  "meta": {
    "request_id": "req_123456789",
    "timestamp": "2026-03-01T10:00:00Z",
    "documentation_url": "https://docs.qbrain.io/errors/ERROR_CODE"
  }
}
```

### 2.3 HTTP 状态码使用

| 状态码 | 场景 | 示例 |
|-------|------|------|
| 200 OK | 成功获取/更新 | GET, PUT, PATCH |
| 201 Created | 成功创建 | POST |
| 204 No Content | 成功删除 | DELETE |
| 400 Bad Request | 请求参数错误 | 验证失败 |
| 401 Unauthorized | 未认证 | Token 缺失/过期 |
| 403 Forbidden | 无权限 | 权限不足 |
| 404 Not Found | 资源不存在 | ID 错误 |
| 409 Conflict | 资源冲突 | 重复创建 |
| 422 Unprocessable Entity | 语义错误 | 业务规则违反 |
| 429 Too Many Requests | 请求限流 | 超过速率限制 |
| 500 Internal Server Error | 服务器错误 | 未处理异常 |
| 502 Bad Gateway | 上游错误 | 依赖服务失败 |
| 503 Service Unavailable | 服务不可用 | 维护/过载 |

---

## 3. 错误处理规范

### 3.1 错误码分类

**格式**: `{领域}_{错误类型}_{具体错误}`

```
认证授权:
  AUTH_001 - Token 缺失
  AUTH_002 - Token 过期
  AUTH_003 - Token 无效
  AUTH_004 - 权限不足

参数验证:
  VALIDATION_001 - 必填字段缺失
  VALIDATION_002 - 字段格式错误
  VALIDATION_003 - 字段值超出范围
  VALIDATION_004 - 字段长度超限

业务规则:
  BUSINESS_001 - 资源不存在
  BUSINESS_002 - 资源已存在
  BUSINESS_003 - 状态不允许此操作
  BUSINESS_004 - 余额不足
  BUSINESS_005 - 超出交易限额

系统错误:
  SYSTEM_001 - 数据库错误
  SYSTEM_002 - 缓存错误
  SYSTEM_003 - 消息队列错误
  SYSTEM_004 - 第三方服务错误
  SYSTEM_005 - 未知错误
```

### 3.2 错误处理最佳实践

**服务端**:
```python
from fastapi import HTTPException, status
from pydantic import BaseModel

class APIError(BaseModel):
    code: str
    message: str
    field: str | None = None
    details: list[dict] | None = None

class APIResponse(BaseModel):
    success: bool
    code: str
    message: str
    data: Any | None = None
    error: APIError | None = None

# 自定义异常
class QBrainException(HTTPException):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(
            status_code=status_code,
            detail={
                "code": code,
                "message": message,
            }
        )

# 使用示例
@app.post("/v1/orders")
async def create_order(order: OrderCreate):
    if order.quantity <= 0:
        raise QBrainException(
            code="VALIDATION_003",
            message="订单数量必须大于 0",
            status_code=422
        )
    
    if not await account_has_sufficient_funds(order):
        raise QBrainException(
            code="BUSINESS_004",
            message="账户余额不足",
            status_code=422
        )
```

**客户端**:
```python
async def handle_response(response: Response):
    if response.status_code >= 400:
        error = await response.json()
        if error["code"].startswith("VALIDATION_"):
            # 参数错误，提示用户修正
            show_validation_error(error["error"]["details"])
        elif error["code"].startswith("AUTH_"):
            # 认证错误，重新登录
            await refresh_token_and_retry()
        elif error["code"].startswith("BUSINESS_"):
            # 业务错误，显示友好提示
            show_business_error(error["message"])
        else:
            # 系统错误，记录日志并上报
            log_error(error)
            show_system_error()
```

### 3.3 错误日志记录

```python
import structlog

logger = structlog.get_logger()

async def global_exception_handler(request: Request, exc: Exception):
    request_id = request.headers.get("X-Request-ID", generate_uuid())
    
    logger.error(
        "Unhandled exception",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        exception_type=type(exc).__name__,
        exception=str(exc),
        traceback=traceback.format_exc()
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "code": "SYSTEM_005",
            "message": "服务器内部错误",
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
```

---

## 4. 请求/响应规范

### 4.1 请求头规范

**必需头**:
```
Content-Type: application/json
X-Request-ID: <uuid>           # 请求追踪 ID
X-Timestamp: <unix_timestamp>  # 请求时间戳
Authorization: Bearer <token>  # 认证 Token
```

**可选头**:
```
X-Idempotency-Key: <uuid>     # 幂等性 Key (POST/PUT)
X-Client-Version: <version>   # 客户端版本
Accept-Language: zh-CN        # 语言偏好
```

### 4.2 分页规范

**查询参数**:
```
GET /v1/strategies?page=1&page_size=20&sort=-created_at
```

**参数说明**:
| 参数 | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| page | int | 1 | 页码 (从 1 开始) |
| page_size | int | 20 | 每页数量 (最大 100) |
| sort | string | -created_at | 排序字段 (- 表示降序) |
| fields | string | * | 返回字段 (逗号分隔) |

**响应**:
```json
{
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 150,
      "total_pages": 8,
      "has_next": true,
      "has_prev": false,
      "next_page": 2,
      "prev_page": null
    }
  }
}
```

### 4.3 过滤规范

**查询参数**:
```
GET /v1/orders?status=filled&symbol=AAPL&created_at_gte=2026-01-01&created_at_lt=2026-02-01
```

**操作符**:
| 操作符 | 说明 | 示例 |
|-------|------|------|
| _eq | 等于 (可省略) | status=filled |
| _ne | 不等于 | status_ne=canceled |
| _gt | 大于 | quantity_gt=100 |
| _gte | 大于等于 | price_gte=150.5 |
| _lt | 小于 | price_lt=200 |
| _lte | 小于等于 | volume_lte=10000 |
| _in | 包含 | status_in=filled,pending |
| _contains | 包含 (数组) | tags_contains=tech |

### 4.4 批量操作规范

**批量创建**:
```http
POST /v1/orders/batch
Content-Type: application/json

{
  "items": [
    {"symbol": "AAPL", "quantity": 100, "action": "BUY"},
    {"symbol": "GOOGL", "quantity": 50, "action": "BUY"},
    {"symbol": "MSFT", "quantity": 75, "action": "BUY"}
  ]
}
```

**批量响应**:
```json
{
  "success": true,
  "data": {
    "results": [
      {"success": true, "id": "ord_001", "error": null},
      {"success": true, "id": "ord_002", "error": null},
      {"success": false, "id": null, "error": {"code": "BUSINESS_004", "message": "余额不足"}}
    ],
    "summary": {
      "total": 3,
      "success": 2,
      "failed": 1
    }
  }
}
```

---

## 5. 认证授权规范

### 5.1 认证方式

**JWT Token**:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Token 获取**:
```http
POST /v1/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123"
}

Response:
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600
  }
}
```

**Token 刷新**:
```http
POST /v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 5.2 权限模型

**RBAC 模型**:
```
用户 → 角色 → 权限 → 资源

角色定义:
  - admin: 全部权限
  - trader: 交易相关权限
  - analyst: 分析相关权限
  - viewer: 只读权限

权限粒度:
  - resource:action (如：strategy:read, order:create)
```

**权限检查**:
```python
from fastapi import Depends
from qbrain.auth import get_current_user, check_permission

@app.delete("/v1/strategies/{strategy_id}")
async def delete_strategy(
    strategy_id: str,
    user: User = Depends(get_current_user),
    _: None = Depends(check_permission("strategy:delete"))
):
    ...
```

---

## 6. 限流规范

### 6.1 限流策略

**基于用户的限流**:
```
普通用户：100 请求/分钟
VIP 用户：1000 请求/分钟
内部服务：不限
```

**基于接口的限流**:
```
交易接口：10 请求/秒
查询接口：100 请求/秒
批量接口：5 请求/分钟
```

### 6.2 限流响应

**触发限流**:
```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1709280060

{
  "success": false,
  "code": "SYSTEM_RATE_LIMIT",
  "message": "请求过于频繁，请稍后再试",
  "meta": {
    "retry_after": 60,
    "limit": 100,
    "remaining": 0,
    "reset_at": "2026-03-01T10:01:00Z"
  }
}
```

---

## 7. Webhook 规范

### 7.1 Webhook 配置

**注册 Webhook**:
```http
POST /v1/webhooks
Content-Type: application/json

{
  "url": "https://your-server.com/webhook",
  "events": ["order.filled", "order.canceled"],
  "secret": "whsec_your_secret_key"
}
```

### 7.2 Webhook 投递

**投递格式**:
```http
POST https://your-server.com/webhook
Content-Type: application/json
X-Webhook-Signature: sha256=abc123...
X-Webhook-Timestamp: 1709280000
X-Webhook-Event: order.filled

{
  "event_id": "evt_123",
  "event_type": "order.filled",
  "timestamp": "2026-03-01T10:00:00Z",
  "data": {
    "order_id": "ord_001",
    "symbol": "AAPL",
    "quantity": 100,
    "filled_price": 185.50
  }
}
```

### 7.3 签名验证

```python
import hmac
import hashlib

def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

---

## 8. API 版本管理

### 8.1 版本策略

**URL 版本**:
```
/v1/strategies
/v2/strategies
```

**版本生命周期**:
```
v1: current (当前版本)
v2: beta (测试版本)
v0: deprecated (已废弃，6 个月后下线)
```

### 8.2 破坏性变更处理

**破坏性变更** (需要升级版本号):
- 删除字段或端点
- 修改字段类型
- 修改必填字段
- 修改认证方式

**非破坏性变更** (可保持版本号):
- 新增字段或端点
- 新增可选参数
- 性能优化
- Bug 修复

---

## 9. 文档规范

### 9.1 OpenAPI 规范

```yaml
openapi: 3.0.3
info:
  title: Q脑量化交易系统 API
  version: 1.0.0
  description: Q脑系统的 RESTful API 文档

servers:
  - url: https://api.qbrain.io/v1
    description: 生产环境
  - url: https://staging-api.qbrain.io/v1
    description: 预发布环境

paths:
  /strategies:
    get:
      summary: 获取策略列表
      tags:
        - strategies
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: page_size
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/StrategyListResponse'
        '401':
          description: 未认证
        '429':
          description: 请求限流
```

### 9.2 文档工具

- **API 文档**: FastAPI 自动生成 + Swagger UI
- **使用指南**: MkDocs + Markdown
- **示例代码**: 多语言 SDK (Python, JavaScript, Go)

---

*文档版本：v1.0*
*最后更新：2026-03-01*
*作者：Archie (架构师)*
