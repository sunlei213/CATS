#!/usr/bin/env python
# encoding: utf-8

""" 
@version: v1.0 
@author: sunlei 
@license: Apache Licence  
@contact: 12166056@qq.com 
@site: http://blog.csdn.net/sunlei213 
@software: PyCharm Community Edition 
@file: vncast.py 
@time: 2017/9/15 21:08 
"""
# import json
from queue import Queue, Empty
# from trader.vtFunction import getTempPath, getJsonPath
# from trader.vtGateway import *
from threading import Thread
from time import sleep
from datetime import datetime
from collections import defaultdict, OrderedDict
import dbf
from vtobject import *
import copy


class MdApi(object):  # 行情处理类

    DEBUG = True

    def __init__(self):
        self._sh_db = None
        self._sz_db = None
        self.interval = 1  # 每次请求的间隔等待
        self.active = False  # API工作状态
        self._is_reqhq = False  # 是否开始发送行情
        self.reqID = 0  # 请求编号
        self._hq_dict = dict()
        self.interval = 2  # 每次请求的间隔等待
        self.subSymbols = defaultdict(set)  # 订阅代码表
        self.reqQueue = Queue()  # 请求队列
        self._req_thread = Thread(target=self.process_queue)  # 请求处理线程
        self._hq_prices_thread = Thread(target=self.process_prices)  # 实时行情线程
        # 合约字典（保存合约查询数据）
        self._codepage = 'cp936'

    def init(self, db_path):
        try:
            self._sh_db = dbf.Table(db_path['SH'], codepage=self._codepage)
            # self._sz_db = dbf.Table(db_path['SZ'])
        except KeyError:
            log = VtLogData()
            log.gatewayName = 'CastMdApi'
            log.logContent = u'dbf路径配置出错，请检查'
            self.onLog(log)
            return
        self.active = True
        self._req_thread.start()
        self._hq_prices_thread.start()
        self.on_inited()

    def exit(self):
        if self.active:
            self.active = False
            self._is_reqhq = False
            self._req_thread.join()
            log = VtLogData()
            log.gatewayName = 'CastMdApi'
            log.logContent = u'Api结束'
            self.onLog(log)
        self.on_exited()

    def process_queue(self):
        while self.active:
            try:
                req = self.reqQueue.get(block=True, timeout=1)  # 获取请求的阻塞为一秒
                callback = req['callback']
                reqID = req['reqID']

                error = req.get('error', {})

                # 请求失败

                if 'error_code' in error:
                    error1 = u'请求出错，错误代码：%s' % error['error_code']
                    self.onError(error1, 0, True)
                # 请求成功
                else:
                    if self.DEBUG:
                        print(callback.__name__)
                    callback(req, reqID)

                    # 流控等待
                    # sleep(self.interval)

            except Empty:
                pass

    def process_prices(self):
        """获取价格推送"""

        while self.active:
            # 首先获取上海市场的行情
            if self._is_reqhq:
                try:
                    self._sh_db.open()
                    hq_list = [rec for rec in self._sh_db]
                    self._sh_db.close()
                except Exception as e:
                    self.onError('打开上海行情库失败,错误信息：{0}'.format(str(e)), 0, True)
                    hq_list = []
                sh_time = ''
                today = ''
                now_time = datetime.now()
                for n, record in enumerate(hq_list):
                    tick = dict()
                    if len(record):
                        if n == 0:
                            today = str(int(record.s6))
                            time1 = record.s2.strip()
                            sh_time = '{0}:{1}:{2}'.format(
                                time1[:2], time1[2:4], time1[-2:])
                            continue
                        if dbf.is_deleted(record):
                            continue
                        tick['TradingDay'] = today
                        tick['UpdateTime'] = sh_time
                        tick['datetime'] = now_time
                        tick['symbol'] = record.s1.strip()
                        tick['exchange'] = 'SH'
                        tick['vtSymbol'] = '.'.join([tick['symbol'], 'SH'])

                        tick['lastPrice'] = record.s8
                        tick['volume'] = record.s11
                        tick['openPrice'] = record.s4
                        tick['highPrice'] = record.s6
                        tick['lowPrice'] = record.s7
                        tick['preClosePrice'] = record.s3

                        # LTS有5档行情
                        tick['buyPrice1'] = record.s9
                        tick['buyVolume1'] = record.s15
                        tick['sellPrice1'] = record.s10
                        tick['sellVolume1'] = record.s21

                        tick['buyPrice2'] = record.s16
                        tick['buyVolume2'] = record.s17
                        tick['sellPrice2'] = record.s22
                        tick['sellVolume2'] = record.s23

                        tick['buyPrice3'] = record.s18
                        tick['buyVolume3'] = record.s19
                        tick['sellPrice3'] = record.s24
                        tick['sellVolume3'] = record.s25

                        tick['buyPrice4'] = record.s26
                        tick['buyVolume4'] = record.s27
                        tick['sellPrice4'] = record.s30
                        tick['sellVolume4'] = record.s31

                        tick['buyPrice5'] = record.s28
                        tick['buyVolume5'] = record.s29
                        tick['sellPrice5'] = record.s32
                        tick['sellVolume5'] = record.s33
                        if record.s1.strip() in self.subSymbols['SH']:
                            req = dict()
                            req['callback'] = self.on_send_mkt_data
                            req['reqID'] = 0
                            req['data'] = tick
                            self.reqQueue.put(req)
                        self._hq_dict[tick['vtSymbol']] = tick
                    if not self.active:
                        break
            # 获取深圳行情

            # 流量控制
            sleep(self.interval)
            pass

    def start(self):
        self._is_reqhq = True

    def stop(self):
        self._is_reqhq = False

    def sub_symbol(self, rq):
        self.subSymbols[rq['exchange']].add(rq['symbol'])
        vsymbol = '.'.join([rq['symbol'], rq['exchange']])
        print(vsymbol)

        req = dict()
        req['callback'] = self.on_send_mkt_data
        req['reqID'] = 0
        req['data'] = self._hq_dict.get(vsymbol, {})
        self.reqQueue.put(req)

    def unsub_symbol(self, exchange, symbol):
        req = dict()
        if symbol in self.subSymbols[exchange]:
            self.subSymbols[exchange].remove(symbol)
            req['callback'] = self.on_unsub_symbol
            req['reqID'] = 0
        else:
            req['callback'] = self.on_unsub_symbol
            req['reqID'] = 0
            req['data'] = {'error_code': '{0}未订阅'.format(symbol)}
        self.reqQueue.put(req)

    # ----------------------------------------------------------------------
    def getInstrument(self):
        """获取合约信息"""
        hq_stat = self._is_reqhq  # 保存行情更新状态
        self._is_reqhq = False  # 停止行情更新
        try:
            self._sh_db.open()
            hq_list = [rec for rec in self._sh_db]
            self._sh_db.close()
        except Exception as e:
            self.onError('打开上海行情库失败,错误信息：{0}'.format(str(e)), 0, True)
            hq_list = []
        for record in hq_list:
            tick = VtContractData()
            if len(record):
                tick.symbol = record.s1.strip()
                tick.exchange = 'SH'
                tick.vtSymbol = '.'.join([tick.symbol, 'SH'])
                tick.name = record.s2.strip()
                if tick.symbol[:3] in ['511']:
                    tick.is_t0 = True
                req = dict()
                req['callback'] = self.on_get_instrument
                req['reqID'] = 0
                req['data'] = tick
                req['last'] = False
                req['ErrorID'] = 0
                self.reqQueue.put(req)
        req = dict()
        req['reqID'] = 0
        req['callback'] = self.on_get_instrument
        req['last'] = True
        req['data'] = dict()
        req['ErrorID'] = 0
        self.reqQueue.put(req)
        self._is_reqhq = hq_stat  # 恢复行情状态

    def onError(self, error, n, last):
        """错误推送"""
        print(error, n, last)

    def on_get_instrument(self, req, reqID):
        pass

    def on_inited(self):
        pass

    def on_exited(self):
        pass

    def onLog(self, log):
        """显示log"""
        print(log.gatewayName, log.logContent)

    def on_send_mkt_data(self, req, reqID):
        print(req['data'])
        print('*' * 20)
        pass

    def on_sub_symbol(self, req, reqID):
        print(self.subSymbols)

    def on_unsub_symbol(self, req, reqID):
        pass


