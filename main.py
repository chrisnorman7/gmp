if __name__ == '__main__':
 import requests, application
 from gui.login_frame import LoginFrame
 from requests.packages.urllib3.exceptions import InsecureRequestWarning
 requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
 LoginFrame()
 application.app.MainLoop()
