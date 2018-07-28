# coding:utf-8
'''
发送业务逻辑
'''
import time
import json
import codecs


class sender(object):
    def __init__(self):
        self.sender = None
        self.http_data = None
        self.time_obj = None

    def set_info(self, usr_dict):
        self.http_data = {
            'sat_name': 'DSWLP-B',
            'physical_channel': 13,
            'proxy_nickname': usr_dict[0],
            'proxy_long': usr_dict[1],
            'proxy_alt': usr_dict[2],
            'proxy_lat': usr_dict[3]
        }

    def set_time_obj(self, time_obj):
        self.time_obj = time_obj

    def set_sender(self, sender):
        self.sender = sender

    def send_msg(self, msg):
        if self.http_data is None:
            print "please input info"
        elif self.time_obj is None:
            print "please set time object"
        elif self.sender is not None:
            if len(msg) != 0:
                msg = unicode(msg)  # Qstring to string
                py_time = self.time_obj.dateTime().toPyDateTime()
                py_time = time.mktime(
                    py_time.timetuple()) + py_time.microsecond / 1E6
                # 使用输入框输入的时间
                self.http_data['proxy_receive_time'] = int(py_time * 1000)
                self.http_data['raw_data'] = codecs.encode(msg, 'hex')
                send_data = json.dumps(self.http_data)  # 转json
                print self.http_data  # debug
                self.sender.SendData(send_data)
            else:
                print "please input something"
        else:
            print "[Error] msg sender is not set!"
