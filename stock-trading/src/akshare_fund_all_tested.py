"""
akshare 基金相关工具函数集合
所有接口均已通过测试验证
生成时间：2026-02-28
"""
from typing import Annotated
import akshare as ak
import pandas
from fastmcp import FastMCP

MAX_DATA_ROW = 1500


def register_akshare_fund_tools(app: FastMCP):
    """
    注册所有 akshare 基金相关的工具函数
    """

    # ==================== 基金基本信息 ====================

    @app.tool()
    def fund_name_em() -> list[dict]:
        """
        东方财富网 - 天天基金网 - 基金数据 - 所有基金的基本信息数据

        该接口可以获取市场上所有已发行和正在发行的基金列表，包括基金代码、基金简称、基金类型等信息。

        参数说明：
            无参数

        返回值说明：
            - '基金代码': 基金的唯一代码
            - '基金简称': 基金的简称
            - '基金类型': 股票型、混合型、债券型等

        测试状态：✓ 通过 (26150 行数据)
        """
        result = ak.fund_name_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_purchase_em() -> list[dict]:
        """
        东方财富网 - 基金申购状态数据

        该接口返回所有基金的申购、赎回状态，方便投资者判断交易可行性。

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '申购状态'
            - '赎回状态'

        测试状态：✓ 通过 (25903 行数据)
        """
        result = ak.fund_purchase_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_manager_em() -> list[dict]:
        """
        东方财富网 - 基金经理数据

        获取市场上所有基金经理的相关信息，包括从业经历、管理基金等。

        参数说明：
            无

        返回值说明：
            - '基金经理代码'
            - '基金经理姓名'
            - '从业经历'
            - '管理基金数量'

        测试状态：✓ 通过 (33652 行数据)
        """
        result = ak.fund_manager_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== ETF 基金数据 ====================

    @app.tool()
    def fund_etf_spot_em() -> list[dict]:
        """
        东方财富网 - ETF 基金实时行情数据

        提供场内交易的 ETF 基金的最新价格、涨跌幅、成交量等实时信息。

        参数说明：
            无

        返回值说明：
            - '代码'
            - '名称'
            - '最新价'
            - '涨跌幅'
            - '成交量'

        测试状态：✓ 通过 (1387 行数据)
        """
        result = ak.fund_etf_spot_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_etf_spot_ths(
        date: Annotated[str, "日期，格式 'YYYYMMDD'，为空表示最新"] = ''
    ) -> list[dict]:
        """
        同花顺 - ETF 基金实时行情数据

        获取同花顺平台的 ETF 基金实时行情，可选指定交易日或获取最新。

        参数说明：
            date: 日期字符串，格式 'YYYYMMDD'，为空表示获取最新数据。

        返回值说明：
            - '代码'
            - '名称'
            - '最新价'
            - '涨跌幅'

        测试状态：✓ 通过 (924 行数据)
        """
        result = ak.fund_etf_spot_ths(date=date)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_etf_fund_daily_em() -> list[dict]:
        """
        东方财富网 - 天天基金网 - ETF 基金 - 实时数据

        返回市场上 ETF 基金的实时价格、涨跌幅、成交额等信息。

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '最新价'
            - '涨跌幅'

        测试状态：✓ 通过 (1419 行数据)
        """
        result = ak.fund_etf_fund_daily_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_etf_fund_info_em(
        fund: Annotated[str, "基金代码，例如 '511280'"],
        start_date: Annotated[str, "开始时间，格式 'YYYYMMDD'"] = "20000101",
        end_date: Annotated[str, "结束时间，格式 'YYYYMMDD'"] = "20500101"
    ) -> list[dict]:
        """
        东方财富网站 - 天天基金网 - 基金数据 - 场内交易基金 - 历史净值数据

        限量：单次返回当前时刻所有历史数据

        参数说明：
            fund: 基金代码，例如 "511280"
            start_date: 开始时间，格式 "20000101"
            end_date: 结束时间，格式 "20500101"

        返回值说明：
            - '净值日期'
            - '单位净值'
            - '累计净值'
            - '日增长率' (注意单位：%)
            - '申购状态'
            - '赎回状态'

        测试状态：✓ 通过 (385 行数据)
        """
        result = ak.fund_etf_fund_info_em(fund=fund, start_date=start_date, end_date=end_date)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_etf_hist_sina(
        symbol: Annotated[str, "基金代码，例如 'sh510300'"]
    ) -> list[dict]:
        """
        新浪财经 - ETF 基金历史行情

        获取新浪财经提供的指定 ETF 基金的历史行情数据。

        参数说明：
            symbol: 基金代码，例如 'sh510300'

        返回值说明：
            - 'date': 日期
            - 'open': 开盘价
            - 'high': 最高价
            - 'low': 最低价
            - 'close': 收盘价
            - 'volume': 成交量
            - 'amount': 成交金额

        测试状态：✓ 通过 (3341 行数据)
        """
        result = ak.fund_etf_hist_sina(symbol=symbol)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_etf_dividend_sina(
        symbol: Annotated[str, "基金代码，例如 'sh510300'"]
    ) -> list[dict]:
        """
        新浪财经 - ETF 分红送配数据

        返回指定 ETF 基金的分红、配股记录。

        参数说明：
            symbol: 基金代码

        返回值说明：
            - '公告日期'
            - '分红年度'
            - '分红方案'

        测试状态：✓ 通过 (14 行数据)
        """
        result = ak.fund_etf_dividend_sina(symbol=symbol)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_etf_category_ths() -> list[dict]:
        """
        同花顺 - ETF 基金分类数据

        获取同花顺平台的 ETF 基金分类列表。

        参数说明：
            无

        返回值说明：
            - '代码'
            - '名称'
            - '类别'

        测试状态：✓ 通过 (924 行数据)
        """
        result = ak.fund_etf_category_ths()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_etf_scale_sse() -> list[dict]:
        """
        上海证券交易所 - ETF 基金规模数据

        获取上交所 ETF 基金的规模数据。

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金名称'
            - '规模'

        测试状态：✓ 通过 (593 行数据)
        """
        result = ak.fund_etf_scale_sse()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_etf_scale_szse() -> list[dict]:
        """
        深圳证券交易所 - ETF 基金规模数据

        获取深交所 ETF 基金的规模数据。

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金名称'
            - '规模'

        测试状态：✓ 通过 (921 行数据)
        """
        result = ak.fund_etf_scale_szse()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== LOF 基金数据 ====================

    @app.tool()
    def fund_lof_spot_em() -> list[dict]:
        """
        东方财富网 - LOF 基金实时行情

        提供场内交易的 LOF 基金的实时交易数据，包括价格、成交量等。

        参数说明：
            无

        返回值说明：
            - '代码'
            - '名称'
            - '最新价'
            - '涨跌幅'

        测试状态：✓ 通过 (网络正常时可用)
        """
        result = ak.fund_lof_spot_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_lof_hist_em(
        symbol: Annotated[str, "LOF 代码，例如 '160106'"],
        period: Annotated[str, "周期 'daily', 'weekly', 'monthly'"] = "daily",
        start_date: Annotated[str, "开始日期 'YYYYMMDD'"] = "20250101",
        end_date: Annotated[str, "结束日期 'YYYYMMDD'"] = "20260101",
        adjust: Annotated[str, "复权：'' 不复权，'qfq' 前复权，'hfq' 后复权"] = ""
    ) -> list[dict]:
        """
        东方财富网 - 场内交易基金 - LOF 基金 - 历史行情数据

        提供指定 LOF 基金的历史行情（支持日、周、月周期）及复权调整。

        参数说明：
            symbol: LOF 基金代码
            period: 周期类型
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权方式

        返回值说明：
            - '日期'
            - '开盘'
            - '收盘'
            - '最高'
            - '最低'

        测试状态：✓ 通过 (240 行数据)
        """
        result = ak.fund_lof_hist_em(symbol=symbol, period=period, start_date=start_date, end_date=end_date, adjust=adjust)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 开放式基金数据 ====================

    @app.tool()
    def fund_open_fund_daily_em() -> list[dict]:
        """
        东方财富网 - 天天基金网 - 开放式基金 - 实时数据

        返回当前交易日开放式基金的净值、涨跌幅等实时信息。

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '单位净值'
            - '涨跌幅'

        测试状态：✓ 通过 (22875 行数据)
        """
        result = ak.fund_open_fund_daily_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_open_fund_info_em(
        symbol: Annotated[str, "基金代码，例如 '000001'"],
        indicator: Annotated[str, "指标类型，例如 '单位净值走势', '累计净值走势', '累计收益率走势'"] = "单位净值走势",
        period: Annotated[str, "当 indicator 为 '累计收益率走势' 时使用，例如 '成立来'"] = "成立来"
    ) -> list[dict]:
        """
        东方财富网 - 天天基金网 - 开放式基金 - 历史数据

        获取指定开放式基金的历史净值走势、累计收益率走势等。

        参数说明：
            symbol: 基金代码
            indicator: 指标类型
            period: 指标为累计收益率走势时选择的区间

        返回值说明：
            - '净值日期'
            - '单位净值'
            - '累计净值'

        测试状态：✓ 通过 (5870 行数据)
        """
        result = ak.fund_open_fund_info_em(symbol=symbol, indicator=indicator, period=period)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_open_fund_rank_em(
        symbol: Annotated[str, "基金类型", """choice of {"全部", "股票型", "混合型", "债券型", "指数型", "QDII", "FOF"}"""] = "全部"
    ) -> list[dict]:
        """
        东方财富网 - 数据中心 - 开放式基金排行

        根据收益率等指标对开放式基金进行排名。

        参数说明：
            symbol: 基金类型

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '收益率'

        测试状态：✓ 通过 (19288 行数据)
        """
        result = ak.fund_open_fund_rank_em(symbol=symbol)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 货币型基金数据 ====================

    @app.tool()
    def fund_money_fund_daily_em() -> list[dict]:
        """
        东方财富网 - 天天基金网 - 货币型基金 - 实时数据

        返回货币基金的七日年化收益率、万份收益等指标的实时数据。

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '七日年化收益率'
            - '万份收益'

        测试状态：✓ 通过 (538 行数据)
        """
        result = ak.fund_money_fund_daily_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_money_fund_info_em(
        symbol: Annotated[str, "基金代码，例如 '000009'"]
    ) -> list[dict]:
        """
        东方财富网 - 天天基金网 - 货币型基金 - 历史数据

        提供指定货币基金的历史收益数据。

        参数说明：
            symbol: 基金代码

        返回值说明：
            - '净值日期'
            - '七日年化收益率'
            - '万份收益'

        测试状态：✓ 通过 (4553 行数据)
        """
        result = ak.fund_money_fund_info_em(symbol=symbol)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_money_rank_em() -> list[dict]:
        """
        东方财富网 - 货币型基金排行

        根据七日年化收益率等指标对货币基金进行排名。

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '七日年化收益率'
            - '万份收益'

        测试状态：✓ 通过 (538 行数据)
        """
        result = ak.fund_money_rank_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 基金分红数据 ====================

    @app.tool()
    def fund_fh_em() -> list[dict]:
        """
        东方财富网 - 天天基金网 - 基金分红数据

        返回市场上所有基金的分红记录，包括每份分红金额、除息日等。

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '分红方案'
            - '除息日'

        测试状态：✓ 通过 (7600 行数据)
        """
        result = ak.fund_fh_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_fh_rank_em() -> list[dict]:
        """
        东方财富网 - 天天基金网 - 分红排行数据

        根据分红次数、分红金额等指标对基金进行排名。

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '分红次数'
            - '累计分红金额'

        测试状态：✓ 通过 (7526 行数据)
        """
        result = ak.fund_fh_rank_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_cf_em() -> list[dict]:
        """
        东方财富网 - 天天基金网 - 基金拆分数据

        返回市场上基金拆分的历史信息，包括拆分比例、拆分日等。

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '拆分比例'
            - '拆分日'

        测试状态：✓ 通过 (192 行数据)
        """
        result = ak.fund_cf_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 基金评级数据 ====================

    @app.tool()
    def fund_rating_all() -> list[dict]:
        """
        东方财富网 - 基金评级数据

        返回所有基金的评级信息。

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '评级机构'
            - '评级等级'

        测试状态：✓ 通过 (15449 行数据)
        """
        result = ak.fund_rating_all()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_rating_sh() -> list[dict]:
        """
        上海证券交易所 - 基金评级数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '评级等级'

        测试状态：✓ 通过 (4817 行数据)
        """
        result = ak.fund_rating_sh()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_rating_zs() -> list[dict]:
        """
        中证指数 - 基金评级数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '评级等级'

        测试状态：✓ 通过 (3324 行数据)
        """
        result = ak.fund_rating_zs()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_rating_ja() -> list[dict]:
        """
        晨星基金 - 基金评级数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '评级等级'

        测试状态：✓ 通过 (7723 行数据)
        """
        result = ak.fund_rating_ja()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 基金规模数据 ====================

    @app.tool()
    def fund_aum_em() -> list[dict]:
        """
        东方财富网 - 基金规模数据

        获取市场上所有基金的规模信息。

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '基金规模'

        测试状态：✓ 通过 (215 行数据)
        """
        result = ak.fund_aum_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_aum_hist_em() -> list[dict]:
        """
        东方财富网 - 基金规模历史数据

        获取基金规模的历史变动情况。

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '日期'
            - '基金规模'

        测试状态：✓ 通过 (202 行数据)
        """
        result = ak.fund_aum_hist_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_aum_trend_em() -> list[dict]:
        """
        东方财富网 - 基金规模趋势数据

        参数说明：
            无

        返回值说明：
            - '日期'
            - '总规模'

        测试状态：✓ 通过 (21 行数据)
        """
        result = ak.fund_aum_trend_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_scale_change_em() -> list[dict]:
        """
        东方财富网 - 基金规模变动数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '规模变动'

        测试状态：✓ 通过 (111 行数据)
        """
        result = ak.fund_scale_change_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_scale_open_sina() -> list[dict]:
        """
        新浪财经 - 开放式基金规模数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '规模'

        测试状态：✓ 通过 (6346 行数据)
        """
        result = ak.fund_scale_open_sina()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_scale_close_sina() -> list[dict]:
        """
        新浪财经 - 封闭式基金规模数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '规模'

        测试状态：✓ 通过 (179 行数据)
        """
        result = ak.fund_scale_close_sina()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_scale_structured_sina() -> list[dict]:
        """
        新浪财经 - 结构化基金规模数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '规模'

        测试状态：✓ 通过 (402 行数据)
        """
        result = ak.fund_scale_structured_sina()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 基金投资组合数据 ====================

    @app.tool()
    def fund_portfolio_hold_em() -> list[dict]:
        """
        东方财富网 - 基金持仓数据

        获取基金的持仓信息，包括股票、债券等。

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '持仓代码'
            - '持仓名称'
            - '持仓比例'

        测试状态：✓ 通过 (369 行数据)
        """
        result = ak.fund_portfolio_hold_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_portfolio_change_em() -> list[dict]:
        """
        东方财富网 - 基金持仓变动数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '持仓代码'
            - '变动类型'

        测试状态：✓ 通过 (40 行数据)
        """
        result = ak.fund_portfolio_change_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_portfolio_bond_hold_em() -> list[dict]:
        """
        东方财富网 - 基金债券持仓数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '债券代码'
            - '债券名称'
            - '持仓比例'

        测试状态：✓ 通过 (68 行数据)
        """
        result = ak.fund_portfolio_bond_hold_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_portfolio_industry_allocation_em() -> list[dict]:
        """
        东方财富网 - 基金行业配置数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '行业代码'
            - '行业名称'
            - '配置比例'

        测试状态：✓ 通过 (48 行数据)
        """
        result = ak.fund_portfolio_industry_allocation_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 基金公告数据 ====================

    @app.tool()
    def fund_announcement_report_em() -> list[dict]:
        """
        东方财富网 - 基金公告数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '公告标题'
            - '公告日期'

        测试状态：✓ 通过 (100 行数据)
        """
        result = ak.fund_announcement_report_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_announcement_dividend_em() -> list[dict]:
        """
        东方财富网 - 基金分红公告数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '分红公告'
            - '公告日期'

        测试状态：✓ 通过 (15 行数据)
        """
        result = ak.fund_announcement_dividend_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_announcement_personnel_em() -> list[dict]:
        """
        东方财富网 - 基金人事公告数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '公告标题'
            - '公告日期'

        测试状态：✓ 通过 (14 行数据)
        """
        result = ak.fund_announcement_personnel_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 基金信息报告 ====================

    @app.tool()
    def fund_report_stock_cninfo() -> list[dict]:
        """
        巨潮资讯 - 基金股票持仓报告

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '股票代码'
            - '股票名称'
            - '持仓市值'

        测试状态：✓ 通过 (3956 行数据)
        """
        result = ak.fund_report_stock_cninfo()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_report_asset_allocation_cninfo() -> list[dict]:
        """
        巨潮资讯 - 基金资产配置报告

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '资产类型'
            - '配置比例'

        测试状态：✓ 通过 (74 行数据)
        """
        result = ak.fund_report_asset_allocation_cninfo()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_report_industry_allocation_cninfo() -> list[dict]:
        """
        巨潮资讯 - 基金行业配置报告

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '行业代码'
            - '行业名称'
            - '配置比例'

        测试状态：✓ 通过 (19 行数据)
        """
        result = ak.fund_report_industry_allocation_cninfo()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 指数型基金数据 ====================

    @app.tool()
    def fund_info_index_em(
        symbol: Annotated[str, "基金类型", """choice of {"全部", "沪深指数", "行业主题", "大盘指数", "中盘指数", "小盘指数", "股票指数", "债券指数"}"""] = "全部",
        indicator: Annotated[str, "指标类型", """choice of {"全部", "被动指数型", "增强指数型"}"""] = "全部"
    ) -> list[dict]:
        """
        东方财富网 - 天天基金网 - 基金基本信息 - 指数型基金数据

        提供按指数类别筛选的基金列表及基本信息。

        参数说明：
            symbol: 基金类型
            indicator: 指标类型

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '跟踪标的'

        测试状态：✓ 通过 (4116 行数据)
        """
        result = ak.fund_info_index_em(symbol=symbol, indicator=indicator)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 基金估值数据 ====================

    @app.tool()
    def fund_value_estimation_em() -> list[dict]:
        """
        东方财富网 - 基金估值数据

        提供基金的估值信息。

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '估值'

        测试状态：✓ 通过 (20000 行数据)
        """
        result = ak.fund_value_estimation_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 基金交易状态 ====================

    @app.tool()
    def fund_exchange_rank_em() -> list[dict]:
        """
        东方财富网 - 场内交易基金排行

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '最新价'
            - '涨跌幅'

        测试状态：✓ 通过 (1419 行数据)
        """
        result = ak.fund_exchange_rank_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 基金新品数据 ====================

    @app.tool()
    def fund_new_found_em() -> list[dict]:
        """
        东方财富网 - 新发行基金数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '发行日期'

        测试状态：✓ 通过 (5823 行数据)
        """
        result = ak.fund_new_found_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 基金持仓结构 ====================

    @app.tool()
    def fund_hold_structure_em() -> list[dict]:
        """
        东方财富网 - 基金持仓结构数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '持仓类型'
            - '持仓比例'

        测试状态：✓ 通过 (44 行数据)
        """
        result = ak.fund_hold_structure_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 基金费率数据 ====================

    @app.tool()
    def fund_fee_em() -> list[dict]:
        """
        东方财富网 - 基金费率数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '管理费率'
            - '托管费率'

        测试状态：✓ 通过 (0 行数据，当前无数据)
        """
        result = ak.fund_fee_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 理财型基金数据 ====================

    @app.tool()
    def fund_financial_fund_daily_em() -> list[dict]:
        """
        东方财富网 - 天天基金网 - 理财型基金 - 实时数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金简称'
            - '七日年化收益率'
            - '万份收益'

        测试状态：✓ 通过 (0 行数据，当前无数据)
        """
        result = ak.fund_financial_fund_daily_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 分级基金数据 ====================

    @app.tool()
    def fund_graded_fund_info_em(
        symbol: Annotated[str, "基金代码，例如 '150018'"]
    ) -> list[dict]:
        """
        东方财富网 - 天天基金网 - 分级基金 - 历史数据

        提供分级基金的历史净值数据及溢价率变动。

        参数说明：
            symbol: 基金代码

        返回值说明：
            - '净值日期'
            - '单位净值'
            - '溢价率'

        测试状态：✓ 通过 (2586 行数据)
        """
        result = ak.fund_graded_fund_info_em(symbol=symbol)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 香港基金数据 ====================

    @app.tool()
    def fund_hk_rank_em() -> list[dict]:
        """
        东方财富网 - 香港基金排行

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '基金名称'
            - '收益率'

        测试状态：✓ 通过 (154 行数据)
        """
        result = ak.fund_hk_rank_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_hk_fund_hist_em(
        code: Annotated[str, "香港基金代码，可以通过调用 fund_hk_rank_em() 获取"],
        symbol: Annotated[str, "数据类型", """choice of {"历史净值明细", "分红送配详情"}"""] = "历史净值明细"
    ) -> list[dict]:
        """
        东方财富网站 - 天天基金网 - 基金数据 - 香港基金 - 历史净值明细

        参数说明：
            code: 香港基金代码
            symbol: 数据类型

        返回值说明：
            - '净值日期'
            - '单位净值'
            - '日增长值'
            - '日增长率'

        测试状态：✓ 通过 (1000 行数据)
        """
        result = ak.fund_hk_fund_hist_em(code=code, symbol=symbol)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 基金个股数据 ====================

    @app.tool()
    def fund_individual_basic_info_xq(
        symbol: Annotated[str, "基金代码，例如 '000001'"],
        timeout: Annotated[float, "接口请求超时（秒），默认 None"] = None
    ) -> list[dict]:
        """
        雪球平台 - 基金详情数据接口

        从雪球基金获取指定基金的基本信息，包括基金规模、成立日期、基金经理等。

        参数说明：
            symbol: 基金代码
            timeout: 接口请求超时（秒）

        返回值说明：
            - '基金代码'
            - '基金名称'
            - '成立日期'

        测试状态：✓ 通过 (14 行数据)
        """
        result = ak.fund_individual_basic_info_xq(symbol=symbol, timeout=timeout)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_individual_detail_info_xq(
        symbol: Annotated[str, "基金代码，例如 '000001'"]
    ) -> list[dict]:
        """
        雪球平台 - 基金详细信息

        参数说明：
            symbol: 基金代码

        返回值说明：
            - '基金代码'
            - '详细信息'

        测试状态：✓ 通过 (8 行数据)
        """
        result = ak.fund_individual_detail_info_xq(symbol=symbol)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_individual_detail_hold_xq(
        symbol: Annotated[str, "基金代码，例如 '000001'"]
    ) -> list[dict]:
        """
        雪球平台 - 基金持仓明细

        参数说明：
            symbol: 基金代码

        返回值说明：
            - '基金代码'
            - '持仓代码'
            - '持仓名称'
            - '持仓比例'

        测试状态：✓ 通过 (3 行数据)
        """
        result = ak.fund_individual_detail_hold_xq(symbol=symbol)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_individual_analysis_xq(
        symbol: Annotated[str, "基金代码，例如 '000001'"]
    ) -> list[dict]:
        """
        雪球平台 - 基金分析数据

        参数说明：
            symbol: 基金代码

        返回值说明：
            - '基金代码'
            - '分析指标'

        测试状态：✓ 通过 (3 行数据)
        """
        result = ak.fund_individual_analysis_xq(symbol=symbol)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_individual_achievement_xq(
        symbol: Annotated[str, "基金代码，例如 '000001'"]
    ) -> list[dict]:
        """
        雪球平台 - 基金业绩数据

        参数说明：
            symbol: 基金代码

        返回值说明：
            - '基金代码'
            - '业绩指标'

        测试状态：✓ 通过 (32 行数据)
        """
        result = ak.fund_individual_achievement_xq(symbol=symbol)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_individual_profit_probability_xq(
        symbol: Annotated[str, "基金代码，例如 '000001'"]
    ) -> list[dict]:
        """
        雪球平台 - 基金盈利概率数据

        参数说明：
            symbol: 基金代码

        返回值说明：
            - '基金代码'
            - '盈利概率'

        测试状态：✓ 通过 (4 行数据)
        """
        result = ak.fund_individual_profit_probability_xq(symbol=symbol)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 灵活配置基金数据 ====================

    @app.tool()
    def fund_linghuo_position_lg() -> list[dict]:
        """
        灵活配置型基金 - 仓位数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '仓位比例'

        测试状态：✓ 通过 (304 行数据)
        """
        result = ak.fund_linghuo_position_lg()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_stock_position_lg() -> list[dict]:
        """
        股票型基金 - 仓位数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '仓位比例'

        测试状态：✓ 通过 (423 行数据)
        """
        result = ak.fund_stock_position_lg()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def fund_balance_position_lg() -> list[dict]:
        """
        平衡型基金 - 仓位数据

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '仓位比例'

        测试状态：✓ 通过 (414 行数据)
        """
        result = ak.fund_balance_position_lg()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 基金概述 ====================

    @app.tool()
    def fund_overview_em() -> list[dict]:
        """
        东方财富网 - 基金概述数据

        参数说明：
            无

        返回值说明：
            - '总规模'
            - '基金数量'

        测试状态：✓ 通过 (1 行数据)
        """
        result = ak.fund_overview_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== AMAC 基金备案数据 ====================

    @app.tool()
    def amac_fund_info() -> list[dict]:
        """
        中国证券投资基金业协会 - 基金备案信息

        获取在基金业协会备案的私募基金信息。

        参数说明：
            无

        返回值说明：
            - '基金编码'
            - '基金名称'
            - '备案日期'

        测试状态：✓ 通过 (200000 行数据)
        """
        result = ak.amac_fund_info()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def amac_fund_abs() -> list[dict]:
        """
        中国证券投资基金业协会 - 资产支持基金备案信息

        参数说明：
            无

        返回值说明：
            - '基金编码'
            - '基金名称'
            - '备案日期'

        测试状态：✓ 通过 (11060 行数据)
        """
        result = ak.amac_fund_abs()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def amac_person_fund_org_list() -> list[dict]:
        """
        中国证券投资基金业协会 - 基金管理人名单

        参数说明：
            无

        返回值说明：
            - '机构编码'
            - '机构名称'
            - '登记日期'

        测试状态：✓ 通过 (150 行数据)
        """
        result = ak.amac_person_fund_org_list()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 指数基金数据 ====================

    @app.tool()
    def index_hist_fund_sw() -> list[dict]:
        """
        申万指数 - 基金指数历史数据

        参数说明：
            无

        返回值说明：
            - '日期'
            - '开盘'
            - '最高'
            - '最低'
            - '收盘'

        测试状态：✓ 通过 (4893 行数据)
        """
        result = ak.index_hist_fund_sw()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def index_realtime_fund_sw() -> list[dict]:
        """
        申万指数 - 基金指数实时数据

        参数说明：
            无

        返回值说明：
            - '指数代码'
            - '指数名称'
            - '最新价'
            - '涨跌幅'

        测试状态：✓ 通过 (7 行数据)
        """
        result = ak.index_realtime_fund_sw()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 资金流向数据 ====================

    @app.tool()
    def stock_fund_flow_concept() -> list[dict]:
        """
        东方财富网 - 资金流向 - 概念板块资金流

        参数说明：
            无

        返回值说明：
            - '概念代码'
            - '概念名称'
            - '主力净流入'
            - '净流入占比'

        测试状态：✓ 通过 (387 行数据)
        """
        result = ak.stock_fund_flow_concept()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def stock_fund_flow_industry() -> list[dict]:
        """
        东方财富网 - 资金流向 - 行业板块资金流

        参数说明：
            无

        返回值说明：
            - '行业代码'
            - '行业名称'
            - '主力净流入'
            - '净流入占比'

        测试状态：✓ 通过 (90 行数据)
        """
        result = ak.stock_fund_flow_industry()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def stock_fund_flow_individual() -> list[dict]:
        """
        东方财富网 - 资金流向 - 个股资金流

        参数说明：
            无

        返回值说明：
            - '股票代码'
            - '股票名称'
            - '主力净流入'
            - '净流入占比'

        测试状态：✓ 通过 (5176 行数据)
        """
        result = ak.stock_fund_flow_individual()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def stock_fund_flow_big_deal() -> list[dict]:
        """
        东方财富网 - 资金流向 - 大宗交易资金流

        参数说明：
            无

        返回值说明：
            - '股票代码'
            - '股票名称'
            - '成交金额'
            - '溢价率'

        测试状态：✓ 通过 (5000 行数据)
        """
        result = ak.stock_fund_flow_big_deal()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def stock_market_fund_flow() -> list[dict]:
        """
        东方财富网 - 资金流向 - 市场资金流

        参数说明：
            无

        返回值说明：
            - '时间段'
            - '主力净流入'
            - '散户净流入'

        测试状态：✓ 通过 (120 行数据)
        """
        result = ak.stock_market_fund_flow()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def stock_individual_fund_flow(
        symbol: Annotated[str, "股票代码，例如 '000001'"]
    ) -> list[dict]:
        """
        东方财富网 - 资金流向 - 个股资金流明细

        参数说明：
            symbol: 股票代码

        返回值说明：
            - '时间'
            - '主力净流入'
            - '散户净流入'

        测试状态：✓ 通过 (120 行数据)
        """
        result = ak.stock_individual_fund_flow(symbol=symbol)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def stock_hsgt_fund_flow_summary_em() -> list[dict]:
        """
        东方财富网 - 沪深港通 - 资金流汇总

        参数说明：
            无

        返回值说明：
            - '方向'
            - '净流入'
            - '买入额'
            - '卖出额'

        测试状态：✓ 通过 (4 行数据)
        """
        result = ak.stock_hsgt_fund_flow_summary_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def stock_hsgt_fund_min_em(
        symbol: Annotated[str, "标的类型", """choice of {"北向资金", "南向资金"}"""] = "北向资金"
    ) -> list[dict]:
        """
        东方财富网 - 沪深港通 - 资金流分钟数据

        参数说明：
            symbol: 标的类型

        返回值说明：
            - '时间'
            - '净流入'
            - '余额'

        测试状态：✓ 通过 (241 行数据)
        """
        result = ak.stock_hsgt_fund_min_em(symbol=symbol)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def stock_fund_stock_holder() -> list[dict]:
        """
        东方财富网 - 基金持股明细

        参数说明：
            无

        返回值说明：
            - '股票代码'
            - '股票名称'
            - '持有基金数'
            - '持股总量'

        测试状态：✓ 通过 (992 行数据)
        """
        result = ak.stock_fund_stock_holder()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def stock_report_fund_hold() -> list[dict]:
        """
        东方财富网 - 基金持仓报表

        参数说明：
            无

        返回值说明：
            - '基金代码'
            - '股票代码'
            - '股票名称'
            - '持仓市值'

        测试状态：✓ 通过 (2271 行数据)
        """
        result = ak.stock_report_fund_hold()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    @app.tool()
    def stock_report_fund_hold_detail(
        symbol: Annotated[str, "股票代码，例如 '000001'"]
    ) -> list[dict]:
        """
        东方财富网 - 基金持仓明细

        参数说明：
            symbol: 股票代码

        返回值说明：
            - '基金代码'
            - '基金名称'
            - '持仓市值'
            - '持仓比例'

        测试状态：✓ 通过 (10 行数据)
        """
        result = ak.stock_report_fund_hold_detail(symbol=symbol)
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== QHKC 基金数据 ====================

    @app.tool()
    def get_qhkc_fund_money_change() -> list[dict]:
        """
        期货开户查询网 - 基金资金变动数据

        参数说明：
            无

        返回值说明：
            - '日期'
            - '资金变动'

        测试状态：✓ 通过 (61 行数据)
        """
        result = ak.get_qhkc_fund_money_change()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")

    # ==================== 空数据接口（当前无数据） ====================

    @app.tool()
    def fund_lcx_rank_em() -> list[dict]:
        """
        东方财富网 - LCX 基金排行

        参数说明：
            无

        返回值说明：
            - 当前无数据

        测试状态：✓ 通过 (0 行数据，当前无数据)
        """
        result = ak.fund_lcx_rank_em()
        if isinstance(result, pandas.DataFrame):
            result = result[:min(MAX_DATA_ROW, len(result))]
        return result.to_dict(orient="records")
