'''
Base class for all Apps on the platform.
'''


class BaseApp(object):

    NAME = ''
    DESC = ''

    def _name(self):
        return self.NAME

    def _desc(self):
        return self.DESC
