#!/usr/bin/env python
# encoding: utf-8

""" 
@version: v1.0 
@author: sunlei 
@license: Apache Licence  
@contact: 12166056@qq.com 
@site: http://blog.csdn.net/sunlei213 
@software: PyCharm Community Edition 
@file: vtobject.py 
@time: 2017/10/2 11:24 
"""
from time import strftime, localtime
from constant import *


class VtBaseData(object):
    """回调函数推送数据的基础类，其他数据类继承于此"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.gatewayName = EMPTY_STRING  # Gateway名称
        self.rawData = None  # 原始数据


class VtTickData(VtBaseData):
    """Tick行情数据类"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtTickData, self).__init__()

        # 代码相关
        self.symbol = EMPTY_STRING  # 合约代码
        self.exchange = EMPTY_STRING  # 交易所代码
        self.vtSymbol = EMPTY_STRING  # 合约在vt系统中的唯一代码，通常是 合约代码.交易所代码

        # 成交数据
        self.lastPrice = EMPTY_FLOAT  # 最新成交价
        self.lastVolume = EMPTY_INT  # 最新成交量
        self.volume = EMPTY_INT  # 今天总成交量
        self.openInterest = EMPTY_INT  # 持仓量
        self.time = EMPTY_STRING  # 时间 11:20:56.5
        self.date = EMPTY_STRING  # 日期 20151009
        self.datetime = None  # python的datetime时间对象

        # 常规行情
        self.openPrice = EMPTY_FLOAT  # 今日开盘价
        self.highPrice = EMPTY_FLOAT  # 今日最高价
        self.lowPrice = EMPTY_FLOAT  # 今日最低价
        self.preClosePrice = EMPTY_FLOAT

        self.upperLimit = EMPTY_FLOAT  # 涨停价
        self.lowerLimit = EMPTY_FLOAT  # 跌停价

        # 五档行情
        self.sellPrice1 = EMPTY_FLOAT
        self.sellPrice2 = EMPTY_FLOAT
        self.sellPrice3 = EMPTY_FLOAT
        self.sellPrice4 = EMPTY_FLOAT
        self.sellPrice5 = EMPTY_FLOAT

        self.buyPrice1 = EMPTY_FLOAT
        self.buyPrice2 = EMPTY_FLOAT
        self.buyPrice3 = EMPTY_FLOAT
        self.buyPrice4 = EMPTY_FLOAT
        self.buyPrice5 = EMPTY_FLOAT

        self.sellVolume1 = EMPTY_INT
        self.sellVolume2 = EMPTY_INT
        self.sellVolume3 = EMPTY_INT
        self.sellVolume4 = EMPTY_INT
        self.sellVolume5 = EMPTY_INT

        self.buyVolume1 = EMPTY_INT
        self.buyVolume2 = EMPTY_INT
        self.buyVolume3 = EMPTY_INT
        self.buyVolume4 = EMPTY_INT
        self.buyVolume5 = EMPTY_INT

    def set_data(self, data):
        self.symbol = data['symbol']
        self.exchange = data['exchange']
        self.vtSymbol = data['vtSymbol']

        self.lastPrice = data['lastPrice']
        self.volume = data['volume']
        # self.openInterest = data['OpenInterest']
        self.time = data['UpdateTime']
        self.date = data['TradingDay']
        self.datetime = data['datetime']

        self.openPrice = data['openPrice']
        self.highPrice = data['highPrice']
        self.lowPrice = data['lowPrice']
        self.preClosePrice = data['preClosePrice']

        #self.upperLimit = data['UpperLimitPrice']
        #self.lowerLimit = data['LowerLimitPrice']

        # LTS有5档行情
        self.sellPrice1 = data['sellPrice1']
        self.sellVolume1 = data['sellVolume1']
        self.buyPrice1 = data['buyPrice1']
        self.buyVolume1 = data['buyVolume1']

        self.sellPrice2 = data['sellPrice2']
        self.sellVolume2 = data['sellVolume2']
        self.buyPrice2 = data['buyPrice2']
        self.buyVolume2 = data['buyVolume2']

        self.sellPrice3 = data['sellPrice3']
        self.sellVolume3 = data['sellVolume3']
        self.buyPrice3 = data['buyPrice3']
        self.buyVolume3 = data['buyVolume3']

        self.sellPrice4 = data['sellPrice4']
        self.sellVolume4 = data['sellVolume4']
        self.buyPrice4 = data['buyPrice4']
        self.buyVolume4 = data['buyVolume4']

        self.sellPrice5 = data['sellPrice5']
        self.sellVolume5 = data['sellVolume5']
        self.buyPrice5 = data['buyPrice5']
        self.buyVolume5 = data['buyVolume5']

    def read_data(self):
        data = {}
        data['symbol'] = self.symbol
        data['exchange'] = self.exchange
        data['vtSymbol'] = self.vtSymbol

        data['lastPrice'] = self.lastPrice
        data['volume'] = self.volume
        # self.openInterest = data['OpenInterest']
        data['UpdateTime'] = self.time
        data['TradingDay'] = self.date
        data['datetime'] = self.datetime

        data['openPrice'] = self.openPrice
        data['highPrice'] = self.highPrice
        data['lowPrice'] = self.lowPrice
        data['preClosePrice'] = self.preClosePrice

        #self.upperLimit = data['UpperLimitPrice']
        #self.lowerLimit = data['LowerLimitPrice']

        # LTS有5档行情
        data['sellPrice1'] = self.sellPrice1
        data['sellVolume1'] = self.sellVolume1
        data['buyPrice1'] = self.buyPrice1
        data['buyVolume1'] = self.buyVolume1

        data['sellPrice2'] = self.sellPrice2
        data['sellVolume2'] = self.sellVolume2
        data['buyPrice2'] = self.buyPrice2
        data['buyVolume2'] = self.buyVolume2

        data['sellPrice3'] = self.sellPrice3
        data['sellVolume3'] = self.sellVolume3
        data['buyPrice3'] = self.buyPrice3
        data['buyVolume3'] = self.buyVolume3

        data['sellPrice4'] = self.sellPrice4
        data['sellVolume4'] = self.sellVolume4
        data['buyPrice4'] = self.buyPrice4
        data['buyVolume4'] = self.buyVolume4

        data['sellPrice5'] = self.sellPrice5
        data['sellVolume5'] = self.sellVolume5
        data['buyPrice5'] = self.buyPrice5
        data['buyVolume5'] = self.buyVolume5
        return data


