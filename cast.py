# -*- coding: utf-8 -*-
"""
Created on Wed Aug 30 09:09:35 2017

@author: sunlei
"""
from queue import Queue, Empty
from threading import Thread
from time import sleep, clock
from collections import defaultdict, namedtuple, OrderedDict
import dbf
# from math import ceil
# from PyQt5.QtCore import QTimer
from datetime import datetime
from random import randint
from decimal import Decimal
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
            #             if event.type_ == EVENT_TIMER:
            #                 print(self.__handlers[event.type_])
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
        self.mkt_time = 0
        self._isClose = False
        self.hq_list = {}
        self._dataMap = {}
        self.mtk_file = r'y:\remote\dbf\mktdt00.txt'
        self._active = False
        self._codepage = 'cp936'
        self.__thread = Thread(target=self.__run)

        if self._ee:
            self._ee.register(EVENT_TIMER, self._on_get_cj)

    def start(self):
        self._hq_db = dbf.Table(self.tables['hq'], codepage=self._codepage)
        self._ord_db = dbf.Table(self.tables['wt'], codepage=self._codepage)
        self._hb_db = dbf.Table(self.tables['hb'], codepage=self._codepage)
        self._zh_db = dbf.Table(self.tables['zh'], codepage=self._codepage)
        self._zh_db.open()
        for rec in self._zh_db:
            if rec.acct.strip() in self._zh_list:
                asset = self._zh_list[rec.acct.strip()]
            else:
                asset = {'zjky': 3000000.0}
            if rec.a_type.strip() == 'F':
                asset['zjky'] = 3000000.0  # float(rec.s4)
            else:
                asset[rec.s1.strip()] = [int(rec.s3), float(rec.s4)]
            self._zh_list[rec.acct.strip()] = asset
        self._zh_db.close()
        self._client_id += self._get_wt()
        self._get_cj(False)
        self._active = True
        self.__thread.start()
        print(self._zh_list)

    def stop(self):
        self._active = False
        self.__thread.join()

    def __run(self):
        while self._active:
            #             self._hq_db.open()
            #             for rec in self._hq_db:
            #                 if dbf.is_deleted(rec):
            #                     continue
            #                 self.hq_list[rec.s1.strip()] = rec
            #             self._hq_db.close()
            self.write_mkt_to_show()
            # print(self.mkt_time)

    def record_strip(self, recodes):
        for recode in recodes:
            re = [value.strip() for value in recode]
            yield re

    def write_mkt_to_show(self):
        """
        mkt转show2003
        :return: True or False
        """
        start = clock()
        first_line = second_line = third_line = ""
        i = 0
        while True:
            try:
                with open(self.mtk_file) as f:
                    lines = [x.replace('\n', '').split('|') for x in f]
                break
            except IOError as e:
                print(e.strerror)
                i += 1
                sleep(randint(1, 100) / 100.00)
                if i > 3:
                    return False
        lines = [x for x in self.record_strip(lines)]
        for i, line in enumerate(lines):
            if i == 0:
                first_line = line
            elif i == 1:
                second_line = line
            elif i == 2:
                third_line = line
            else:
                if i == 3:
                    self._dataMap['000000'] = self.set_first_recode(
                        first_line, second_line[9], third_line[9], line[9])
                    self.mkt_to_map(second_line)
                    self.mkt_to_map(third_line)
                self.mkt_to_map(line)
        self.mkt_time = clock() - start
        return True

    def set_first_recode(self, line, zs_price, ag_price, bg_price):
        objs = [""] * 30
        objs[0] = "000000"
        objs[1] = line[6][9:17].replace(":", "") + "  "
        objs[2] = float(ag_price)
        objs[3] = float(bg_price)
        objs[4] = 0
        self._jyDate = line[6][0:8]
        objs[5] = self._jyDate
        if line[8][0] == "E":
            objs[10] = 1111111111
            self._isClose = True
        else:
            objs[10] = 0
            self._isClose = False
        objs[11] = float(zs_price)
        objs[12] = int(line[8][2])
        objs[14] = int(line[8][1])
        objs.insert(0, True)
        return objs

    def mkt_to_map(self, records):
        if len(records) == 0 or records[0] == "TRAILER":
            return
        objs = [''] * 30
        if records[0] == "MD001":
            objs[0] = records[1]
            objs[1] = records[2]
            objs[2] = float(records[5])
            objs[3] = float(records[6])
            objs[4] = int(999999999999 if len(str(Decimal(records[4]).quantize(Decimal('1')))) > 12
                          else Decimal(records[4]).quantize(Decimal('1')))
            objs[5] = float(records[7])
            objs[6] = float(records[8])
            objs[7] = float(records[10] if self._isClose else records[9])
            objs[10] = int(records[3])
            objs[11] = True
        else:
            objs[0] = records[1]
            objs[1] = records[2]
            objs[2] = float(records[5])
            objs[3] = float(records[6])
            objs[4] = int(999999999999 if len(str(Decimal(records[4]).quantize(Decimal('1')))) > 12
                          else Decimal(records[4]).quantize(Decimal('1')))
            objs[5] = float(records[7])
            objs[6] = float(records[8])
            objs[7] = float(records[10] if self._isClose else records[9])
            objs[8] = float(records[11])
            objs[9] = float(records[13])
            objs[10] = int(records[3])
            st_tmp = records[33] if records[0] == "MD004" else records[31]
            objs[11] = True if len(st_tmp) < 3 else (
                not (st_tmp[0] != 'P' and st_tmp[2] == '1'))
            objs[12] = int(records[12])
            objs[13] = float(records[15])
            objs[14] = int(records[16])
            objs[15] = float(records[19])
            objs[16] = int(records[20])
            objs[17] = int(records[14])
            objs[18] = float(records[17])
            objs[19] = int(records[18])
            objs[20] = float(records[21])
            objs[21] = int(records[22])
            objs[22] = float(records[23])
            objs[23] = int(records[24])
            objs[24] = float(records[27])
            objs[25] = int(records[28])
            objs[26] = float(records[25])
            objs[27] = int(records[26])
            objs[28] = float(records[29])
            objs[29] = int(records[30])
        if objs[11]:
            objs.insert(0, True)
        else:
            objs.insert(0, False)
        objs[12] = ""
        self._dataMap[records[1]] = objs

    def get_price(self, stocks):

        sell = {}
        buy = {}
        for stock in stocks:
            if stock not in self._dataMap:
                continue
            recodes = self._dataMap[stock]

            sell[stock] = (recodes[10], recodes[18], recodes[19],
                           recodes[20], recodes[21], recodes[22])
            buy[stock] = (recodes[9], recodes[13], recodes[14],
                          recodes[15], recodes[16], recodes[17])

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
        ord_rec = self._wt_list[cl_id][0]
        if normal:
            if ord_rec.tradeside == '1':
                self._zh_list[rec.acct.strip(
                )]['zjky'] += self._wt_list[cl_id][4]
            if ord_rec.tradeside == '2':
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
        if self._tick % 60 == 0:
            start_t = clock()
            pr, _ = self._mdi.get_price(['204001'])
            self._pr_204001[0] = self._pr_204001[1]
            self._pr_204001[1] = self._pr_204001[2]
            self._pr_204001[2] = pr['204001'][0]
            print(self._pr_204001, clock() - start_t)
            if self._pr_204001[2] < self._pr_204001[1] < self._pr_204001[0]:
                self._is_down = True
            elif self._pr_204001[2] > self._pr_204001[1] > self._pr_204001[0]:
                self._is_down = False

        if self._tick % 3 == 0:
            #    event = Event(self.EVENT_CHK)  #发送查成交请求
            # print('check')
            buy, sell = self._mdi.get_price(self._stocks.keys())
            for stock in sell.keys():
                if sell[stock][0] < 99.95:
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
                            event.dict_['direct'] = '1'
                            print(stock, sell[stock])
                            self._ee.put(event)
                    print(stock, sell[stock])
                    return

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
                        event.dict_['direct'] = '2'
                        self._ee.put(event)

        if self._is_down:
            if self._tick % 3 == 0:
                set_ord = False
                # print('choice')
                buy, sell = self._mdi.get_price(['511990'])
                stock = '511990'
                if not sell:
                    return
