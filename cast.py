# -*- coding: utf-8 -*-
"""
Created on Wed Aug 30 09:09:35 2017

@author: sunlei
"""
from queue import Queue, Empty
from threading import Thread
from time import sleep
from collections import defaultdict, namedtuple, OrderedDict
import dbf
from math import ceil
from PyQt5.QtCore import QTimer
from datetime import datetime
import msvcrt
import json

# 系统相关
EVENT_TIMER = 'eTimer'  # 计时器事件，每隔1秒发送一次
EVENT_LOG = 'eLog'  # 日志事件，全局通用

# Gateway相关
EVENT_TICK = 'eTick.'  # TICK行情事件，可后接具体的vtSymbol
EVENT_TRADE = 'eTrade.'  # 成交回报事件
EVENT_ORDER = 'eOrder.'  # 报单回报事件
EVENT_POSITION = 'ePosition.'  # 持仓回报事件
EVENT_ACCOUNT = 'eAccount.'  # 账户回报事件
EVENT_CONTRACT = 'eContract.'  # 合约基础信息回报事件
EVENT_ERROR = 'eError.'  # 错误回报事件
Order_rec = namedtuple('Order_rec', ['inst_type', 'client_id', 'acct_type', 'acct',
                                     'ord_no', 'symbol', 'tradeside', 'ord_qty', 'ord_price',
                                     'ord_type'])


########################################################################
class EventEngine(object):
    """
    事件驱动引擎
    事件驱动引擎中所有的变量都设置为了私有，这是为了防止不小心
    从外部修改了这些变量的值或状态，导致bug。

    变量说明
    __queue：私有变量，事件队列
    __active：私有变量，事件引擎开关
    __thread：私有变量，事件处理线程
    __timer：私有变量，计时器
    __handlers：私有变量，事件处理函数字典


    方法说明
    __run: 私有方法，事件处理线程连续运行用
    __process: 私有方法，处理事件，调用注册在引擎中的监听函数
    __onTimer：私有方法，计时器固定事件间隔触发后，向事件队列中存入计时器事件
    start: 公共方法，启动引擎
    stop：公共方法，停止引擎
    register：公共方法，向引擎中注册监听函数
    unregister：公共方法，向引擎中注销监听函数
    put：公共方法，向事件队列中存入新的事件

    事件监听函数必须定义为输入参数仅为一个event对象，即：

    函数
    def func(event)
        ...

    对象方法
    def method(self, event)
        ...

    """

    # ----------------------------------------------------------------------
    def __init__(self):
        """初始化事件引擎"""
        # 事件队列
        self.__queue = Queue()

        # 事件引擎开关
        self.__active = False

        # 事件处理线程
        self.__thread = Thread(target=self.__run)

        # 计时器，用于触发计时器事件
        # self.__timer = QTimer()
        # self.__timer.timeout.connect(self.__onTimer)
        self.__timer = Thread(target=self.__onTimer)
        self.__timeout = 1.0  # 延迟1秒
        # 这里的__handlers是一个字典，用来保存对应的事件调用关系
        # 其中每个键对应的值是一个列表，列表中保存了对该事件进行监听的函数功能
        self.__handlers = defaultdict(list)

        # __generalHandlers是一个列表，用来保存通用回调函数（所有事件均调用）
        self.__generalHandlers = []

    # ----------------------------------------------------------------------
    def __run(self):
        """引擎运行"""
        while self.__active:
            try:
                event = self.__queue.get(
                    block=True, timeout=1)  # 获取事件的阻塞时间设为1秒
                self.__process(event)
            except Empty:
                pass

    # ----------------------------------------------------------------------
    def __process(self, event):
        """处理事件"""
        # 检查是否存在对该事件进行监听的处理函数
        if event.type_ in self.__handlers:
            # 若存在，则按顺序将事件传递给处理函数执行
            [handler(event) for handler in self.__handlers[event.type_]]

            # 以上语句为Python列表解析方式的写法，对应的常规循环写法为：
            # for handler in self.__handlers[event.type_]:
            # handler(event)

        # 调用通用处理函数进行处理
        if self.__generalHandlers:
            [handler(event) for handler in self.__generalHandlers]

    # ----------------------------------------------------------------------
    def __onTimer(self):
        """向事件队列中存入计时器事件"""
        while self.__active:
            # 创建计时器事件
            sleep(self.__timeout)
            event = Event(type_=EVENT_TIMER)

            # 向队列中存入计时器事件
            self.put(event)

            # ----------------------------------------------------------------------

    def start(self, timer=True):
        """
        引擎启动
        timer：是否要启动计时器
        """
        # 将引擎设为启动
        self.__active = True

        # 启动事件处理线程
        self.__thread.start()

        # 启动计时器，计时器事件间隔默认设定为1秒
        if timer:
            self.__timer.start()
            # self.__timer.start(1000)

    # ----------------------------------------------------------------------
    def stop(self):
        """停止引擎"""
        # 将引擎设为停止
        self.__active = False

        # 停止计时器
        # self.__timer.stop()
        self.__timer.join()

        # 等待事件处理线程退出
        self.__thread.join()

    # ----------------------------------------------------------------------
    def register(self, type_, handler):
        """注册事件处理函数监听"""
        # 尝试获取该事件类型对应的处理函数列表，若无defaultDict会自动创建新的list
        handler_list = self.__handlers[type_]

        # 若要注册的处理器不在该事件的处理器列表中，则注册该事件
        if handler not in handler_list:
            handler_list.append(handler)

    # ----------------------------------------------------------------------
    def unregister(self, type_, handler):
        """注销事件处理函数监听"""
        # 尝试获取该事件类型对应的处理函数列表，若无则忽略该次注销请求
        handler_list = self.__handlers[type_]

        # 如果该函数存在于列表中，则移除
        if handler in handler_list:
            handler_list.remove(handler)

        # 如果函数列表为空，则从引擎中移除该事件类型
        if not handler_list:
            del self.__handlers[type_]

    # ----------------------------------------------------------------------
    def put(self, event):
        """向事件队列中存入事件"""
        self.__queue.put(event)

    # ----------------------------------------------------------------------
    def registerGeneralHandler(self, handler):
        """注册通用事件处理函数监听"""
        if handler not in self.__generalHandlers:
            self.__generalHandlers.append(handler)

    # ----------------------------------------------------------------------
    def unregisterGeneralHandler(self, handler):
        """注销通用事件处理函数监听"""
        if handler in self.__generalHandlers:
            self.__generalHandlers.remove(handler)