class VtBarData(VtBaseData):
    """K线数据"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtBarData, self).__init__()

        self.vtSymbol = EMPTY_STRING  # vt系统代码
        self.symbol = EMPTY_STRING  # 代码
        self.exchange = EMPTY_STRING  # 交易所

        self.open = EMPTY_FLOAT  # OHLC
        self.high = EMPTY_FLOAT
        self.low = EMPTY_FLOAT
        self.close = EMPTY_FLOAT

        self.date = EMPTY_STRING  # bar开始的时间，日期
        self.time = EMPTY_STRING  # 时间
        self.datetime = None  # python的datetime时间对象

        self.volume = EMPTY_INT  # 成交量
        self.openInterest = EMPTY_INT  # 持仓量


class VtTradeData(VtBaseData):
    """成交数据类"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtTradeData, self).__init__()

        # 代码编号相关
        self.symbol = EMPTY_STRING  # 合约代码
        self.exchange = EMPTY_STRING  # 交易所代码
        self.vtSymbol = EMPTY_STRING  # 合约在vt系统中的唯一代码，通常是 合约代码.交易所代码

        self.tradeID = EMPTY_STRING  # 成交编号
        self.vtTradeID = EMPTY_STRING  # 成交在vt系统中的唯一编号，通常是 Gateway名.成交编号

        self.orderID = EMPTY_STRING  # 订单编号
        self.vtOrderID = EMPTY_STRING  # 订单在vt系统中的唯一编号，通常是 Gateway名.订单编号

        # 成交相关
        self.direction = EMPTY_UNICODE  # 成交方向
        self.offset = EMPTY_UNICODE  # 成交开平仓
        self.price = EMPTY_FLOAT  # 成交价格
        self.volume = EMPTY_INT  # 成交数量
        self.tradeTime = EMPTY_STRING  # 成交时间