class TdApi(object):
    DEBUG = True

    def __init__(self):
        self._ord_db = None
        self._hb_db = None
        self._zh_db = None
        self._zh_list = dict()
        self._wt_list = OrderedDict()  # 委托列表
        self._cj_list = dict()  # 委托的最后一笔成交
        self._client_id = 1000  # 委托起始编号
        self._wt_num = 0  # 委托库起始记录号
        self._cj_num = 0  # 回报库起始记录号
        self.interval = 1  # 每次请求的间隔等待
        self.active = False  # API工作状态
        self.reqID = 0  # 请求编号
        self.reqQueue = Queue()  # 请求队列
        self._req_thread = Thread(target=self.process_queue)  # 请求处理线程
        self._events_thread = Thread(target=self.process_events)  # 实时事件线程（成交等）
        self._codepage = 'cp936'

    def get_zj(self, exchangeid):
        return self._zh_list[exchangeid]['acct']

    def get_stocks(self, exchangeid):
        return self._zh_list[exchangeid]['stock']

    @property
    def acct_list(self):
        return tuple(self._zh_list.keys())

    @property
    def wt_list(self):
        return self._wt_list

    def init(self, db_path):
        try:
            self._ord_db = dbf.Table(db_path['Order'], codepage=self._codepage)
            self._hb_db = dbf.Table(db_path['HB'], codepage=self._codepage)
            self._zh_db = dbf.Table(db_path['Acct'], codepage=self._codepage)
        except Exception as e:
            log = VtLogData()
            log.gatewayName = 'CastTdApi'
            log.logContent = u'dbf路径配置出错，请检查.{0}'.format(str(e))
            self.onLog(log)
            return
        self.active = True
        self._req_thread.start()
        self.query_acc('', False)
        print(self._zh_list)
        self._client_id += self._get_wt()
        print(self._zh_list)
        self._get_cj()
        print(self._zh_list)
        self._events_thread.start()
        self.on_inited()

    def query_acc(self, data, reqID):
        self._zh_db.open()

        for rec in self._zh_db:
            if rec.acct.strip() in self._zh_list:
                asset = self._zh_list[rec.acct.strip()]
            else:
                asset = {'acct': {'zjky': 0.0, 'zzc': 0.0}, 'stocks': dict()}
            if rec.a_type.strip() == 'F':
                asset['acct']['zjky'] = float(rec.s4)
                zzc = float(rec.s4)
            else:
                asset['stocks'][rec.s1.strip()] = [int(rec.s3), float(
                    rec.s4), rec.s8.strip(), float(rec.s9) if rec.s9.strip() else 0]
                zzc += float(rec.s9) if rec.s9.strip() else 0
            asset['acct']['zzc'] = zzc
            self._zh_list[rec.acct.strip()] = asset
        self._zh_db.close()
        self.push_zh()

        # if reqID:
        #    self.on_query()

    def push_zh(self):
        pass

    def exit(self):
        if self.active:
            self.active = False
            self._req_thread.join()
            log = VtLogData()
            log.gatewayName = 'CastTdApi'
            log.logContent = u'Api结束'
            self.onLog(log)
        self.on_exited()

    def process_queue(self):
        while self.active:
            try:
                req = self.reqQueue.get(block=True, timeout=1)  # 获取请求的阻塞为一秒
                callback = req['callback']
                reqID = req['reqID']

                error = req.get('error', {})

                # 请求失败

                if 'error_code' in error:
                    error1 = u'请求出错，错误代码：%s' % error['error_code']
                    self.onError(error1, req, reqID)
                # 请求成功
                else:
                    if self.DEBUG:
                        print(callback.__name__, req.get('func', ''))
                    callback(req, reqID)

            except Empty:
                pass

    def onError(self, error, n, reqID):
        """错误推送"""
        print(error, n, reqID)

    def on_inited(self):
        pass

    def on_exited(self):
        pass

    def on_query(self):
        self.reqQryTradingAccount()
        self.reqQryInvestorPosition()
        pass

    def onLog(self, log):
        """"显示log"""
        pass

    def on_order(self, req, reqID):
        pass

    def on_cancel(self, req, reqID):
        pass

    def process_events(self):
        while self.active:
            last = False
            try:
                self._hb_db.open()
                rec_num = len(self._hb_db)
                if self._cj_num < rec_num:
                    hb_list = [self._hb_db[x]
                               for x in range(self._cj_num, rec_num)]
                    self._cj_num = rec_num
                else:
                    hb_list = []
                self._hb_db.close()

            except Exception as e:
                self.onError('打开回报库失败,错误信息：{0}'.format(str(e)), 0, 0)
                hb_list = []
            for rec in hb_list:
                last = True
                req = dict()
                req['data'] = rec
                req['last'] = False
                req['reqID'] = 0
                req['callback'] = self.on_event
                self.reqQueue.put(req)
                if not self.active:
                    break
            if last:
                req = dict()
                req['data'] = dict()
                req['last'] = True
                req['reqID'] = 0
                req['callback'] = self.on_event
                self.reqQueue.put(req)

            # 流控等待
            sleep(self.interval)

    def reqQryTradingAccount(self):
        for acc in self._zh_list.keys():
            data = dict()
            data['AccountID'] = acc
            data['Available'] = self._zh_list[acc]['acct']['zjky']
            data['CurrMargin'] = self._zh_list[acc]['acct']['zjky']
            req = dict()
            req['reqID'] = True
            req['callback'] = self.onRspQryTradingAccount
            req['data'] = data
            req['ErrorID'] = 0
            self.reqQueue.put(req)

    def reqQryInvestorPosition(self):
        for acc in self._zh_list.keys():
            for stock in self._zh_list[acc]['stocks'].keys():
                data = dict()
                data['AccountID'] = acc
                data['InstrumentID'] = stock
                data['StockName'] = self._zh_list[acc]['stocks'][stock][2]
                data['Position'] = self._zh_list[acc]['stocks'][stock][0]
                data['PositionCost'] = self._zh_list[acc]['stocks'][stock][1]
                data['StockValue'] = self._zh_list[acc]['stocks'][stock][3]

                req = dict()
                req['reqID'] = True
                req['callback'] = self.onRspQryInvestorPosition
                req['data'] = data
                req['ErrorID'] = 0
                self.reqQueue.put(req)

    def onRspQryTradingAccount(self, req, req_id):
        pass

    def onRspQryInvestorPosition(self, req, req_id):
        pass

    def order(self, req, req_id):
        rec = Order_rec()
        rec.inst_type = 'O'
        rec.client_id = self._client_id
        rec.acct_type = 'S0'
        rec.acct = req['exchangeid']

        rec.symbol = req['stock']
        rec.tradeside = req['direction']
        rec.ord_qty = req['volume']
        rec.ord_price = req['price']
        rec.ord_type = req['pricetype']
        rec.cj_je = -(req['price'])
        rec.cj_vol = req['volume']
        je = req['price'] * req['volume']
        if rec.tradeside.strip() == '1':
            self._zh_list[rec.acct]['acct']['zjky'] += je
        elif rec.tradeside.strip() == '2':
            self._zh_list[rec.acct]['stocks'][rec.symbol][0] -= rec.ord_qty
        self._wt_list[str(self._client_id)] = rec
        self._ord_db.open()
        self._ord_db.append(rec.ord())
        self._ord_db.close()
        self._client_id += 1
        rq = dict()
        rq['callback'] = self.on_order
        rq['data'] = copy.deepcopy(rec)
        rq['reqID'] = 0
        rq['func'] = 'order'
        self.reqQueue.put(rq)
        return self._client_id - 1

    def cancel_order(self, req, req_id):
        rec = Order_rec()
        ord_cl = str(req['orderid'])
        can_rec = self._wt_list[ord_cl]
        if not can_rec.can_cancel or len(can_rec.ord_no) == 0:
            error = u'无可撤委托'
            self.onError(error, 0, 0)
            return

        print(can_rec)
        rec.inst_type = 'C'
        rec.client_id = self._client_id
        rec.acct_type = 'S0'
        rec.acct = can_rec.acct
        rec.ord_no = can_rec.ord_no
        self._wt_list[str(self._client_id)] = rec
        self._ord_db.open()
        self._ord_db.append(rec.ord())
        self._ord_db.close()
        self._client_id += 1
        can_rec.can_cancel = False
        if can_rec.tradeside == '1':
            self._zh_list[can_rec.acct]['acct']['zjky'] += can_rec.je
        if can_rec.tradeside == '2':
            can_rec.cj_vol = 0
            self._zh_list[can_rec.acct]['stocks'][can_rec.symbol][0] += (
                can_rec.ord_qty - can_rec.filled_qty)
        rq = dict()
        rq['callback'] = self.on_order
        rq['data'] = copy.deepcopy(can_rec)
        rq['reqID'] = 0
        rq['func'] = 'cancel_order'
        self.reqQueue.put(rq)

    def on_event(self, req, reqid):
        if req['last']:
            self.on_cj_update()
        else:
            rec = req['data']
            self.update_cj(rec)

    def on_cj_update(self):
        pass

    def on_trade(self, req, req_id):
        pass

    def _get_cj(self):
        try:
            self._hb_db.open()
            rec_num = len(self._hb_db)
            if self._cj_num < rec_num:
                hb_list = [self._hb_db[x]
                           for x in range(self._cj_num, rec_num)]
                self._cj_num = rec_num
            else:
                hb_list = []
            self._hb_db.close()

        except Exception as e:
            self.onError('打开回报库失败,错误信息：{0}'.format(str(e)), 0, 0)
            hb_list = []
        for rec in hb_list:
            self.update_cj(rec, False)
        print('成交获取完毕')
