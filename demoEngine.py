# encoding: UTF-8

"""
该文件中包含的是交易平台的中间层，
将API和事件引擎包装到一个主引擎类中，便于管理。

当客户想采用服务器-客户机模式，实现交易功能放在托管机房，
而图形控制功能在本地电脑时，该主引擎负责实现远程通讯。
"""

import sys
from datetime import date

import shelve

from collections import OrderedDict
from vtobject import * 
from demoApi import *
from eventEngine import EventEngine


########################################################################
class MainEngine:
    """主引擎，负责对API的调度"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.eventEngine = EventEngine()         # 创建事件驱动引擎
        
        self.md = DemoMdApi(self.eventEngine)    # 创建API接口
        #self.md = DemoL2Api(self.ee)   # 如果使用L2行情就改为这行
        self.td = DemoTdApi(self.eventEngine)
        
        self.eventEngine.start()                 # 启动事件驱动引擎
        self.dataEngine = DataEngine(self, self.eventEngine)
        
        # 循环查询持仓和账户相关
        self.countGet = 0               # 查询延时计数
        self.lastGet = 'Account'        # 上次查询的性质
        self.eventEngine.register(EVENT_TDLOGIN, self.initGet)  # 登录成功后开始初始化查询
        
        # 合约储存相关
        #self.dictInstrument = {}        # 字典（保存合约查询数据）
        #self.eventEngine.register(EVENT_INSTRUMENT, self.insertInstrument)
        # 接口实例
        self.gatewayDict = OrderedDict()
        self.gatewayDetailList = []

        # 应用模块实例
        self.appDict = OrderedDict()
        self.appDetailList = []

        # 风控引擎实例（特殊独立对象）
        self.rmEngine = None

    # ----------------------------------------------------------------------
    def addGateway(self, gatewayModule):
        """添加底层接口"""
        gatewayName = gatewayModule.gatewayName

        # 创建接口实例
        self.gatewayDict[gatewayName] = gatewayModule.gatewayClass(self.eventEngine,
                                                                   gatewayName)

        # 设置接口轮询
        if gatewayModule.gatewayQryEnabled:
            self.gatewayDict[gatewayName].setQryEnabled(gatewayModule.gatewayQryEnabled)

        # 保存接口详细信息
        d = {
            'gatewayName': gatewayModule.gatewayName,
            'gatewayDisplayName': gatewayModule.gatewayDisplayName,
            'gatewayType': gatewayModule.gatewayType
        }
        self.gatewayDetailList.append(d)

    # ----------------------------------------------------------------------
    def addApp(self, appModule):
        """添加上层应用"""
        appName = appModule.appName

        # 创建应用实例
        self.appDict[appName] = appModule.appEngine(self, self.eventEngine)

        # 保存应用信息
        d = {
            'appName': appModule.appName,
            'appDisplayName': appModule.appDisplayName,
            'appWidget': appModule.appWidget,
            'appIco': appModule.appIco
        }
        self.appDetailList.append(d)

    # ----------------------------------------------------------------------
    def getGateway(self, gatewayName):
        """获取接口"""
        if gatewayName in self.gatewayDict:
            return self.gatewayDict[gatewayName]
        else:
            self.writeLog('{gateway}接口不存在'.format(gateway=gatewayName))
            return None

    # ----------------------------------------------------------------------
    def writeLog(self, content):
        """快速发出日志事件"""
        log = VtLogData()
        log.logContent = content
        event = Event(type_=EVENT_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)

    # ----------------------------------------------------------------------
    def connect(self, gatewayName):
        """连接特定名称的接口"""
        gateway = self.getGateway(gatewayName)

        if gateway:
            gateway.connect()

    #----------------------------------------------------------------------
    def login(self, userid, mdPassword, tdPassword, mdAddress, tdAddress):
        """登陆"""
        db_path = {}
        db_path['SH'] = userid
        db_path['SZ'] = mdPassword
        db_path['Order'] = tdPassword
        db_path['HB'] = mdAddress
        db_path['Acct'] = tdAddress
        print(db_path)
        self.md.login(db_path)
        self.td.login(db_path)
    
    #----------------------------------------------------------------------
    def subscribe(self, instrumentid, exchangeid):
        """订阅合约"""
        self.md.subscribe(instrumentid, exchangeid)
        
    #----------------------------------------------------------------------
    def getAccount(self):
        """查询账户"""
        self.dataEngine.getAccount()

    #----------------------------------------------------------------------
    def getPosition(self):
        """查询持仓"""
        self.dataEngine.getPosition()
    
    #----------------------------------------------------------------------
    def getInstrument(self):
        """获取合约"""
        event = Event(type_=EVENT_LOG)
        log = VtLogData()
        log.gatewayName = 'MainEngine'
        log.logContent = u'查询合约信息'
        event.dict_['log'] = log
        self.eventEngine.put(event)
        
        self.md.getInstrument()
        
    #----------------------------------------------------------------------
    def sendOrder(self, instrumentid, exchangeid, price, pricetype, volume, direction):
        """发单"""
        self.td.sendOrder(instrumentid, exchangeid, price, pricetype, volume, direction)
        
    #----------------------------------------------------------------------
    def cancelOrder(self, orderref):
        """撤单"""

        self.td.cancelOrder(orderref)
        
    #----------------------------------------------------------------------
    def getAccountPosition(self, event):
        """循环查询账户和持仓"""
        self.countGet = self.countGet + 1
        
        # 每5秒发一次查询
        if self.countGet > 5:
            self.countGet = 0   # 清空计数
            
            if self.lastGet == 'Account':
                self.getPosition()
                self.lastGet = 'Position'
            else:
                self.getAccount()
                self.lastGet = 'Account'
    
    #----------------------------------------------------------------------
    def initGet(self, event):
        """在交易服务器登录成功后，开始初始化查询"""
        # 打开设定文件setting.vn
        if self.dataEngine.no_data:
            self.getInstrument()
        self.getAccount()
        self.getPosition()
        self.eventEngine.register(EVENT_TIMER, self.getAccountPosition)
 
    #----------------------------------------------------------------------
    def selectInstrument(self, instrumentid):
        """获取合约信息对象"""
        return self.dataEngine.getContract(instrumentid)
    
    #----------------------------------------------------------------------
    def exit(self):
        """退出"""
        # 销毁API对象
        self.td.exit()
        self.md.exit()
        self.td = None
        self.md = None
        
        # 停止事件驱动引擎
        self.eventEngine.stop()
        
    # ----------------------------------------------------------------------
    def getAllContracts(self):
        """查询所有合约（返回列表）"""
        return self.dataEngine.getAllContracts()

    # ----------------------------------------------------------------------
    def getOrder(self, vtOrderID):
        """查询委托"""
        return self.dataEngine.getOrder(vtOrderID)

    # ----------------------------------------------------------------------
    def getAllWorkingOrders(self):
        """查询所有的活跃的委托（返回列表）"""
        return self.dataEngine.getAllWorkingOrders()

    # ----------------------------------------------------------------------
    def getAllGatewayDetails(self):
        """查询引擎中所有底层接口的信息"""
        return self.gatewayDetailList

    # ----------------------------------------------------------------------
    def getAllAppDetails(self):
        """查询引擎中所有上层应用的信息"""
        return self.appDetailList


class DataEngine(object):
    """数据引擎"""
    contractFileName = 'ContractData.vt'

    # ----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        self.eventEngine = eventEngine
        self.mainEngine = mainEngine

        # 保存合约详细信息的字典
        self.contractDict = {}

        # 保存委托数据的字典
        self.orderDict = {}

        # 保存账户持仓字典
        self.accountDict = {}
        self.stockDict = {}
        self.Portfolio = {}

        # 保存活动委托数据的字典（即可撤销）
        self.workingOrderDict = {}

        # 读取保存在硬盘的合约数据
        self.no_data = self.loadContracts()

        # 注册事件监听
        self.registerEvent()

    # ----------------------------------------------------------------------
    def updateContract(self, event):
        """更新合约数据"""
        contract = event.dict_['data']
        last = event.dict_['last']

        # 合约对象查询完成后，查询投资者信息并开始循环查询
        if last:
            # 将查询完成的合约信息保存到本地文件，今日登录可直接使用不再查询
            self.saveContracts()

            event = Event(type_=EVENT_LOG)
            log = VtLogData()
            log.gatewayName = 'MainEngine'
            log.logContent = u'合约信息查询完成'
            event.dict_['log'] = log
            self.eventEngine.put(event)
        else:
            self.contractDict[contract.vtSymbol] = contract

    # ----------------------------------------------------------------------
    def update_acc(self,event):
        data = event.dict_['data']
        sub_stocks = set()
        print(data)
        for acc in data.keys():
            self.accountDict[acc] = data[acc]['acct']
            self.stockDict[acc] = data[acc]['stocks']

            if acc not in self.Portfolio:
                self.Portfolio[acc] = Portfolio(acc)
            self.Portfolio[acc].update_account(data[acc])
            for stock in self.Portfolio[acc].long_positions.keys():
                sub_stocks.add(stock)

            for stock in self.stockDict[acc].keys():
                sub_stocks.add(stock)
        for stock in sub_stocks:
            self.mainEngine.subscribe(stock[:6],stock[-2:])

        # ----------------------------------------------------------------------
    def update_trade(self, event):
        d = event.dict_['data']
        if d['Direction'] == '1':
            stocks = self.stockDict.get(d['ExchangeInstID'], {})
            if d['InstrumentID'] in stocks:
                vol = stocks[d['InstrumentID']][0]
                pri = stocks[d['InstrumentID']][1]
                stocks[d['InstrumentID']][0] += d['Volume']
                stocks[d['InstrumentID']][1] = (vol * pri + d['Volume'] * d['Price']) / (vol + d['Volume'])
            else:
                stocks[d['InstrumentID']] = [d['Volume'],  d['Price'], '', d['Volume'] * d['Price']]
            self.stockDict[d['ExchangeInstID']] = stocks
        elif d['Direction'] == '2':
            acct = self.accountDict[d['ExchangeInstID']]
            acct['zjky'] += d['Volume'] * d['Price']
            self.accountDict[d['ExchangeInstID']] = acct

    def sum_zc(self, acc):
        zzc = self.accountDict[acc]['zjky']
        for key in self.stockDict[acc].keys():
            zzc += self.stockDict[acc][key][3]
        self.accountDict[acc]['zzc'] = zzc

    def update_mkt_data(self, event):
        d = event.dict_['data']


        for key in self.Portfolio.keys():
            self.Portfolio[key].update_mkt(d)


    # ----------------------------------------------------------------------
    def getContract(self, vtSymbol):
        """查询合约对象"""
        try:
            return self.contractDict[vtSymbol]
        except KeyError:
            return None

    # ----------------------------------------------------------------------
    def getAllContracts(self):
        """查询所有合约对象（返回列表）"""
        return self.contractDict.values()

    # ----------------------------------------------------------------------
    def saveContracts(self):
        """保存所有合约对象到硬盘"""
        f = shelve.open(self.contractFileName)
        d = {}
        d['date'] = date.today()
        d['contract'] = self.contractDict
        f['data'] = d
        f.close()

    # ----------------------------------------------------------------------
    def loadContracts(self):
        """从硬盘读取合约对象"""
        f = shelve.open(self.contractFileName)
        no_data =True
        if 'data' in f:
            data = f['data']
            if 'date' in data:
                if data['date'] == date.today():
                    d = data['contract']
                    for key, value in d.items():
                        self.contractDict[key] = value
                    no_data = False
        f.close()
        return no_data

    # ----------------------------------------------------------------------
    def updateOrder(self, event):
        """更新委托数据"""
        order = event.dict_['data']
        self.orderDict[order.vtOrderID] = order

        # 如果订单的状态是全部成交或者撤销，则需要从workingOrderDict中移除
        if not order.can_cancel:
            if order.vtOrderID in self.workingOrderDict:
                del self.workingOrderDict[order.vtOrderID]
        # 否则则更新字典中的数据
        else:
            self.workingOrderDict[order.vtOrderID] = order
        if order.tradeside.strip() == '1':
            self.accountDict[order.acct]['zjky'] += order.je
        elif order.tradeside.strip() == '2':
            self.stockDict[order.acct][order.symbol][0] -= order.ord_qty

        if order.acct.strip() in self.Portfolio:
            stock = self.getContract(order.symbol)
            if stock:
                order.name = stock.name
                order.is_t0 = order.is_t0
            self.Portfolio[order.acct.strip()].update_order(order)

    def start_ord(self, event):
        trade = event.dict_['data']
        if int(trade.filled_qty) > 0:
            if trade.acct.strip() in self.Portfolio:
                self.Portfolio[trade.acct.strip()].set_trade(trade)

    # ----------------------------------------------------------------------
    def getOrder(self, vtOrderID):
        """查询委托"""
        try:
            return self.orderDict[vtOrderID]
        except KeyError:
            return None

    # ----------------------------------------------------------------------
    def getAllWorkingOrders(self):
        """查询所有活动委托（返回列表）"""
        return self.workingOrderDict.values()

    #----------------------------------------------------------------------
    def getAccount(self):
        """查询账户"""
        acc = '无'
        try:
            for acc in self.accountDict.keys():
                self.sum_zc(acc)
                data = {}
                data['AccountID'] = acc
                data['Available'] = self.accountDict[acc]['zjky']
                data['CurrMargin'] = self.accountDict[acc]['zzc']
                event = Event(type_=EVENT_ACCOUNT)
                event.dict_['data'] = data
                self.eventEngine.put(event)
        except KeyError as e:
            event = Event(type_=EVENT_LOG)
            log = VtLogData()
            log.gatewayName = 'dataEngine'
            log.logContent = u'账户查询回报，错误账户：' + acc + u',' + u'错误信息：' + str(e)
            event.dict_['log'] = log
            self.eventEngine.put(event)
        for key in self.Portfolio.keys():
            self.Portfolio[key].calc_total()
            print(self.Portfolio[key])

    #----------------------------------------------------------------------
    def getPosition(self):
        """查询持仓"""
        acc = '无'
        try:
            for acc in self.stockDict.keys():
                for stock in self.stockDict[acc].keys():
                    data = {}
                    data['AccountID'] = acc
                    data['InstrumentID'] = stock
                    data['StockName'] = self.stockDict[acc][stock][2]
                    data['Position'] = self.stockDict[acc][stock][0]
                    data['PositionCost'] = self.stockDict[acc][stock][1]
                    data['StockValue'] = self.stockDict[acc][stock][3]
                    event = Event(type_=EVENT_POSITION)
                    event.dict_['data'] = data
                    self.eventEngine.put(event)
        except KeyError as e:
            event = Event(type_=EVENT_LOG)
            log = VtLogData()
            log.gatewayName = 'dataEngine'
            log.logContent = u'账户查询回报，错误账户：' + acc + u',' + u'错误信息：' + str(e)
            event.dict_['log'] = log
            self.eventEngine.put(event)
        for key in self.Portfolio.keys():
            self.Portfolio[key].calc_total()
            print(self.Portfolio[key].get_all_positions())

    # ----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_INSTRUMENT, self.updateContract)
        self.eventEngine.register(EVENT_ORDER, self.updateOrder)
        self.eventEngine.register(EVENT_MARKETDATA, self.update_mkt_data)
        self.eventEngine.register((EVENT_ACCOUNT+'data'), self.update_acc)
        self.eventEngine.register((EVENT_TRADE + 'data'), self.update_trade)
        self.eventEngine.register((EVENT_ORDER + 'start'), self.start_ord)