class VtOrderData(VtBaseData):
    """订单数据类"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtOrderData, self).__init__()

        # 代码编号相关
        self.symbol = EMPTY_STRING  # 合约代码
        self.exchange = EMPTY_STRING  # 交易所代码
        self.vtSymbol = EMPTY_STRING  # 合约在vt系统中的唯一代码，通常是 合约代码.交易所代码

        self.orderID = EMPTY_STRING  # 订单编号
        self.vtOrderID = EMPTY_STRING  # 订单在vt系统中的唯一编号，通常是 Gateway名.订单编号

        # 报单相关
        self.inst_type = EMPTY_STRING  # 报单类别
        self.direction = EMPTY_UNICODE  # 报单方向
        self.offset = EMPTY_UNICODE  # 报单开平仓
        self.price = EMPTY_FLOAT  # 报单价格
        self.totalVolume = EMPTY_INT  # 报单总数量
        self.tradedVolume = EMPTY_INT  # 报单成交数量
        self.status = EMPTY_UNICODE  # 报单状态

        self.orderTime = EMPTY_STRING  # 发单时间
        self.cancelTime = EMPTY_STRING  # 撤单时间

        # CTP/LTS相关
        self.frontID = EMPTY_INT  # 前置机编号
        self.sessionID = EMPTY_INT  # 连接编号


class VtPositionData(VtBaseData):
    """持仓数据类"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtPositionData, self).__init__()

        # 代码编号相关
        self.symbol = EMPTY_STRING  # 合约代码
        self.exchange = EMPTY_STRING  # 交易所代码
        self.vtSymbol = EMPTY_STRING  # 合约在vt系统中的唯一代码，合约代码.交易所代码

        # 持仓相关
        self.direction = EMPTY_STRING  # 持仓方向
        self.position = EMPTY_INT  # 持仓量
        self.frozen = EMPTY_INT  # 冻结数量
        self.price = EMPTY_FLOAT  # 持仓均价
        self.vtPositionName = EMPTY_STRING  # 持仓在vt系统中的唯一代码，通常是vtSymbol.方向
        self.ydPosition = EMPTY_INT  # 昨持仓
        self.positionProfit = EMPTY_FLOAT  # 持仓盈亏


class VtAccountData(VtBaseData):
    """账户数据类"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtAccountData, self).__init__()

        # 账号代码相关
        self.accountID = EMPTY_STRING  # 账户代码
        self.vtAccountID = EMPTY_STRING  # 账户在vt中的唯一代码，通常是 Gateway名.账户代码

        # 数值相关
        self.preBalance = EMPTY_FLOAT  # 昨日账户结算净值
        self.balance = EMPTY_FLOAT  # 账户净值
        self.available = EMPTY_FLOAT  # 可用资金
        self.commission = EMPTY_FLOAT  # 今日手续费
        self.margin = EMPTY_FLOAT  # 保证金占用
        self.closeProfit = EMPTY_FLOAT  # 平仓盈亏
        self.positionProfit = EMPTY_FLOAT  # 持仓盈亏


class VtErrorData(VtBaseData):
    """错误数据类"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtErrorData, self).__init__()

        self.errorID = EMPTY_STRING  # 错误代码
        self.errorMsg = EMPTY_UNICODE  # 错误信息
        self.additionalInfo = EMPTY_UNICODE  # 补充信息

        self.errorTime = strftime('%X', localtime())  # 错误生成时间