#         for rec in self._wt_list.values():
#             rq = dict()
#             rq['callback'] = self.on_order
#             rq['data'] = copy.deepcopy(rec)
#             rq['reqID'] = 0
#             rq['func'] = '_get_cj'
#             self.reqQueue.put(rq)

    def update_cj(self, rec, normal=True):
        if len(rec.client_id.strip()):
            if len(rec.err_msg.strip()):
                self._wt_err(rec, normal)
            else:
                client_id = rec.client_id.strip()
                self._wt_list[client_id].ord_time = rec.ord_time.strip()
                if self._wt_list[client_id].inst_type == 'C':
                    self._wt_cancel(rec)
                else:
                    self._wt_list[client_id].ord_no = rec.ord_no.strip()
                    if int(rec.filled_qty) > 0:
                        if rec.tradeside.strip() == '1':
                            self._wt_buy(rec, normal)
                        elif rec.tradeside.strip() == '2':
                            self._wt_sell(rec, normal)
                        if normal and rec.tradeside.strip() in ['1', '2']:
                            d = self.get_trade(rec)
                            rq = dict()
                            rq['callback'] = self.on_trade
                            rq['data'] = d
                            rq['reqID'] = 0
                            rq['func'] = 'update_cj'
                            self.reqQueue.put(rq)
                            rq = dict()
                            rq['callback'] = self.on_order
                            rq['data'] = copy.deepcopy(
                                self._wt_list[client_id])
                            rq['reqID'] = 0
                            rq['func'] = 'update_cj'
                            self.reqQueue.put(rq)

    def get_trade(self, rec):
        cl_id = rec.client_id.strip()
        dictLabels = dict()
        if cl_id in self._cj_list:
            old_rec = self._cj_list[cl_id]
            dictLabels['OrderRef'] = cl_id
            dictLabels['InstrumentID'] = rec.symbol.strip()
            dictLabels['ExchangeInstID'] = rec.acct.strip()
            dictLabels['Direction'] = rec.tradeside.strip()
            dictLabels['TradeTime'] = rec.ord_time.strip()
            dictLabels['Volume'] = int(
                rec.filled_qty) - int(old_rec.filled_qty)
            if dictLabels['Volume']:
                dictLabels['Price'] = (int(rec.filled_qty) * float(rec.avg_px) - int(old_rec.filled_qty) *
                                       float(old_rec.avg_px)) / dictLabels['Volume']
            else:
                dictLabels['Price'] = 0.0
            dictLabels['OrderSysID'] = rec.ord_no.strip()
        else:
            dictLabels['OrderRef'] = cl_id
            dictLabels['InstrumentID'] = rec.symbol.strip()
            dictLabels['ExchangeInstID'] = rec.acct.strip()
            dictLabels['Direction'] = rec.tradeside.strip()
            dictLabels['TradeTime'] = rec.ord_time.strip()
            dictLabels['Volume'] = int(rec.filled_qty)
            dictLabels['Price'] = float(rec.avg_px)
            dictLabels['OrderSysID'] = rec.ord_no.strip()
        self._cj_list[cl_id] = rec
        return dictLabels

    def _wt_cancel(self, rec):
        cl_id = rec.client_id.strip()
        ord_no = self._wt_list[cl_id].ord_no
        for cl_id in self._wt_list.keys():
            # print(self._wt_list[cl_id],ord_no)
            if self._wt_list[cl_id].can_cancel and self._wt_list[cl_id].ord_no == ord_no:
                self._wt_list[cl_id].can_cancel = False

    def _wt_buy(self, rec, normal):
        cl_id = rec.client_id.strip()
        if int(rec.filled_qty) > 0:
            if normal:
                if rec.symbol.strip() in self._zh_list[rec.acct.strip()]['stocks']:
                    self._zh_list[rec.acct.strip()]['stocks'][rec.symbol.strip()][0] += (int(rec.filled_qty) -
                                                                                         self._wt_list[cl_id].filed_qty)
                else:
                    self._zh_list[rec.acct.strip()]['stocks'][rec.symbol.strip()] = [int(rec.filled_qty),
                                                                                     float(rec.avg_px), '', 0.0]
            tmp = self._wt_list[cl_id].update_cj(
                int(rec.filled_qty), float(rec.avg_px))

            if tmp and self._wt_list[cl_id].je > 0 and normal:
                self._zh_list[rec.acct.strip(
                )]['acct']['zjky'] += self._wt_list[cl_id].je

    def _wt_sell(self, rec, normal):
        cl_id = rec.client_id.strip()

        if int(rec.filled_qty) > 0:
            if normal:
                self._zh_list[rec.acct.strip()]['acct']['zjky'] += (int(rec.filled_qty) * float(rec.avg_px) -
                                                                    self._wt_list[cl_id].je)
            self._wt_list[cl_id].update_cj(
                int(rec.filled_qty), float(rec.avg_px))

    def _wt_err(self, rec, normal):
        cl_id = rec.client_id.strip()
        self._wt_list[cl_id].can_cancel = False
        if normal:
            if rec.tradeside == '1':
                self._zh_list[rec.acct.strip(
                )]['acct']['zjky'] += self._wt_list[cl_id].je
            if rec.tradeside == '2':
                self._zh_list[rec.acct.strip(
                )]['stocks'][rec.symbol] += (rec.ord_qty - self._wt_list[cl_id].filled_qty)

    def _get_wt(self):
        self._ord_db.open()
        rec_no = 0
        for rec in self._ord_db:
            record = Order_rec()
            record.inst_type = rec.inst_type.strip()
            record.client_id = rec.client_id
            record.acct_type = rec.acct_type.strip()
            record.acct = rec.acct.strip()
            record.ord_no = rec.ord_no.strip()
            record.symbol = rec.symbol.strip()
            record.tradeside = rec.tradeside.strip()
            record.ord_qty = rec.ord_qty
            record.ord_price = rec.ord_price
            record.ord_type = rec.ord_type.strip()
            if rec.inst_type.strip() == 'O':
                record.can_cancel = True
            else:
                record.can_cancel = False
            self._wt_list[str(rec.client_id)] = record
