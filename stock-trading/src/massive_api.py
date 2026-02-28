"""
Massive.com API 数据获取工具
只负责数据获取，不包含分析逻辑
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# Massive API Key - 从环境变量读取
MASSIVE_API_KEY = os.getenv('MASSIVE_API_KEY')

if not MASSIVE_API_KEY:
    raise ValueError(
        "MASSIVE_API_KEY 未设置！\n"
        "请在项目根目录创建 .env 文件，添加：\n"
        "MASSIVE_API_KEY=your_api_key_here"
    )

def get_aggs(symbol: str, multiplier: int = 1, timespan: str = "day", 
             from_: str = None, to: str = None, limit: int = 5000) -> Dict[str, Any]:
    """
    获取股票聚合数据（K线）
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        if from_ is None:
            from_ = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if to is None:
            to = datetime.now().strftime('%Y-%m-%d')
        
        aggs = client.get_aggs(
            ticker=symbol,
            multiplier=multiplier,
            timespan=timespan,
            from_=from_,
            to=to,
            limit=limit
        )
        
        return {
            "symbol": symbol,
            "data": list(aggs),
            "from": from_,
            "to": to,
            "timespan": timespan
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def get_last_trade(symbol: str) -> Dict[str, Any]:
    """
    获取股票最新成交数据
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        trade = client.get_last_trade(symbol)
        
        return {
            "symbol": symbol,
            "price": float(trade.price),
            "size": int(trade.size),
            "timestamp": datetime.fromtimestamp(trade.timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def get_last_quote(symbol: str) -> Dict[str, Any]:
    """
    获取股票最新买卖报价
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        quote = client.get_last_quote(symbol)
        
        return {
            "symbol": symbol,
            "bid_price": float(quote.bid_price),
            "bid_size": int(quote.bid_size),
            "ask_price": float(quote.ask_price),
            "ask_size": int(quote.ask_size),
            "timestamp": datetime.fromtimestamp(quote.timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def get_sma(symbol: str, window: int = 20, from_: str = None, to: str = None) -> Dict[str, Any]:
    """
    获取简单移动平均指标
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        if from_ is None:
            from_ = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        if to is None:
            to = datetime.now().strftime('%Y-%m-%d')
        
        sma = client.get_sma(
            ticker=symbol,
            window=window,
            timestamp_gte=from_,
            timestamp_lt=to,
            expand_underlying=True
        )
        
        return {
            "symbol": symbol,
            "window": window,
            "data": [
                {
                    "timestamp": datetime.fromtimestamp(item.timestamp / 1000).strftime('%Y-%m-%d'),
                    "value": float(item.value),
                    "underlying": {
                        "open": float(item.underlying.open),
                        "close": float(item.underlying.close),
                        "high": float(item.underlying.high),
                        "low": float(item.underlying.low)
                    }
                } for item in sma
            ]
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def get_ema(symbol: str, window: int = 20, from_: str = None, to: str = None) -> Dict[str, Any]:
    """
    获取指数移动平均指标
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        if from_ is None:
            from_ = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        if to is None:
            to = datetime.now().strftime('%Y-%m-%d')
        
        ema = client.get_ema(
            ticker=symbol,
            window=window,
            from_=from_,
            to=to
        )
        
        return {
            "symbol": symbol,
            "window": window,
            "data": [
                {
                    "timestamp": datetime.fromtimestamp(item.timestamp / 1000).strftime('%Y-%m-%d'),
                    "value": float(item.value)
                } for item in ema
            ]
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def get_macd(symbol: str, short_window: int = 12, long_window: int = 26, 
             signal_window: int = 9, from_: str = None, to: str = None) -> Dict[str, Any]:
    """
    获取MACD指标
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        if from_ is None:
            from_ = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        if to is None:
            to = datetime.now().strftime('%Y-%m-%d')
        
        macd = client.get_macd(
            ticker=symbol,
            short_window=short_window,
            long_window=long_window,
            signal_window=signal_window,
            from_=from_,
            to=to
        )
        
        return {
            "symbol": symbol,
            "params": {
                "short_window": short_window,
                "long_window": long_window,
                "signal_window": signal_window
            },
            "data": [
                {
                    "timestamp": datetime.fromtimestamp(item.timestamp / 1000).strftime('%Y-%m-%d'),
                    "macd": float(item.value),
                    "signal": float(item.signal),
                    "histogram": float(item.histogram)
                } for item in macd
            ]
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def get_rsi(symbol: str, window: int = 14, from_: str = None, to: str = None) -> Dict[str, Any]:
    """
    获取相对强弱指标
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        if from_ is None:
            from_ = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        if to is None:
            to = datetime.now().strftime('%Y-%m-%d')
        
        rsi = client.get_rsi(
            ticker=symbol,
            window=window,
            from_=from_,
            to=to
        )
        
        return {
            "symbol": symbol,
            "window": window,
            "data": [
                {
                    "timestamp": datetime.fromtimestamp(item.timestamp / 1000).strftime('%Y-%m-%d'),
                    "value": float(item.value)
                } for item in rsi
            ]
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def get_stoch(symbol: str, k_window: int = 14, d_window: int = 3, 
              from_: str = None, to: str = None) -> Dict[str, Any]:
    """
    获取随机指标
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        if from_ is None:
            from_ = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        if to is None:
            to = datetime.now().strftime('%Y-%m-%d')
        
        stoch = client.get_stoch(
            ticker=symbol,
            k_window=k_window,
            d_window=d_window,
            from_=from_,
            to=to
        )
        
        return {
            "symbol": symbol,
            "params": {
                "k_window": k_window,
                "d_window": d_window
            },
            "data": [
                {
                    "timestamp": datetime.fromtimestamp(item.timestamp / 1000).strftime('%Y-%m-%d'),
                    "k": float(item.k),
                    "d": float(item.d)
                } for item in stoch
            ]
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def get_cci(symbol: str, window: int = 20, from_: str = None, to: str = None) -> Dict[str, Any]:
    """
    获取商品通道指标
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        if from_ is None:
            from_ = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        if to is None:
            to = datetime.now().strftime('%Y-%m-%d')
        
        cci = client.get_cci(
            ticker=symbol,
            window=window,
            from_=from_,
            to=to
        )
        
        return {
            "symbol": symbol,
            "window": window,
            "data": [
                {
                    "timestamp": datetime.fromtimestamp(item.timestamp / 1000).strftime('%Y-%m-%d'),
                    "value": float(item.value)
                } for item in cci
            ]
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def get_adx(symbol: str, window: int = 14, from_: str = None, to: str = None) -> Dict[str, Any]:
    """
    获取平均趋向指标
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        if from_ is None:
            from_ = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        if to is None:
            to = datetime.now().strftime('%Y-%m-%d')
        
        adx = client.get_adx(
            ticker=symbol,
            window=window,
            from_=from_,
            to=to
        )
        
        return {
            "symbol": symbol,
            "window": window,
            "data": [
                {
                    "timestamp": datetime.fromtimestamp(item.timestamp / 1000).strftime('%Y-%m-%d'),
                    "adx": float(item.adx),
                    "+di": float(item.plus_di),
                    "-di": float(item.minus_di)
                } for item in adx
            ]
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def get_williams_r(symbol: str, window: int = 14, from_: str = None, to: str = None) -> Dict[str, Any]:
    """
    获取威廉指标
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        if from_ is None:
            from_ = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        if to is None:
            to = datetime.now().strftime('%Y-%m-%d')
        
        williams = client.get_williams_r(
            ticker=symbol,
            window=window,
            from_=from_,
            to=to
        )
        
        return {
            "symbol": symbol,
            "window": window,
            "data": [
                {
                    "timestamp": datetime.fromtimestamp(item.timestamp / 1000).strftime('%Y-%m-%d'),
                    "value": float(item.value)
                } for item in williams
            ]
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def get_snapshot_ticker(symbol: str) -> Dict[str, Any]:
    """
    获取单只股票快照
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        snapshot = client.get_snapshot_ticker("stocks", symbol)
        
        return {
            "symbol": symbol,
            "last_trade": {
                "price": float(snapshot.last_trade.price),
                "size": int(snapshot.last_trade.size),
                "timestamp": datetime.fromtimestamp(snapshot.last_trade.timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
            },
            "last_quote": {
                "bid_price": float(snapshot.last_quote.bid_price),
                "bid_size": int(snapshot.last_quote.bid_size),
                "ask_price": float(snapshot.last_quote.ask_price),
                "ask_size": int(snapshot.last_quote.ask_size)
            },
            "day": {
                "open": float(snapshot.day.open),
                "high": float(snapshot.day.high),
                "low": float(snapshot.day.low),
                "close": float(snapshot.day.close),
                "volume": int(snapshot.day.volume)
            }
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def get_snapshot_all() -> Dict[str, Any]:
    """
    获取全部股票快照
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        snapshots = client.get_snapshot_all("stocks")
        
        return {
            "count": len(snapshots),
            "data": [
                {
                    "symbol": s.ticker,
                    "last_price": float(s.last_trade.price),
                    "change_percent": float(s.change_percent),
                    "day_volume": int(s.day.volume)
                } for s in snapshots
            ]
        }
    except Exception as e:
        return {"error": str(e)}

def get_ticker_details(symbol: str) -> Dict[str, Any]:
    """
    获取股票详情信息
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        details = client.get_ticker_details(symbol)
        
        return {
            "symbol": symbol,
            "name": details.name if hasattr(details, 'name') else symbol,
            "market": details.market if hasattr(details, 'market') else 'stocks',
            "locale": details.locale if hasattr(details, 'locale') else 'us',
            "primary_exchange": details.primary_exchange if hasattr(details, 'primary_exchange') else None,
            "type": details.type if hasattr(details, 'type') else 'cs',
            "active": details.active if hasattr(details, 'active') else True,
            "cik": details.cik if hasattr(details, 'cik') else None,
            "composite_figi": details.composite_figi if hasattr(details, 'composite_figi') else None,
            "share_class_figi": details.share_class_figi if hasattr(details, 'share_class_figi') else None,
            "market_cap": float(details.market_cap) if hasattr(details, 'market_cap') else None,
            "phone_number": details.phone_number if hasattr(details, 'phone_number') else None,
            "address": {
                "address1": details.address.address1 if hasattr(details, 'address') and hasattr(details.address, 'address1') else None,
                "city": details.address.city if hasattr(details, 'address') and hasattr(details.address, 'city') else None,
                "state": details.address.state if hasattr(details, 'address') and hasattr(details.address, 'state') else None,
                "postal_code": details.address.postal_code if hasattr(details, 'address') and hasattr(details.address, 'postal_code') else None
            },
            "description": details.description if hasattr(details, 'description') else None,
            "sic_code": details.sic_code if hasattr(details, 'sic_code') else None,
            "sic_description": details.sic_description if hasattr(details, 'sic_description') else None,
            "ticker_root": details.ticker_root if hasattr(details, 'ticker_root') else None,
            "homepage_url": details.homepage_url if hasattr(details, 'homepage_url') else None,
            "total_employees": details.total_employees if hasattr(details, 'total_employees') else None,
            "list_date": details.list_date if hasattr(details, 'list_date') else None
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def list_tickers(market: str = "stocks", locale: str = "us", limit: int = 100) -> Dict[str, Any]:
    """
    获取股票列表
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        tickers = client.list_tickers(
            market=market,
            locale=locale,
            limit=limit
        )
        
        return {
            "count": len(tickers),
            "data": [
                {
                    "symbol": t.ticker,
                    "name": t.name if hasattr(t, 'name') else t.ticker,
                    "market": t.market if hasattr(t, 'market') else market,
                    "locale": t.locale if hasattr(t, 'locale') else locale,
                    "active": t.active if hasattr(t, 'active') else True
                } for t in tickers
            ]
        }
    except Exception as e:
        return {"error": str(e)}

def list_dividends(symbol: str, limit: int = 100) -> Dict[str, Any]:
    """
    获取分红数据
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        dividends = client.list_dividends(symbol, limit=limit)
        div_list = list(dividends)
        
        if not div_list:
            return {"symbol": symbol, "dividends": []}
        
        total = sum(d.cash_amount for d in div_list)
        latest = div_list[-1]
        
        return {
            "symbol": symbol,
            "dividend_count": len(div_list),
            "total_annual_dividend": total,
            "latest": {
                "amount": float(latest.cash_amount),
                "ex_date": latest.ex_dividend_date,
                "pay_date": latest.pay_date,
                "record_date": latest.record_date if hasattr(latest, 'record_date') else None,
                "declaration_date": latest.declaration_date if hasattr(latest, 'declaration_date') else None
            },
            "all_dividends": [
                {
                    "amount": float(d.cash_amount),
                    "ex_date": d.ex_dividend_date,
                    "pay_date": d.pay_date,
                    "record_date": d.record_date if hasattr(d, 'record_date') else None,
                    "declaration_date": d.declaration_date if hasattr(d, 'declaration_date') else None
                } for d in div_list
            ]
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def list_splits(symbol: str, limit: int = 100) -> Dict[str, Any]:
    """
    获取拆股数据
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        splits = client.list_splits(symbol, limit=limit)
        split_list = list(splits)
        
        return {
            "symbol": symbol,
            "split_count": len(split_list),
            "latest": {
                "split_from": split_list[-1].split_from if split_list else None,
                "split_to": split_list[-1].split_to if split_list else None,
                "execution_date": split_list[-1].execution_date if split_list else None,
                "declaration_date": split_list[-1].declaration_date if split_list and hasattr(split_list[-1], 'declaration_date') else None,
                "record_date": split_list[-1].record_date if split_list and hasattr(split_list[-1], 'record_date') else None
            } if split_list else None,
            "all_splits": [
                {
                    "split_from": s.split_from,
                    "split_to": s.split_to,
                    "execution_date": s.execution_date,
                    "declaration_date": s.declaration_date if hasattr(s, 'declaration_date') else None,
                    "record_date": s.record_date if hasattr(s, 'record_date') else None
                } for s in split_list
            ]
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def get_market_status() -> Dict[str, Any]:
    """
    获取市场状态
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        status = client.get_market_status()
        
        # 解析服务器时间 (ISO 格式)
        server_time_str = status.server_time if isinstance(status.server_time, str) else str(status.server_time)
        
        return {
            "status": status.market if hasattr(status, 'market') else 'unknown',
            "server_time": server_time_str,
            "after_hours": status.after_hours if hasattr(status, 'after_hours') else False,
            "early_hours": status.early_hours if hasattr(status, 'early_hours') else False,
            "exchanges": {
                "nasdaq": status.exchanges.nasdaq if hasattr(status, 'exchanges') else 'unknown',
                "nyse": status.exchanges.nyse if hasattr(status, 'exchanges') else 'unknown',
                "otc": status.exchanges.otc if hasattr(status, 'exchanges') else 'unknown'
            } if hasattr(status, 'exchanges') else {}
        }
    except Exception as e:
        return {"error": str(e)}

def list_market_holidays(from_: str = None, to: str = None) -> Dict[str, Any]:
    """
    获取市场假日列表
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        if from_ is None:
            from_ = datetime.now().strftime('%Y-%m-%d')
        if to is None:
            to = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
        
        holidays = client.list_market_holidays(
            from_=from_,
            to=to
        )
        
        return {
            "from": from_,
            "to": to,
            "holidays": [
                {
                    "date": h.date,
                    "name": h.name,
                    "status": h.status if hasattr(h, 'status') else 'closed'
                } for h in holidays
            ]
        }
    except Exception as e:
        return {"error": str(e)}

def get_real_time_data(symbol: str) -> Dict[str, Any]:
    """
    获取股票实时数据（价格 + 技术指标）
    整合多个API接口的数据
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        today = datetime.now().strftime('%Y-%m-%d')
        from_ = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        # 获取聚合数据（K 线）
        aggs = client.get_aggs(
            ticker=symbol,
            multiplier=1,
            timespan='day',
            from_=from_,
            to=today,
            limit=90
        )
        
        if not aggs:
            return {"error": f"无数据 {symbol}"}
        
        latest = aggs[-1]
        
        # 获取基本信息
        try:
            details = client.get_ticker_details(symbol)
            name = details.name
        except:
            name = symbol
        
        # 获取最新交易和报价
        try:
            last_trade = get_last_trade(symbol)
        except:
            last_trade = None
            
        try:
            last_quote = get_last_quote(symbol)
        except:
            last_quote = None
        
        return {
            "symbol": symbol,
            "name": name,
            "price": float(latest.close),
            "open": float(latest.open),
            "high": float(latest.high),
            "low": float(latest.low),
            "close": float(latest.close),
            "volume": int(latest.volume) if hasattr(latest, 'volume') else 0,
            "trade_date": datetime.fromtimestamp(latest.timestamp / 1000).strftime('%Y-%m-%d'),
            "last_trade": last_trade,
            "last_quote": last_quote,
            "history": [
                {
                    "timestamp": datetime.fromtimestamp(item.timestamp / 1000).strftime('%Y-%m-%d'),
                    "open": float(item.open),
                    "high": float(item.high),
                    "low": float(item.low),
                    "close": float(item.close),
                    "volume": int(item.volume) if hasattr(item, 'volume') else 0
                } for item in aggs
            ]
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def get_all_indicators(symbol: str, period: int = 90) -> Dict[str, Any]:
    """
    获取所有技术指标
    """
    try:
        from massive import RESTClient
        client = RESTClient(api_key=MASSIVE_API_KEY)
        
        from datetime import datetime, timedelta
        timestamp_gte = (datetime.now() - timedelta(days=period)).strftime('%Y-%m-%d')
        timestamp_lt = datetime.now().strftime('%Y-%m-%d')
        
        indicators = {}
        
        # SMA
        try:
            sma = client.get_sma(symbol, window=20, timestamp_gte=timestamp_gte, timestamp_lt=timestamp_lt, expand_underlying=True)
            if sma and hasattr(sma, 'values') and sma.values:
                indicators['sma_20'] = sma.values[-1].value
        except Exception as e:
            pass
        
        # EMA
        try:
            ema = client.get_ema(symbol, window=20, timestamp_gte=timestamp_gte, timestamp_lt=timestamp_lt)
            if ema and hasattr(ema, 'values') and ema.values:
                indicators['ema_20'] = ema.values[-1].value
        except Exception as e:
            pass
        
        # MACD
        try:
            macd = client.get_macd(symbol, timestamp_gte=timestamp_gte, timestamp_lt=timestamp_lt)
            if macd and hasattr(macd, 'values') and macd.values:
                indicators['macd'] = macd.values[-1].value
                indicators['macd_signal'] = macd.values[-1].signal
                indicators['macd_histogram'] = macd.values[-1].histogram
        except Exception as e:
            pass
        
        # RSI
        try:
            rsi = client.get_rsi(symbol, window=14, timestamp_gte=timestamp_gte, timestamp_lt=timestamp_lt)
            if rsi and hasattr(rsi, 'values') and rsi.values:
                indicators['rsi_14'] = rsi.values[-1].value
        except Exception as e:
            pass
        
        # 随机指标
        try:
            stoch = client.get_stoch(symbol, timestamp_gte=timestamp_gte, timestamp_lt=timestamp_lt)
            if stoch and hasattr(stoch, 'values') and stoch.values:
                indicators['stoch_k'] = stoch.values[-1].k
                indicators['stoch_d'] = stoch.values[-1].d
        except Exception as e:
            pass
        
        # 商品通道指标
        try:
            cci = client.get_cci(symbol, timestamp_gte=timestamp_gte, timestamp_lt=timestamp_lt)
            if cci and hasattr(cci, 'values') and cci.values:
                indicators['cci'] = cci.values[-1].value
        except Exception as e:
            pass
        
        # 平均趋向指标
        try:
            adx = client.get_adx(symbol, timestamp_gte=timestamp_gte, timestamp_lt=timestamp_lt)
            if adx and hasattr(adx, 'values') and adx.values:
                indicators['adx'] = adx.values[-1].adx
                indicators['plus_di'] = adx.values[-1].plus_di
                indicators['minus_di'] = adx.values[-1].minus_di
        except Exception as e:
            pass
        
        # 威廉指标
        try:
            williams = client.get_williams_r(symbol, timestamp_gte=timestamp_gte, timestamp_lt=timestamp_lt)
            if williams and hasattr(williams, 'values') and williams.values:
                indicators['williams_r'] = williams.values[-1].value
        except Exception as e:
            pass
        
        return indicators
    except Exception as e:
        return {"error": str(e), "symbol": symbol}