#                 for key in self._stocks.keys():
#                     rate = (self._stocks[key] + (100 - sell[key][0]) * 365) / 2
#                     if rate > self._rate:
#                         self._rate = rate
#                         stock = key
#                         set_ord = True
#                         print(
# stock, self._stocks[key], (100 - sell[key][0]) * 365, self._rate)
                set_ord = True
                if set_ord:
                    bv = buy[stock][1] + buy[stock][3] + buy[stock][4]
                    sv = sell[stock][1] * 1.5
                    # print(stock, self._rate, bv, sv)
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
                                event.dict_['direct'] = '1'
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
        ord_id = self._mdi.order(key, ev.dict_['stock'], ev.dict_[
            'price'], '0', amon, ev.dict_['direct'])
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
            if self._wt_list[key][3] <= wt[key][2] and self._wt_list[key][5] == '1':
                # if self._wt_list[key][2] < 99.97:
                #    price = 99.98
                # else:
                price = self._wt_list[key][2] + 0.001
                event = Event(EVENT_ORDER)
                event.dict_['account'] = self._wt_list[key][0]
                event.dict_['stock'] = self._wt_list[key][1]
                event.dict_['price'] = price
                event.dict_['vol'] = self._wt_list[key][3]
                event.dict_['direct'] = '2'
                self._ee.put(event)
            print(key, wt[key][5])
            if not wt[key][5]:
                del self._wt_list[key]

    def start(self):  # 主循环
        self._active = True
        is_not_reg = [True, True]
        mini = 0
        while self._active:
            today = datetime.now()