#######################################################################
class VtLogData(VtBaseData):
    """日志数据类"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtLogData, self).__init__()

        self.logTime = strftime('%X', localtime())  # 日志生成时间
        self.logContent = EMPTY_UNICODE  # 日志信息


class VtContractData(VtBaseData):
    """合约详细信息类"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(VtContractData, self).__init__()

        self.symbol = EMPTY_STRING  # 代码
        self.exchange = EMPTY_STRING  # 交易所代码
        self.vtSymbol = EMPTY_STRING  # 合约在vt系统中的唯一代码，通常是 合约代码.交易所代码
        self.name = EMPTY_UNICODE  # 合约中文名
        self.is_t0 = False

        self.productClass = EMPTY_UNICODE  # 合约类型
        self.size = EMPTY_INT  # 合约大小
        self.priceTick = EMPTY_FLOAT  # 合约最小价格TICK

        # 期权相关
        self.strikePrice = EMPTY_FLOAT  # 期权行权价
        self.underlyingSymbol = EMPTY_STRING  # 标的物合约代码
        self.optionType = EMPTY_UNICODE  # 期权类型
        self.expiryDate = EMPTY_STRING  # 到期日


class VtSubscribeReq(object):
    """订阅行情时传入的对象类"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.symbol = EMPTY_STRING  # 代码
        self.exchange = EMPTY_STRING  # 交易所

        # 以下为IB相关
        self.productClass = EMPTY_UNICODE  # 合约类型
        self.currency = EMPTY_STRING  # 合约货币
        self.expiry = EMPTY_STRING  # 到期日
        self.strikePrice = EMPTY_FLOAT  # 行权价
        self.optionType = EMPTY_UNICODE  # 期权类型


class VtOrderReq(object):
    """发单时传入的对象类"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.symbol = EMPTY_STRING  # 代码
        self.exchange = EMPTY_STRING  # 交易所
        self.price = EMPTY_FLOAT  # 价格
        self.volume = EMPTY_INT  # 数量

        self.priceType = EMPTY_STRING  # 价格类型
        self.direction = EMPTY_STRING  # 买卖
        self.offset = EMPTY_STRING  # 开平

        # 以下为IB相关
        self.productClass = EMPTY_UNICODE  # 合约类型
        self.currency = EMPTY_STRING  # 合约货币
        self.expiry = EMPTY_STRING  # 到期日
        self.strikePrice = EMPTY_FLOAT  # 行权价
        self.optionType = EMPTY_UNICODE  # 期权类型
        self.lastTradeDateOrContractMonth = EMPTY_STRING  # 合约月,IB专用
        self.multiplier = EMPTY_STRING  # 乘数,IB专用


