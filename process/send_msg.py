# coding:utf-8
'''
发送业务逻辑
'''


class sender(object):
    def __init__(self):
        self.sender = None

    def set_sender(self, sender):
        self.sender = sender

    def send_msg(self, msg):
        if self.sender is not None:
            if len(msg) != 0:
                self.sender.SendData(msg)
            else:
                print "please input something"
        else:
            print "[Error] msg sender is not set!"