#             rq = dict()
#             rq['callback'] = self.on_order
#             rq['data'] = copy.deepcopy(record)
#             rq['reqID'] = 0
#             rq['func'] = '_get_wt'
#             self.reqQueue.put(rq)
            rec_no += 1
        self._ord_db.close()
        print('委托获取完毕')
        return rec_no


'''
if __name__ == '__main__':
    db_path = {'SH':r'd:\cast\show2003.dbf'}


    # 创建API对象并初始化
    api = MdApi()
    api.DEBUG = True
    api.init(db_path)
    api.start()
    api.sub_symbol('SH','600030')
    stock = input()
    print(stock)
    api.sub_symbol('SH',stock)
    input()
    api.stop()
    input()
    api.start()
    for i in range(3):
        stock = input()
        print(stock)
        api.sub_symbol('SH', stock)
    input('按键终止')
    api.exit()
try:
    self._ord_db.open()
    rec_num = len(self._ord_db)
    if self._wt_num < rec_num:
        wt_list = [self._ord_db[x] for x in range(self._wt_num, rec_num)]
        self._wt_num = rec_num
    else:
        wt_list = []
    self._ord_db.close()

except Exception as e:
    self.onError('打开委托库失败', 0, 0)
    wt_list = []
for rec in wt_list:
    msg = {}
    msg['inst_type'] = rec.inst_type.strip()
    msg['client_id'] = rec.client_id
    msg['acct_type'] = rec.acct_type.strip()
    msg['acct'] = rec.acct.strip()
    msg['ord_no'] = rec.ord_no.strip()
    msg['symbol'] = rec.symbol.strip()
    msg['tradeside'] = rec.tradeside.strip()
    msg['ord_qty'] = rec.ord_qty
    msg['ord_price'] = rec.ord_price
    msg['ord_type'] = rec.ord_type.strip()

    self.on_event(msg)
    if not self.active:
        break
'''
