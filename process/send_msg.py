# coding:utf-8
'''
发送业务逻辑
'''
import json
import codecs
import calendar


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
            print("please start proxy")
        elif self.time_obj is None:
            print("please set time object")
        elif self.sender is not None:
            if len(msg) != 0:
                msg = unicode(msg)  # Qstring to string
                py_time = self.time_obj.dateTime().toPyDateTime()
                py_time = utc_datetime_to_timestamp(py_time)
                # 使用输入框输入的时间
                self.http_data['proxy_receive_time'] = int(py_time)
                self.http_data['raw_data'] = codecs.encode(msg, 'hex')
                send_data = json.dumps(self.http_data)  # 转json
                print(self.http_data)  # debug
                self.sender.SendData(send_data)
            else:
                print("please input something")
        else:
            print("[Error] msg sender is not set!")


def utc_datetime_to_timestamp(utc_datetime):
    """将 utc 时间 (datetime 格式) 转为 utc 时间戳
    :param utc_datetime: {datetime}2016-02-25 20:21:04.242000
    :return: 13位 的毫秒时间戳 1456431664242
    """
    utc_timestamp = long(
        calendar.timegm(utc_datetime.timetuple()) * 1000.0 +
        utc_datetime.microsecond / 1000.0)
    return utc_timestamp