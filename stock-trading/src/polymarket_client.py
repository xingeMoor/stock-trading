"""
Polymarket API Client - 完整客户端
基于官方API文档实现，支持Gamma API(公开数据)和CLOB API(交易操作)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import base64
import hashlib
import hmac
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import requests


class Network(Enum):
    """Polymarket网络环境"""
    CLOB_MAINNET = "https://clob.polymarket.com"
    CLOB_TESTNET = "https://neoclob.polymarket.com"
    GAMMA = "https://gamma-api.polymarket.com"


@dataclass
class APIResponse:
    """API响应容器"""
    success: bool
    data: Any
    status_code: int
    error: Optional[str] = None


class PolymarketAuth:
    """Polymarket认证管理器"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        signer: Optional[str] = None,
        network: Network = Network.GAMMA
    ):
        self.api_key = api_key or os.environ.get("POLYMARKET_API_KEY", "")
        self.secret = secret or os.environ.get("POLYMARKET_SECRET", "")
        self.passphrase = passphrase or os.environ.get("POLYMARKET_PASSPHRASE", "")
        self.signer = signer or os.environ.get("POLYMARKET_SIGNER", "")
        self.network = network
        
    @property
    def is_authenticated(self) -> bool:
        """检查是否已配置认证信息"""
        return bool(self.api_key and self.secret and self.passphrase)
    
    def get_auth_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """生成认证请求头"""
        timestamp = str(int(time.time()))
        message = f"{timestamp}{method.upper()}{path}{body}"
        
        try:
            secret_bytes = base64.b64decode(self.secret)
        except Exception:
            secret_bytes = self.secret.encode("utf-8")
        
        signature = hmac.new(
            secret_bytes,
            message.encode("utf-8"),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.b64encode(signature).decode("utf-8")
        
        headers = {
            "POLY-API-KEY": self.api_key,
            "POLY-PASSPHRASE": self.passphrase,
            "POLY-TIMESTAMP": timestamp,
            "POLY-SIGNATURE": signature_b64,
            "Content-Type": "application/json"
        }
        
        if self.signer:
            headers["POLY-SIGNER"] = self.signer
            
        return headers


class PolymarketClient:
    """
    Polymarket API客户端
    
    支持:
    - Gamma API: 公开市场价格、交易量等数据
    - CLOB API: 需要认证的订单、持仓等操作
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        signer: Optional[str] = None,
        network: Network = Network.GAMMA,
        timeout: int = 30
    ):
        self.auth = PolymarketAuth(api_key, secret, passphrase, signer, network)
        self.network = network
        self.base_url = network.value
        self.timeout = timeout
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "QuantTrading-Polymarket/1.0",
            "Accept": "application/json"
        })
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        requires_auth: bool = False
    ) -> APIResponse:
        """发送HTTP请求"""
        url = f"{self.base_url}{endpoint}"
        
        if requires_auth:
            if not self.auth.is_authenticated:
                return APIResponse(
                    success=False, data=None, status_code=401,
                    error="需要认证信息 (API Key, Secret, Passphrase)"
                )
            body = "" if json_data is None else str(json_data)
            headers = self.auth.get_auth_headers(method, endpoint, body)
        else:
            headers = {"Content-Type": "application/json"}
        
        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json_data,
                headers=headers,
                timeout=self.timeout
            )
            
            try:
                data = response.json()
            except ValueError:
                data = {"raw": response.text}
            
            if response.status_code >= 400:
                error_msg = data.get("error", data.get("message", f"HTTP {response.status_code}"))
                return APIResponse(
                    success=False, data=data,
                    status_code=response.status_code,
                    error=error_msg
                )
            
            return APIResponse(
                success=True, data=data,
                status_code=response.status_code
            )
            
        except requests.exceptions.RequestException as e:
            return APIResponse(
                success=False, data=None,
                status_code=0, error=str(e)
            )
    
    # ============ Gamma API - 公开数据 ============
    
    def get_markets(
        self,
        limit: int = 50,
        active: bool = True,
        closed: bool = False,
        category: Optional[str] = None
    ) -> APIResponse:
        """获取市场列表"""
        params = {
            'limit': limit,
            'active': str(active).lower(),
            'closed': str(closed).lower()
        }
        if category:
            params['category'] = category
            
        return self._request("GET", "/markets", params=params)
    
    def get_market(self, market_id: str) -> APIResponse:
        """获取特定市场详情"""
        return self._request("GET", f"/markets/{market_id}")
    
    def search_markets(self, query: str, limit: int = 20) -> APIResponse:
        """搜索市场"""
        params = {'search': query, 'limit': limit}
        return self._request("GET", "/markets", params=params)
    
    def get_categories(self) -> APIResponse:
        """获取市场分类"""
        return self._request("GET", "/categories")
    
    def get_orderbook(self, market_id: str) -> APIResponse:
        """获取订单簿"""
        return self._request("GET", f"/book?market_id={market_id}")
    
    # ============ CLOB API - 需要认证 ============
    
    def get_balances(self) -> APIResponse:
        """获取账户余额"""
        return self._request("GET", "/balance", requires_auth=True)
    
    def get_positions(self) -> APIResponse:
        """获取持仓"""
        return self._request("GET", "/positions", requires_auth=True)
    
    def get_orders(self, status: str = "OPEN") -> APIResponse:
        """获取订单列表"""
        params = {"status": status}
        return self._request("GET", "/orders", params=params, requires_auth=True)
    
    def create_order(
        self,
        market_id: str,
        side: str,  # BUY or SELL
        price: float,  # 美分单位，如50表示$0.50
        size: float
    ) -> APIResponse:
        """创建订单"""
        data = {
            "marketId": market_id,
            "side": side,
            "price": price,
            "size": size
        }
        return self._request("POST", "/order", json_data=data, requires_auth=True)


# 便捷函数 - 用于快速获取情绪数据
def get_market_sentiment(limit: int = 100) -> Dict[str, Any]:
    """
    快速获取市场情绪指标
    
    Returns:
        {
            'economy_score': float,  # -1到1，经济情绪
            'fed_score': float,      # -1到1，美联储政策预期
            'crypto_score': float,   # -1到1，加密货币情绪
            'overall_score': float,  # 综合评分
            'top_markets': list      # 重要市场列表
        }
    """
    client = PolymarketClient(network=Network.GAMMA)
    response = client.get_markets(limit=limit)
    
    if not response.success:
        return {'error': response.error}
    
    data = response.data
    if isinstance(data, list):
        markets = data
    elif isinstance(data, dict):
        markets = data.get('markets', [])
    else:
        markets = []
    
    # 分类统计
    economy_probs = []
    fed_probs = []
    crypto_probs = []
    top_markets = []
    
    for m in markets[:20]:  # 只分析前20个高流动性市场
        title = m.get('question', '').lower()
        prob = m.get('probability', 0.5)
        volume = m.get('volume', 0)
        
        market_info = {
            'title': m.get('question', '')[:60],
            'probability': prob,
            'volume': volume,
            'category': 'other'
        }
        
        # 经济相关
        if any(k in title for k in ['recession', 'gdp', 'inflation', 'cpi', 'unemployment']):
            sentiment = -(prob * 2 - 1) if 'recession' in title else (prob * 2 - 1)
            economy_probs.append((sentiment, volume))
            market_info['category'] = 'economy'
            
        # 美联储
        elif any(k in title for k in ['fed', 'rate hike', 'rate cut', 'powell']):
            sentiment = -(prob * 2 - 1) if 'hike' in title else (prob * 2 - 1)
            fed_probs.append((sentiment, volume))
            market_info['category'] = 'fed'
            
        # 加密货币
        elif any(k in title for k in ['bitcoin', 'btc', 'ethereum', 'eth']):
            crypto_probs.append((prob * 2 - 1, volume))
            market_info['category'] = 'crypto'
        
        if market_info['category'] != 'other':
            top_markets.append(market_info)
    
    # 计算加权平均
    def weighted_avg(items):
        if not items:
            return 0
        total_weight = sum(w for _, w in items)
        if total_weight == 0:
            return 0
        return sum(s * w for s, w in items) / total_weight
    
    economy_score = weighted_avg(economy_probs)
    fed_score = weighted_avg(fed_probs)
    crypto_score = weighted_avg(crypto_probs)
    
    # 综合评分 (经济40% + 美联储40% + 加密20%)
    overall_score = economy_score * 0.4 + fed_score * 0.4 + crypto_score * 0.2
    
    return {
        'economy_score': round(economy_score, 3),
        'fed_score': round(fed_score, 3),
        'crypto_score': round(crypto_score, 3),
        'overall_score': round(overall_score, 3),
        'interpretation': _interpret_score(overall_score),
        'top_markets': sorted(top_markets, key=lambda x: x['volume'], reverse=True)[:10]
    }


def _interpret_score(score: float) -> str:
    """解释情绪分数"""
    if score > 0.5:
        return "强烈乐观"
    elif score > 0.2:
        return "温和乐观"
    elif score > -0.2:
        return "中性"
    elif score > -0.5:
        return "温和悲观"
    else:
        return "强烈悲观"


def test_client():
    """测试客户端"""
    print("🧪 测试 Polymarket 客户端\n")
    
    # 测试公开API
    client = PolymarketClient(network=Network.GAMMA)
    
    print("1️⃣  获取市场列表...")
    response = client.get_markets(limit=10)
    if response.success:
        data = response.data
        # API可能返回列表或字典格式
        if isinstance(data, list):
            markets = data
        elif isinstance(data, dict):
            markets = data.get('markets', [])
        else:
            markets = []
        print(f"   ✅ 获取 {len(markets)} 个市场")
        if markets:
            print(f"   📊 TOP3:")
            for m in markets[:3]:
                print(f"      - {str(m.get('question', ''))[:45]}... ({m.get('probability', 0):.1%})")
    else:
        print(f"   ⚠️  {response.error}")
    
    print("\n2️⃣  获取市场情绪...")
    sentiment = get_market_sentiment(limit=50)
    if 'error' not in sentiment:
        print(f"   ✅ 综合评分: {sentiment['overall_score']} ({sentiment['interpretation']})")
        print(f"   📈 经济: {sentiment['economy_score']:+}")
        print(f"   🏦 美联储: {sentiment['fed_score']:+}")
        print(f"   ₿ 加密: {sentiment['crypto_score']:+}")
    else:
        print(f"   ⚠️  {sentiment['error']}")
    
    print("\n✅ 测试完成!")


if __name__ == "__main__":
    test_client()
