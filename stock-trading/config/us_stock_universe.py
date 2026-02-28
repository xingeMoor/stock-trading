"""
美股100只跨行业股票池
覆盖11个GICS行业分类
"""

US_STOCK_UNIVERSE = {
    "信息技术": [
        "AAPL",  # 苹果
        "MSFT",  # 微软
        "NVDA",  # 英伟达
        "AVGO",  # 博通
        "ORCL",  # 甲骨文
        "ADBE",  # Adobe
        "CRM",   # Salesforce
        "ACN",   # 埃森哲
        "CSCO",  # 思科
        "INTC",  # 英特尔
    ],
    "通信服务": [
        "GOOGL", # 谷歌A
        "META",  # Meta
        "NFLX",  # 奈飞
        "VZ",    # Verizon
        "T",     # AT&T
        "DIS",   # 迪士尼
        "CMCSA", # 康卡斯特
        "TMUS",  # T-Mobile
        "VOD",   # 沃达丰
        "SPOT",  # Spotify
    ],
    "医疗保健": [
        "LLY",   # 礼来
        "JNJ",   # 强生
        "UNH",   # 联合健康
        "ABBV",  # 艾伯维
        "PFE",   # 辉瑞
        "MRK",   # 默克
        "TMO",   # 赛默飞世尔
        "ABT",   # 雅培
        "DHR",   # 丹纳赫
        "BMY",   # 百时美施贵宝
    ],
    "金融": [
        "BRK-B", # 伯克希尔B
        "JPM",   # 摩根大通
        "V",     # Visa
        "MA",    # Mastercard
        "BAC",   # 美国银行
        "WFC",   # 富国银行
        "GS",    # 高盛
        "MS",    # 摩根士丹利
        "BLK",   # 贝莱德
        "AXP",   # 美国运通
    ],
    "非必需消费品": [
        "AMZN",  # 亚马逊
        "TSLA",  # 特斯拉
        "HD",    # 家得宝
        "MCD",   # 麦当劳
        "NKE",   # 耐克
        "LOW",   # Lowe's
        "SBUX",  # 星巴克
        "TJX",   # TJX公司
        "BKNG",  # Booking Holdings
        "MAR",   # 万豪国际
    ],
    "工业": [
        "GE",    # GE航空
        "CAT",   # 卡特彼勒
        "RTX",   # RTX集团
        "BA",    # 波音
        "HON",   # 霍尼韦尔
        "UPS",   # UPS
        "UNP",   # 联合太平洋铁路
        "LMT",   # 洛克希德马丁
        "DE",    # 迪尔股份
        "ETN",   # 伊顿公司
    ],
    "必需消费品": [
        "WMT",   # 沃尔玛
        "PG",    # 宝洁
        "COST",  # 好市多
        "KO",    # 可口可乐
        "PEP",   # 百事可乐
        "PM",    # 菲利普莫里斯
        "MDLZ",  # 亿滋国际
        "CL",    # 高露洁
        "GIS",   # 通用磨坊
        "KMB",   # 金佰利
    ],
    "能源": [
        "XOM",   # 埃克森美孚
        "CVX",   # 雪佛龙
        "COP",   # 康菲石油
        "EOG",   # EOG资源
        "SLB",   # 斯伦贝谢
        "MPC",   # Marathon Petroleum
        "PSX",   # Phillips 66
        "VLO",   # Valero
        "OXY",   # 西方石油
        "KMI",   # Kinder Morgan
    ],
    "原材料": [
        "LIN",   # 林德集团
        "SHW",   # 宣伟涂料
        "APD",   # 空气化工
        "FCX",   # 自由港麦克莫兰
        "NEM",   # 纽蒙特矿业
        "ECL",   # 艺康集团
        "DOW",   # 陶氏化学
        "PPG",   # PPG工业
        "DD",    # 杜邦
        "NUE",   # 纽柯钢铁
    ],
    "房地产": [
        "PLD",   # Prologis
        "AMT",   # American Tower
        "EQIX",  # Equinix
        "CCI",   # Crown Castle
        "PSA",   # Public Storage
        "O",     # Realty Income
        "SPG",   # Simon Property
        "DLR",   # Digital Realty
        "WELL",  # Welltower
        "AVB",   # AvalonBay
    ],
    "公用事业": [
        "NEE",   # NextEra Energy
        "SO",    # Southern Company
        "DUK",   # Duke Energy
        "AEP",   # American Electric Power
        "EXC",   # Exelon
        "SRE",   # Sempra Energy
        "XEL",   # Xcel Energy
        "ED",    # Consolidated Edison
        "WEC",   # WEC Energy
        "PEG",   # Public Service Enterprise
    ]
}

# 获取所有股票列表
def get_all_us_stocks():
    """获取全部100只美股"""
    all_stocks = []
    for sector, stocks in US_STOCK_UNIVERSE.items():
        all_stocks.extend(stocks)
    return all_stocks

# 按行业获取
def get_stocks_by_sector(sector: str):
    """获取指定行业的股票"""
    return US_STOCK_UNIVERSE.get(sector, [])

if __name__ == "__main__":
    stocks = get_all_us_stocks()
    print(f"美股股票池: {len(stocks)} 只")
    print(f"行业分布:")
    for sector, symbols in US_STOCK_UNIVERSE.items():
        print(f"  {sector}: {len(symbols)} 只")
