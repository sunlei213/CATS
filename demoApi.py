# encoding: UTF-8

"""
该文件中包含的是交易平台的底层接口相关的部分，
主要对API进行了一定程度的简化封装，方便开发。
"""


from vncast import MdApi, TdApi
from eventEngine import *
from vtobject import VtLogData


# ----------------------------------------------------------------------
def print_dict(d):
    """打印API收到的字典，该函数主要用于开发时的debug"""
    print('-' * 60)
    for key, value in d.items():
        print(key, ':', value)


########################################################################
class DemoMdApi(MdApi):
    """
    Demo中的行情API封装
    封装后所有数据自动推送到事件驱动引擎中，由其负责推送到各个监听该事件的回调函数上
    
    对用户暴露的主动函数包括:
    登陆 login
    订阅合约 subscribe
    """

    # ----------------------------------------------------------------------
    def __init__(self, eventEngine):
        """
        API对象的初始化函数
        """
        super(DemoMdApi, self).__init__()

        # 事件引擎，所有数据都推送到其中，再由事件引擎进行分发
        self.__eventEngine = eventEngine

        # 请求编号，由api负责管理
        self.__reqid = 0

        # 以下变量用于实现连接和重连后的自动登陆
        self.__db_path = {}

        # 以下集合用于重连后自动订阅之前已订阅的合约，使用集合为了防止重复
        self.__setSubscribed = set()

        # 初始化.con文件的保存目录为\mdconnection，注意这个目录必须已存在，否则会报错

    # ----------------------------------------------------------------------
    def on_inited(self):
        """服务器连接"""
        log = VtLogData()
        log.gatewayName = 'CastMdApi'
        log.logContent = u'行情服务器连接成功'
        event = Event(type_=EVENT_LOG)
        event.dict_['log'] = log
        self.__eventEngine.put(event)
        self.start()
        # 如果用户已经填入了用户名等等，则自动尝试连接

    # ----------------------------------------------------------------------
    def on_exited(self):
        """服务器断开"""
        log = VtLogData()
        log.gatewayName = 'CastMdApi'
        log.logContent = u'行情服务器连接断开'
        event = Event(type_=EVENT_LOG)
        event.dict_['log'] = log
        self.__eventEngine.put(event)

    # ----------------------------------------------------------------------
    def onLog(self, log):
        event = Event(type_=EVENT_LOG)
        event.dict_['log'] = log
        self.__eventEngine.put(event)

    # ----------------------------------------------------------------------
    def onError(self, error, n, last):
        """错误回报"""
        log = VtLogData()
        log.gatewayName = 'CastMdApi'
        log.logContent = u'行情错误回报，' + u'错误信息：' + error
        event = Event(type_=EVENT_LOG)
        event.dict_['log'] = log
        self.__eventEngine.put(event)

    # ----------------------------------------------------------------------
    def onRspUserLogin(self, data, error, n, last):
        """登陆回报"""
        event = Event(type_=EVENT_LOG)
        log = VtLogData()
        log.gatewayName = 'CastMdApi'
        if error['ErrorID'] == 0:
            log.logContent = u'行情服务器登陆成功'
        else:
            log.logContent = u'登陆回报，错误代码：' + str(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')

        event.dict_['log'] = log
        self.__eventEngine.put(event)

        # 重连后自动订阅之前已经订阅过的合约
        if self.__setSubscribed:
            for instrument in self.__setSubscribed:
                self.subscribe(instrument[0], instrument[1])

        self.subscribe('510050', 'SSE')

    # ----------------------------------------------------------------------
    def on_get_instrument(self, req, reqID):
        """合约查询回报
        由于该回报的推送速度极快，因此不适合全部存入队列中处理，
        选择先储存在一个本地字典中，全部收集完毕后再推送到队列中
        （由于耗时过长目前使用其他进程读取）"""
        if req['ErrorID'] == 0:
            event = Event(type_=EVENT_INSTRUMENT)
            event.dict_['data'] = req['data']
            event.dict_['last'] = req['last']
            self.__eventEngine.put(event)

        else:
            event = Event(type_=EVENT_LOG)
            log = VtLogData()
            log.gatewayName = 'CastMdApi'
            log.logContent = u'合约投资者回报，错误代码：' + str(req['ErrorID']) + u',' + u'错误信息：' + req['ErrorMsg'].decode('gbk')
            event.dict_['log'] = log
            self.__eventEngine.put(event)

    # ----------------------------------------------------------------------
    def on_send_mkt_data(self, req, reqID):
        """行情推送"""
        # 行情推送收到后，同时触发常规行情事件，以及特定合约行情事件，用于满足不同类型的监听
        data = req['data']
        # 常规行情事件
        if not data:
            return
        event1 = Event(type_=EVENT_MARKETDATA)
        event1.dict_['data'] = data
        self.__eventEngine.put(event1)

        # 特定合约行情事件
        event2 = Event(type_=(EVENT_MARKETDATA_CONTRACT + data['vtSymbol']))
        event2.dict_['data'] = data
        self.__eventEngine.put(event2)

    # ----------------------------------------------------------------------
    def login(self, db_path):
        """连接服务器"""
        self.__db_path = db_path

        # 初始化连接，成功会调用onFrontConnected
        self.init(self.__db_path)

    # ----------------------------------------------------------------------
    def subscribe(self, instrumentid, exchangeid):
        """订阅合约"""
        req = {}
        req['symbol'] = instrumentid
        req['exchange'] = exchangeid
        self.sub_symbol(req)

        instrument = (instrumentid, exchangeid)
        self.__setSubscribed.add(instrument)


########################################################################
class DemoTdApi(TdApi):
    """
    Demo中的交易API封装
    主动函数包括：
    login 登陆
    getInstrument 查询合约信息
    getAccount 查询账号资金
    getInvestor 查询投资者
    getPosition 查询持仓
    sendOrder 发单
    cancelOrder 撤单
    """

    # ----------------------------------------------------------------------
    def __init__(self, eventEngine):
        """API对象的初始化函数"""
        super(DemoTdApi, self).__init__()

        # 事件引擎，所有数据都推送到其中，再由事件引擎进行分发
        self.__eventEngine = eventEngine

        # 请求编号，由api负责管理
        self.__reqid = 0

        # 报单编号，由api负责管理
        self.__orderref = 0

        # 以下变量用于实现连接和重连后的自动登陆
        self.__db_path = {}

        # 合约字典（保存合约查询数据）
        self.__dictInstrument = {}

        # 查询账户计时数
        self.__query_tick = 0

        # 初始化.con文件的保存目录为\tdconnection

    # ----------------------------------------------------------------------
    def on_inited(self):
        """服务器连接"""
        log = VtLogData()
        log.gatewayName = 'CastTdApi'
        log.logContent = u'交易服务器连接成功'
        event = Event(type_=EVENT_LOG)
        event.dict_['log'] = log
        self.__eventEngine.put(event)

        # 如果用户已经填入了用户名等等，则自动尝试连接
        self.__eventEngine.register(EVENT_TIMER, self.req_query_acc)
        log = VtLogData()
        log.gatewayName = 'CastTdApi'
        log.logContent = u'交易服务器登陆成功'
        event = Event(type_=EVENT_LOG)
        event.dict_['log'] = log
        self.__eventEngine.put(event)
        event2 = Event(type_=EVENT_TDLOGIN)
        self.__eventEngine.put(event2)
        for key in self._cj_list.keys():
            rec = self._cj_list[key]
            event = Event(type_=EVENT_ORDER + 'start')
            event.dict_['data'] = rec
            self.__eventEngine.put(event)

    # ----------------------------------------------------------------------
    def on_exited(self):
        """服务器断开"""
        log = VtLogData()
        log.gatewayName = 'CastTdApi'
        log.logContent = u'交易服务器连接断开'
        event = Event(type_=EVENT_LOG)
        event.dict_['log'] = log
        self.__eventEngine.put(event)

    # ----------------------------------------------------------------------
    def onError(self, error, n, last):
        """错误回报"""
        log = VtLogData()
        log.gatewayName = 'CastTdApi'
        log.logContent = u'交易错误回报，' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        event = Event(type_=EVENT_LOG)
        event.dict_['log'] = log
        self.__eventEngine.put(event)

    # ----------------------------------------------------------------------
    def onRspUserLogin(self, data, error, n, last):
        """登陆回报"""
        event = Event(type_=EVENT_LOG)
        log = VtLogData()
        log.gatewayName = 'CastTdApi'

        if error['ErrorID'] == 0:
            log.logContent = u'交易服务器登陆成功'
        else:
            log.logContent = u'登陆回报，错误代码：' + str(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')

        event.dict_['log'] = log
        self.__eventEngine.put(event)

        event2 = Event(type_=EVENT_TDLOGIN)
        self.__eventEngine.put(event2)

    # ---------------------------------------------------------------------
    def push_zh(self):
        """更新账户"""
        event = Event(type_=(EVENT_ACCOUNT + 'data'))
        event.dict_['data'] = self._zh_list
        self.__eventEngine.put(event)

    # ----------------------------------------------------------------------
    def onRspUserLogout(self, data, error, n, last):
        """登出回报"""
        event = Event(type_=EVENT_LOG)
        log = VtLogData()
        log.gatewayName = 'CastTdApi'

        if error['ErrorID'] == 0:
            log.logContent = u'交易服务器登出成功'
        else:
            log.logContent = u'登出回报，错误代码：' + str(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')

        event.dict_['log'] = log
        self.__eventEngine.put(event)

    # ----------------------------------------------------------------------
    def onRspQryInstrument(self, data, error, n, last):
        """
        合约查询回报
        由于该回报的推送速度极快，因此不适合全部存入队列中处理，
        选择先储存在一个本地字典中，全部收集完毕后再推送到队列中
        （由于耗时过长目前使用其他进程读取）
        """
        if error['ErrorID'] == 0:
            event = Event(type_=EVENT_INSTRUMENT)
            event.dict_['data'] = data
            event.dict_['last'] = last
            self.__eventEngine.put(event)
        else:
            event = Event(type_=EVENT_LOG)
            log = VtLogData()
            log.gatewayName = 'CastTdApi'
            log.logContent = u'合约投资者回报，错误代码：' + str(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode(
                'gbk')
            event.dict_['log'] = log
            self.__eventEngine.put(event)

            # ----------------------------------------------------------------------

    def onRspQryInvestor(self, data, error, n, last):
        """投资者查询回报"""
        if error['ErrorID'] == 0:
            event = Event(type_=EVENT_INVESTOR)
            event.dict_['data'] = data
            self.__eventEngine.put(event)
        else:
            event = Event(type_=EVENT_LOG)
            log = VtLogData()
            log.gatewayName = 'CastTdApi'
            log.logContent = u'合约投资者回报，错误代码：' + str(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode(
                'gbk')
            event.dict_['log'] = log
            self.__eventEngine.put(event)

    # ----------------------------------------------------------------------
    def onRspQryTradingAccount(self, req, req_id):
        """资金账户查询回报"""
        if req['ErrorID'] == 0:
            event = Event(type_=EVENT_ACCOUNT)
            event.dict_['data'] = req['data']
            self.__eventEngine.put(event)
        else:
            event = Event(type_=EVENT_LOG)
            log = VtLogData()
            log.gatewayName = 'CastTdApi'
            log.logContent = u'账户查询回报，错误代码：' + str(req['ErrorID']) + u',' + u'错误信息：' + req['ErrorMsg'].decode('gbk')
            event.dict_['log'] = log
            self.__eventEngine.put(event)

    # ----------------------------------------------------------------------
    def onRspQryInvestorPosition(self, req, req_id):
        """持仓查询回报"""
        if req['ErrorID'] == 0:
            event = Event(type_=EVENT_POSITION)
            event.dict_['data'] = req['data']
            self.__eventEngine.put(event)
        else:
            event = Event(type_=EVENT_LOG)
            log = VtLogData()
            log.gatewayName = 'CastTdApi'
            log.logContent = u'持仓查询回报，错误代码：' + str(req['ErrorID']) + u',' + u'错误信息：' + req['ErrorMsg'].decode('gbk')
            event.dict_['log'] = log
            self.__eventEngine.put(event)

    # ----------------------------------------------------------------------
    def on_order(self, req, reqID):
        """报单回报"""
        # 更新最大报单编号
        rec = req['data']
        self.__query_tick = 0

        # 常规报单事件
        event1 = Event(type_=EVENT_ORDER)
        event1.dict_['data'] = rec
        event1.dict_['func'] = req['func']
        self.__eventEngine.put(event1)

        # 特定合约行情事件
        event2 = Event(type_=(EVENT_ORDER_ORDERREF + str(rec.client_id)))
        event2.dict_['data'] = rec
        self.__eventEngine.put(event2)

    def on_cj_update(self):
        self.__query_tick = 0

    # ----------------------------------------------------------------------
    def on_trade(self, req, reqID):
        """成交回报"""
        # 常规成交事件
        event1 = Event(type_=EVENT_TRADE)
        event1.dict_['data'] = req['data']
        self.__eventEngine.put(event1)

        event = Event(type_=(EVENT_TRADE + 'data'))
        event.dict_['data'] = req['data']
        self.__eventEngine.put(event)

        # 特定合约成交事件
        event2 = Event(type_=(EVENT_TRADE_CONTRACT + str(req.client_id)))
        event2.dict_['data'] = req['data']
        self.__eventEngine.put(event2)

    # ----------------------------------------------------------------------
    def onErrRtnOrderInsert(self, data, error):
        """发单错误回报（交易所）"""
        event = Event(type_=EVENT_LOG)
        log = VtLogData()
        log.gatewayName = 'CastTdApi'
        log.logContent = u'发单错误回报，错误代码：' + str(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        event.dict_['log'] = log
        self.__eventEngine.put(event)

    # ----------------------------------------------------------------------
    def onErrRtnOrderAction(self, data, error):
        """撤单错误回报（交易所）"""
        event = Event(type_=EVENT_LOG)
        log = VtLogData()
        log.gatewayName = 'CastTdApi'
        log.logContent = u'撤单错误回报，错误代码：' + str(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        event.dict_['log'] = log
        self.__eventEngine.put(event)

    # ----------------------------------------------------------------------
    def login(self, db_path):
        """连接服务器"""
        self.__db_path = db_path

        # 初始化连接，成功会调用onFrontConnected
        self.init(self.__db_path)

    # ----------------------------------------------------------------------
    def req_query_acc(self, event):
        """发送账户查询请求"""
        self.__query_tick += 1
        if self.__query_tick == 20:
            req = {}
            req['reqID'] = True
            req['callback'] = self.query_acc
            self.reqQueue.put(req)
            self.__query_tick = 0

    # ----------------------------------------------------------------------
    def getAccount(self):
        """查询账户"""
        self.reqQryTradingAccount()

    # ----------------------------------------------------------------------
    def getPosition(self):
        """查询持仓"""

        self.reqQryInvestorPosition()

    # ----------------------------------------------------------------------
    def sendOrder(self, instrumentid, exchangeid, price, pricetype, volume, direction):
        """发单"""
        self.__reqid = self.__reqid + 1
        req = {}

        req['stock'] = instrumentid
        req['exchangeid'] = exchangeid
        req['pricetype'] = pricetype
        req['price'] = price
        req['volume'] = volume
        req['direction'] = direction

        req['MinVolume'] = 1  # 最小成交量为1

        self.__orderref = self.order(req, self.__reqid)

        # 返回订单号，便于某些算法进行动态管理
        return self.__orderref

    # ----------------------------------------------------------------------
    def cancelOrder(self, orderref):
        """撤单"""
        self.__reqid = self.__reqid + 1
        req = {}

        req['orderid'] = orderref

        self.cancel_order(req, self.__reqid)