########################################################################
class Event:
    """事件对象"""

    # ----------------------------------------------------------------------
    def __init__(self, type_=None):
        """Constructor"""
        self.type_ = type_  # 事件类型
        self.dict_ = {}  # 字典用于保存具体的事件数据


class CastMid(object):  # 资产订单处理类
    def __init__(self, engine=None):
        self.tables = {'hq': r'z:\remote\dbf\show2003.dbf',
                       'wt': r'd:\cast\instructions.dbf',
                       'hb': r'd:\cast\order_updates.dbf',
                       'zh': r'd:\cast\asset.dbf'}
        self._wt_list = OrderedDict()
        self._cj_num = 0
        self._client_id = 1000
        self._zh_list = {}
        self._hq_db = None
        self._ord_db = None
        self._hb_db = None
        self._zh_db = None
        self._ee = engine
        self._time_tick = 0

        if self._ee:
            self._ee.register(EVENT_TIMER, self._on_get_cj)

    def start(self):
        self._hq_db = dbf.Table(self.tables['hq'])
        self._ord_db = dbf.Table(self.tables['wt'])
        self._hb_db = dbf.Table(self.tables['hb'])
        self._zh_db = dbf.Table(self.tables['zh'])
        self._zh_db.open()
        for rec in self._zh_db:
            if rec.acct.strip() in self._zh_list:
                asset = self._zh_list[rec.acct.strip()]
            else:
                asset = {'zjky': 0.0}
            if rec.a_type.strip() == 'F':
                asset['zjky'] = float(rec.s4)
            else:
                asset[rec.s1.strip()] = [int(rec.s3), float(rec.s4)]
            self._zh_list[rec.acct.strip()] = asset
        self._zh_db.close()
        self._client_id += self._get_wt()
        self._get_cj(False)
        print(self._zh_list)

    def get_price(self, stocks):
        self._hq_db.open()
        sell = {}
        buy = {}
        for stock in stocks:
            try:
                recodes = self._hq_db.query(
                    'select * where s1=="{}"'.format(stock))
            except:
                recodes = []
            if len(recodes):
                sell[stock] = (recodes[0].s10, recodes[0].s21, recodes[0].s22,
                               recodes[0].s23, recodes[0].s24, recodes[0].s25)
                buy[stock] = (recodes[0].s9, recodes[0].s15, recodes[0].s16,
                              recodes[0].s17, recodes[0].s18, recodes[0].s19)
        self._hq_db.close()
        return buy, sell

    def get_can_cancel(self):
        keys = tuple(self._wt_list.keys())
        can_cancel = {}
        for key in keys:
            if self._wt_list[key][5]:
                can_cancel[key] = self._wt_list[key]
        return can_cancel

    def get_zc(self, exchangeid):
        return self._zh_list[exchangeid]

    @property
    def get_zh_list(self):
        return tuple(self._zh_list.keys())

    @property
    def get_wt_list(self):
        return self._wt_list

    def order(self, exchangeid, stock, price, pricetype, volume, direction):
        rec = Order_rec('O', self._client_id, 'S0', exchangeid,
                        '', stock, direction, volume, price, pricetype)
        je = price * volume
        if direction.strip() == '1':
            self._zh_list[exchangeid]['zjky'] -= je
        elif direction.strip() == '2':
            self._zh_list[exchangeid][stock][0] -= volume
            je = 0.0
        self._wt_list[str(self._client_id)] = [rec, '', 0, 0.0, je, True]
        self._ord_db.open()
        self._ord_db.append(rec)
        self._ord_db.close()
        self._client_id += 1
        return self._client_id - 1

    def cancel_order(self, exchangeid, orderid):
        rec = Order_rec('C', self._client_id, 'S0', exchangeid,
                        orderid, '', '', 0, 0.0, '')
        self._wt_list[str(self._client_id)] = [rec, '', 0, 0.0, 0.0, False]
        self._ord_db.open()
        self._ord_db.append(rec)
        self._ord_db.close()
        self._client_id += 1
        for cl_id in self._wt_list.keys():
            rec1 = self._wt_list[cl_id][0]
            if self._wt_list[cl_id][5] and self._wt_list[cl_id][1] == rec.ord_no.strip():
                self._wt_list[cl_id][5] = False
                if rec1.tradeside == '1':
                    self._zh_list[rec1.acct]['zjky'] += self._wt_list[cl_id][4]
                if rec1.tradeside == '2':
                    self._zh_list[rec1.acct][rec1.symbol][0] += (
                        rec1.ord_qty - self._wt_list[cl_id][2])
        event = Event(EVENT_TRADE)
        self._ee.put(event)

    def _on_get_cj(self, event):
        self._time_tick += 1
        # print(self._time_tick)
        if self._time_tick >= 2:
            self._time_tick = 0
            self._get_cj()

    def _get_cj(self, normal=True):
        self._hb_db.open()
        cj_list = [rec for rec in self._hb_db]
        self._hb_db.close()
        if self._cj_num == len(cj_list):
            return
        for i in range(self._cj_num, len(cj_list)):
            rec = cj_list[i]
            if len(rec.client_id.strip()):
                if len(rec.err_msg.strip()):
                    self._wt_err(rec, normal)
                else:
                    client_id = rec.client_id.strip()
                    self._wt_list[client_id][1] = rec.ord_no.strip()
                    if self._wt_list[client_id][0].inst_type == 'C':
                        self._wt_cancel(rec, normal)
                    else:
                        if rec.tradeside.strip() == '1':
                            self._wt_buy(rec, normal)
                        if rec.tradeside.strip() == '2':
                            self._wt_sell(rec, normal)
            self._cj_num += 1
        if normal:
            event = Event(EVENT_TRADE)
            self._ee.put(event)

    def _wt_cancel(self, rec, normal=True):
        cl_id = rec.client_id.strip()
        ord_no = self._wt_list[cl_id][0].ord_no
        for cl_id in self._wt_list.keys():
            # print(self._wt_list[cl_id],ord_no)
            if self._wt_list[cl_id][5] and self._wt_list[cl_id][1] == ord_no:
                self._wt_list[cl_id][5] = False

    def _wt_buy(self, rec, normal=True):
        cl_id = rec.client_id.strip()
        if int(rec.filled_qty) > 0:
            if normal:
                if rec.symbol.strip() in self._zh_list[rec.acct.strip()]:
                    self._zh_list[rec.acct.strip()][rec.symbol.strip()][0] += (int(rec.filled_qty) -
                                                                               self._wt_list[cl_id][2])
                else:
                    self._zh_list[rec.acct.strip()][rec.symbol.strip()] = [
                        0, 0.0]
                    self._zh_list[rec.acct.strip()][rec.symbol.strip()][0] = int(
                        rec.filled_qty)
                    self._zh_list[rec.acct.strip()][rec.symbol.strip()
                                                    ][1] = float(rec.avg_px)
            je = (int(rec.filled_qty) * float(rec.avg_px)) - \
                (self._wt_list[cl_id][2] * self._wt_list[cl_id][3])
            self._wt_list[cl_id][2] = int(rec.filled_qty)
            self._wt_list[cl_id][3] = float(rec.avg_px)
            self._wt_list[cl_id][4] -= je
            if self._wt_list[cl_id][0].ord_qty <= self._wt_list[cl_id][2]:
                self._wt_list[cl_id][5] = False
                if self._wt_list[cl_id][4] > 0 and normal:
                    self._zh_list[rec.acct.strip(
                    )]['zjky'] += self._wt_list[cl_id][4]

    def _wt_sell(self, rec, normal=True):
        cl_id = rec.client_id.strip()
        if int(rec.filled_qty) > 0:
            if normal:
                self._zh_list[rec.acct.strip()]['zjky'] += (int(rec.filled_qty) * float(rec.avg_px) -
                                                            self._wt_list[cl_id][4])
            self._wt_list[cl_id][2] = int(rec.filled_qty)
            self._wt_list[cl_id][3] = float(rec.avg_px)
            self._wt_list[cl_id][4] = (int(rec.filled_qty) * float(rec.avg_px))
            if self._wt_list[cl_id][0].ord_qty <= self._wt_list[cl_id][2]:
                self._wt_list[cl_id][5] = False

    def _wt_err(self, rec, normal=True):
        cl_id = rec.client_id.strip()
        self._wt_list[cl_id][5] = False
        if normal:
            if rec.tradeside == '1':
                self._zh_list[rec.acct.strip(
                )]['zjky'] += self._wt_list[cl_id][4]
            if rec.tradeside == '2':
                self._zh_list[rec.acct.strip(
                )][rec.symbol][0] += (rec.ord_qty - self._wt_list[cl_id][2])

    def _get_wt(self):
        self._ord_db.open()
        rec_no = 0
        for rec in self._ord_db:
            record = Order_rec(rec.inst_type.strip(), rec.client_id, rec.acct_type.strip(),
                               rec.acct.strip(), rec.ord_no.strip(), rec.symbol.strip(),
                               rec.tradeside.strip(), rec.ord_qty, rec.ord_price,
                               rec.ord_type.strip())
            je = rec.ord_qty * rec.ord_price
            if rec.inst_type.strip() == 'O':
                if rec.tradeside.strip() == '1':
                    self._wt_list[str(rec.client_id)] = [
                        record, '', 0, 0.0, je, True]
                else:
                    self._wt_list[str(rec.client_id)] = [
                        record, '', 0, 0.0, 0.0, True]
            else:
                self._wt_list[str(rec.client_id)] = [
                    record, '', 0, 0.0, 0.0, False]
            if rec.inst_type.strip() == 'C':
                for cl_id in self._wt_list.keys():
                    if self._wt_list[cl_id][5] and self._wt_list[cl_id][1] == rec.ord_no.strip():
                        self._wt_list[cl_id][5] = False

            rec_no += 1
        self._ord_db.close()
        return rec_no