#             if mini == today.minute:
#                 continue
#             else:
#                 mini = today.minute
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
                            event.dict_['direct'] = '2'
                            self._ee.put(event)
                self._ee.register(EVENT_TIMER, self._onChoice)
                is_not_reg[0] = False
                print('set_ord_cho')
            # 处理函数解除注册并撤销所有可撤委托
            if not is_not_reg[0] and '14:50:00' < now_time < '14:52:00':
                self._ee.unregister(EVENT_TIMER, self._onChoice)
                self._ee.unregister(EVENT_ORDER, self._on_ord)
                print('un_set_ord_cho')
                cancel = self._mdi.get_can_cancel()
                for key in cancel.keys():
                    self._mdi.cancel_order(cancel[key][0].acct, cancel[key][1])
                is_not_reg[0] = True
            if is_not_reg[0] and '14:51:00' < now_time < '14:52:00':
                zh = self._mdi.get_zh_list
                buy, _ = self._mdi.get_price(self._stocks.keys())
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
                            event.dict_['direct'] = '2'
                            self._ee.put(event)

            if is_not_reg[0] and '14:55:00' < now_time < '14:55:00':
                zh = self._mdi.get_zh_list
                for key in zh:
                    zc = self._mdi.get_zc(key)
                    ky = int(zc['zjky'])
                    event = Event(EVENT_ORDER)
                    event.dict_['account'] = key
                    event.dict_['stock'] = '519881.SH'
                    event.dict_['price'] = 0.01
                    event.dict_['vol'] = ky * 100
                    event.dict_['direct'] = 'F'
                    self._ee.put(event)

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


# with open(r'd:\sl1.txt', 'r') as f:
#     i = f.readline()
#     stocks = json.loads(i)
#     print(stocks)

stocks = {'511990': 0, '511810': 0, '511660': 0, '511990': 0, '511650': 0, '511690': 0, '511820': 0, '511760': 0, '511830': 0, '511850': 0, '511600': 0, '511970': 0,
          '511700': 0, '511800': 0, '511860': 0, '511680': 0, '511930': 0, '511980': 0, '511770': 0, '511920': 0, '511620': 0, '511960': 0, '511950': 0, '511910': 0, '511890': 0}
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
mdi.stop()
main_th.join()
print('END')