class VtCancelOrderReq(object):
    """撤单时传入的对象类"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.symbol = EMPTY_STRING  # 代码
        self.exchange = EMPTY_STRING  # 交易所

        # 以下字段主要和CTP、LTS类接口相关
        self.orderID = EMPTY_STRING  # 报单号
        self.frontID = EMPTY_STRING  # 前置机号
        self.sessionID = EMPTY_STRING  # 会话号


class Portfolio(object):
    """资产的对象类"""

    def __init__(self, account, start_cash=0.00):
        self.account = account                # 资金账号
        # 累计出入金, 比如初始资金1000, 后来转移出去100, 则这个值是1000 - 100
        self.inout_cash = start_cash
        self.available_cash = start_cash      # 可用资金, 可用来购买证券的资金
        self.transferable_cash = start_cash   # 可取资金, 即可以提现的资金, 不包括今日卖出证券所得资金
        self.locked_cash = 0.00               # 挂单锁住资金
        self.margin = 100                     # 保证金，股票、基金保证金都为100 %
        self.long_positions = {}              # 多单的仓位, 一个dict, key是证券代码, value是Position对象
        self.short_positions = {}             # 空单的仓位, 一个dict, key是证券代码, value是Position对象
        self.total_value = start_cash         # 总的权益, 包括现金, 保证金, 仓位的总价值, 可用来计算收益
        self.returns = 0.00                   # 总权益的累计收益
        self.positions_value = 0.00           # 持仓价值, 股票基金才有持仓价值, 期货为0

    @property
    def positions(self):                # 等同于long_positions
        return self.long_positions

    def __str__(self):
        return '资金账号:{0}, 可用资金:{1:.2f}, 总资产:{2:.2f}, 总市值:{3:.2f}'.format(self.account, self.available_cash,
                                                                         self.total_value, self.positions_value)

    def get_all_positions(self):
        return [self.long_positions[x].position() for x in self.long_positions.keys()]

    def calc_total(self):
        """计算市值和总资产"""
        self.total_value = self.available_cash
        self.positions_value = 0.00
        for key in self.long_positions.keys():
            self.total_value += self.long_positions[key].value
            self.positions_value += self.long_positions[key].value

    def update_account(self, zh):
        """更新账户信息"""
        self.available_cash = zh['acct']['zjky']
        for stock in zh['stocks'].keys():
            rec = zh['stocks'][stock]
            if stock in self.long_positions:
                self.long_positions[stock].update(rec)
            else:
                record = Positions(stock, rec[2], rec[0], rec[1])
                self.long_positions[stock] = record

    def update_order(self, order):
        """更新持仓"""
        if order.symbol not in self.long_positions:
            self.long_positions[order.symbol] = Positions(order.symbol)
        value = self.long_positions[order.symbol].update_order(order)
        if value:
            self.available_cash += value

    def update_mkt(self, data):
        """更新价格"""
        stock = data.vtSymbol
        pri = data.lastPrice
        if stock in self.long_positions:
            self.long_positions[stock].update_mkt(pri)

    def set_trade(self, record):
        # 发生委托更新冻结股份或资金
        if record.symbol.strip() in self.long_positions:
            self.long_positions[record.symbol.strip()].set_trade(record)


class Positions(object):
    """仓位的对象类"""

    def __init__(self, stock, name='', vol=0, avg_px=0.00):
        self.security = stock            # 标的代码
        self.name = name
        self.price = avg_px              # 最新行情价格
        # 开仓均价，买入标的的加权平均价, 计算方法是: (buy_volume1_buy_price1
        self.avg_cost = avg_px
        # + buy_volume2_buy_price2 + …) / (buy_volume1 + buy_volume2 + …)
        # 每次买入后会调整avg_cost, 卖出时avg_cost不变.这个值也会被用来计算浮动盈亏.
        self.hold_cost = vol * avg_px    # 持仓成本，针对期货有效。
        self.init_time = localtime()     # 建仓时间，格式为datetime.datetime
        self.transact_time = localtime()  # 最后交易时间，格式为datetime.datetime
        self.total_amount = vol          # 总仓位, 但不包括挂单冻结仓位
        self.closeable_amount = vol      # 可卖出的仓位
        self.today_amount = 0            # 今天开的仓位
        self.locked_amount = 0           # 挂单冻结仓位
        self.value = vol * avg_px        # 标的价值，计算方法是: price * total_amount * multiplier,
        # 其中股票、基金的multiplier为1，期货为相应的合约乘数
        self.is_t0 = False               # 是否T+0

    def __str__(self):
        return '{0}:{1},价格:{2}, 持仓均价:{3}, 可用:{4}, 市值:{5}'.format(self.security, self.name, self.price,
                                                                 self.avg_cost, self.closeable_amount, self.value)

    def update(self, record):
        """更新账户信息"""
        self.total_amount = record[0]
        self.closeable_amount = record[0]
        self.avg_cost = record[1]

        self.value = self.price * self.total_amount

    def update_order(self, order):
        """更新持仓"""
        value = 0
        if self.name == '':
            self.name = order.name
            self.is_t0 = order.is_t0
        if order.tradeside == '2':      # 卖出
            value = order.je
            if order.filled_qty == 0:       # 卖出委托发送
                self.closeable_amount -= order.ord_qty
                self.locked_amount += order.ord_qty
            elif order.cj_je == 0:          # 卖出撤单
                rest_vol = order.ord_qty - order.filled_qty
                self.closeable_amount += rest_vol
                self.locked_amount -= rest_vol
            else:                         # 正常卖出成交
                self.locked_amount -= order.cj_vol
        elif order.tradeside == '1':   # 买入
            if order.can_cancel and order.cj_vol >= 0:  # 正常买入成交
                value = 0
                self.today_amount += order.cj_vol
                if self.is_t0:
                    self.closeable_amount += order.cj_vol
            else:                                  # 买入委托或撤单
                value = order.je
        self.total_amount = self.closeable_amount + self.locked_amount + \
            self.today_amount * (0 if self.is_t0 else 1)
        self.value = self.price * self.total_amount
        return value

    def update_mkt(self, price):
        """更新价格"""
        self.price = price
        self.value = self.price * self.total_amount
        return self.value

    def set_trade(self, record):
        # 发生成交更新冻结股份或资金
        if record.tradeside.strip() == '2':
            self.locked_amount += int(record.ord_qty) - int(record.filled_qty)
        elif record.tradeside.strip() == '1':
            self.today_amount += int(record.filled_qty)

    def position(self):
        # 以字典方式返回持仓
        data = {}
        data['InstrumentID'] = self.security
        data['StockName'] = self.name
        data['Position'] = self.total_amount
        data['PositionCost'] = self.avg_cost
        data['StockValue'] = self.value
        return data


class Order_rec:
    def __init__(self):
        self.inst_type = ''
        self.client_id = 0
        self.acct_type = ''
        self.acct = ''
        self.ord_no = ''
        self.symbol = ''
        self.tradeside = ''
        self.ord_qty = 0
        self.ord_price = 0.0
        self._filled_qty = 0
        self._avg_px = 0.0
        self.ord_type = ''
        self.ord_time = ''
        self.can_cancel = True
        self.name = ''
        self.cj_je = 0.00
        self.cj_vol = 0
        self.is_t0 = False

    @property
    def filled_qty(self):
        return self._filled_qty

    @property
    def avg_px(self):
        return self._avg_px

    @property
    def je(self):
        if self.tradeside == '1' and self.can_cancel and self.cj_je >= 0:
            return 0
        else:
            return self.cj_je * self.cj_vol

    @property
    def vtOrderID(self):
        return str(self.client_id)

    def ord(self):
        return (self.inst_type, self.client_id, self.acct_type, self.acct, self.ord_no, self.symbol,
                self.tradeside, self.ord_qty, self.ord_price, self.ord_type)

    def update_cj(self, fill_qty, avg_px):
        if not self.can_cancel:
            return False
        self.cj_vol = int(fill_qty) - self._filled_qty
        self.cj_je = (float(avg_px) * int(fill_qty) -
                      self._filled_qty * self._avg_px) / self.cj_vol
        self._avg_px = float(avg_px)
        self._filled_qty = int(fill_qty)
        self._avg_px = float(avg_px)
        tmp = self.can_cancel
        if self.ord_qty <= self._filled_qty:
            self.can_cancel = False
        return tmp and not self.can_cancel

    def __str__(self):
        return 'client_id={0}, acct={1}, ord_no={2}, symbol={3}, tradeside={4},' \
               'ord_qty={5}, ord_price={6}, filled_qty={7}, avg_px={8}, je={9}, ' \
               'can_cancel={10}'.format(self.client_id, self.acct, self.ord_no, self.symbol,
                                        self.tradeside, self.ord_qty, self.ord_price, self._filled_qty,
                                        self._avg_px, self.je, self.can_cancel)
