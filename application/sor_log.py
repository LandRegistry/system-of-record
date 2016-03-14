import pwd
import datetime
import sys
import logging
import os

class SORLogger:

    def make_log_msg(self, message, title_number=''):
        if title_number == '':
            return "{}, Raised by: {}".format( message, linux_user() )
        else:
            return "{}, Raised by: {}, Title Number: {}".format( message, linux_user(), title_number )


    def linux_user(self):
        try:
            return pwd.getpwuid(os.geteuid()).pw_name
        except Exception as err:
            return "failed to get user: %s" % err


    def log_format(self):
        logging.basicConfig(format='%(levelname)s %(asctime)s [SystemOfRecord] Message: %(message)s', level=logging.INFO, datefmt='%d.%m.%y %I:%M:%S %p')