class Trading(object):  # 策略主体

    def __init__(self, stocks, engine, mdi):
        self._stocks = stocks
        self._ee = engine
        self._mdi = mdi
        self._rate = 0.0
        self._tick = 0
        self._wt_list = OrderedDict()
        self._is_chk = False
        self._active = False
        self._pr_204001 = [0, 0, 0]
        self._is_down = False

    def _onChoice(self, ev):  # 价格判断
        self._tick += 1
        # if self._tick%2==0:
        #    event = Event(self.EVENT_CHK)  #发送查成交请求
        # print('check')
        #    self._ee.put(event)
        if self._tick % 60 == 0:
            pr, _ = self._mdi.get_price(['204001'])
            self._pr_204001[0] = self._pr_204001[1]
            self._pr_204001[1] = self._pr_204001[2]
            self._pr_204001[2] = pr['204001'][0]
            print(self._pr_204001)
            if self._pr_204001[2] < self._pr_204001[1] < self._pr_204001[0]:
                self._is_down = True
            elif self._pr_204001[2] > self._pr_204001[1] > self._pr_204001[0]:
                self._is_down = False

        is_up = False
        if is_up:
            cancel = self._mdi.get_can_cancel()
            for key in cancel.keys():
                self._mdi.cancel_order(cancel[key][0].acct, cancel[key][1])
            zh = self._mdi.get_zh_list
            buy, sell = self._mdi.get_price(self._stocks.keys())
            for key in zh:
                zc = self._mdi.get_zc(key)
                for stock in zc.keys():
                    if stock != 'zjky' and zc[stock][0] > 0:
                        event = Event(EVENT_ORDER)
                        event.dict_['account'] = key
                        event.dict_['stock'] = stock
                        event.dict_['price'] = buy[stock[:6]][0]
                        event.dict_['vol'] = zc[stock][0]
                        event.dict_['direct'] = False
                        self._ee.put(event)

        if self._is_down:
            if self._tick % 3 == 0:
                set_ord = False
                # print('choice')
                buy, sell = self._mdi.get_price(self._stocks.keys())
                stock = ''
                if not sell:
                    return
                for key in self._stocks.keys():
                    rate = (self._stocks[key] + (100 - sell[key][0]) * 365) / 2
                    if rate > self._rate:
                        self._rate = rate
                        stock = key
                        set_ord = True
                        print(
                            stock, self._stocks[key], (100 - sell[key][0]) * 365, self._rate)
                if set_ord:
                    bv = buy[stock][1] + buy[stock][3] + buy[stock][4]
                    sv = sell[stock][1] * 1.5
                    print(stock, self._rate, bv, sv)
                    # if self._rate > pr['204001'][0] and
                    if sell[stock][0] < 110:  # bv > sv and 符合规则，发送委托消息
                        zh = self._mdi.get_zh_list
                        if len(zh) == 0:
                            return
                        bv_max = int(sell[stock][1] / len(zh))
                        if bv_max < 100:
                            bv_max = 100
                        for key in zh:
                            zc = self._mdi.get_zc(key)
                            zjky = zc['zjky']
                            if zjky > 0:
                                amon = int((zjky / sell[stock][0] / 100) * 100)
                                if amon < 100:
                                    continue
                                if amon > bv_max:
                                    amon = bv_max
                                event = Event(EVENT_ORDER)
                                event.dict_['account'] = key
                                event.dict_['stock'] = '{0}.SH'.format(stock)
                                event.dict_['price'] = sell[stock][0]
                                event.dict_['vol'] = amon
                                event.dict_['direct'] = True
                                print(stock, sell[stock])
                                self._ee.put(event)
                                print(stock, self._rate, bv, sv)
                    else:
                        print(self._rate)
                        self._rate = 0.0

    def _on_ord(self, ev):  # 委托买入卖出事件
        ord_id = 0
        amon = ev.dict_['vol']
        key = ev.dict_['account']
        if ev.dict_['direct']:
            ord_id = self._mdi.order(key, ev.dict_['stock'], ev.dict_[
                                     'price'], '0', amon, '1')
        else:
            ord_id = self._mdi.order(key, ev.dict_['stock'], ev.dict_[
                                     'price'], '0', amon, '2')
        if ord_id:
            self._wt_list[str(ord_id)] = [key, ev.dict_['stock'], ev.dict_['price'], amon,
                                          0, ev.dict_['direct']]

    def _on_chk(self, ev):  # 成交查询事件，并发+0.001卖出
        print('check wt')
        if not self._wt_list:
            if not self._mdi.get_can_cancel():
                self._rate = 0.0
            return
        wt = self._mdi.get_wt_list
        key_list = tuple(self._wt_list.keys())
        for key in key_list:
            self._wt_list[key][4] = wt[key][2]
            if self._wt_list[key][3] <= wt[key][2] and self._wt_list[key][5]:
                # if self._wt_list[key][2] < 99.97:
                #    price = 99.98
                # else:
                price = self._wt_list[key][2] + 0.001
                event = Event(EVENT_ORDER)
                event.dict_['account'] = self._wt_list[key][0]
                event.dict_['stock'] = self._wt_list[key][1]
                event.dict_['price'] = price
                event.dict_['vol'] = self._wt_list[key][3]
                event.dict_['direct'] = False
                self._ee.put(event)
            print(key, wt[key][5])
            if not wt[key][5]:
                del self._wt_list[key]

    def start(self):  # 主循环
        self._active = True
        is_not_reg = [True, True]
        print("Press 'D' to exit...")
        while self._active:
            today = datetime.now()
            now_time = '{0:02d}:{1:02d}:{2:02d}'.format(
                today.hour, today.minute, today.second)
            print(now_time)
            # buy,sell = self._mdi.get_price(self._stocks.keys())
            # 注册事件处理函数
            if is_not_reg[0] and '09:30:00' < now_time < '14:50:00':
                zh = self._mdi.get_zh_list
                wt = self._mdi.get_can_cancel()
                if wt:
                    for key in wt:
                        rec = wt[key]
                        self._wt_list[key] = [rec[0].acct, rec[0].symbol, rec[0].ord_price,
                                              rec[0].ord_qty, rec[2], (rec[0].tradeside == '1')]
                buy, sell = self._mdi.get_price(self._stocks.keys())
                self._ee.register(EVENT_ORDER, self._on_ord)
                for key in zh:
                    zc = self._mdi.get_zc(key)
                    for stock in zc.keys():
                        if stock != 'zjky' and zc[stock][0] > 0:
                            event = Event(EVENT_ORDER)
                            event.dict_['account'] = key
                            event.dict_['stock'] = stock
                            event.dict_['price'] = buy[stock[:6]][0]
                            event.dict_['vol'] = zc[stock][0]
                            event.dict_['direct'] = False
                            self._ee.put(event)
                self._ee.register(EVENT_TIMER, self._onChoice)
                is_not_reg[0] = False
                print('set_ord_cho')
            # 处理函数解除注册并撤销所有可撤委托
            if not is_not_reg[0] and now_time > '14:50:00':
                self._ee.unregister(EVENT_TIMER, self._onChoice)
                self._ee.unregister(EVENT_ORDER, self._on_ord)
                print('un_set_ord_cho')
                cancel = self._mdi.get_can_cancel()
                for key in cancel.keys():
                    self._mdi.cancel_order(cancel[key][0].acct, cancel[key][1])
                is_not_reg[0] = True
            if is_not_reg[1] and '09:30:00' < now_time < '15:00:00':
                self._ee.register(EVENT_TRADE, self._on_chk)
                is_not_reg[1] = False
                print('set_chk')

            if '09:30:00' < now_time < '15:00:00':
                zh = self._mdi.get_zh_list
                for key in zh:
                    zc = self._mdi.get_zc(key)
                    print('资产列表：', zc)
                print('未成交委托列表：', self._wt_list)
                print('委托列表：', self._mdi.get_wt_list)
            if now_time > '15:00:00':
                self._active = False
            sleep(30)

        self._ee.stop()


with open(r'd:\sl1.txt', 'r') as f:
    i = f.readline()
    stocks = json.loads(i)
    print(stocks)

# stocks = {'511660':4.103,'511690':3.841,'511810':4.166,'511990':3.893}
ee = EventEngine()
mdi = CastMid(ee)
trade = Trading(stocks, ee, mdi)
mdi.start()
ee.start()
main_th = Thread(target=trade.start)
loop = True
main_th.start()
while loop:
    print("Press 'D' to exit...")
    if ord(msvcrt.getch()) in [68, 100]:
        trade._active = False
        loop = False
    sleep(60)
main_th.join()
print('END')
