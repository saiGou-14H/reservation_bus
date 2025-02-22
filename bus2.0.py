import configparser
import json
import time
from datetime import datetime

import ddddocr
import requests
import hashlib

def log(msg):
    print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]{msg}')
class BUS:
    def __init__(self,t,account,password,type = True,is_verify = False):
        self.headers = {
        'Referer':'https://reservation.scnu.edu.cn/v2/site/ucenter?showroute=myAppointment',
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
          'Cookie':'vjuid=[vjuid]; vjvd=[vjvd]; vt=[vt];PHPSESSID=[PHPSESSID]'
        }
        self.account = account
        self.password = password
        self.REQ = requests.session()
        self.time_str = t
        self.isLogin = self.login()
        self.type = type
        self.is_verify = is_verify
        if self.isLogin:
            self.resource_id = self.getResourceId()
            if self.is_verify:
                self.ocr = ddddocr.DdddOcr(show_ad=False)
                log("验证码识别已开启")
    def run(self):
        if self.resource_id!='' and self.resource_id!=None:
            return self.getZW()
        return False
    def login(self):
        header = {
            'Origin': 'https://sso.scnu.edu.cn/',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Referer': 'https://sso.scnu.edu.cn/AccountService/user/login.html'
        }
        log('[综合平台登录]')
        data = {
            'account': self.account,
            'password': self.password,
            'rancode': ''
        }
        url = 'https://sso.scnu.edu.cn/AccountService/user/login.html'
        # 初始化登录界面
        self.REQ.get(url, headers=header)
        # 登录
        self.REQ.post(url, headers=header, data=data, allow_redirects=True)
        # 初始化用户信息
        info = 'https://sso.scnu.edu.cn/AccountService/user/info.html'
        res = self.REQ.post(info, headers=header).json()
        log(res)
        if res['msgcode'] == -1:
            log('账号密码错误！！')
            return False

        # 生成Cookie
        login = self.REQ.get('https://sso.scnu.edu.cn/AccountService/openapi/onekeyapp.html?app_id=194', headers=header,
                              allow_redirects=False)

        self.cookies = self.REQ.get(login.headers['Location'], headers=header, allow_redirects=False).cookies
        self.vjuid = self.cookies.get('vjuid')
        self.vjvd = self.cookies.get('vjvd')
        self.vt = self.cookies.get('vt')
        self.PHPSESSID = self.cookies.get("PHPSESSID")
        self.headers['Cookie'] = self.headers.get('Cookie').replace('[vjuid]',self.vjuid).replace('[vjvd]',self.vjvd).replace('[vt]',self.vt).replace("[PHPSESSID]",self.PHPSESSID)
        return True
    def getResourceId(self):
        url = 'https://reservation.scnu.edu.cn/site/reservation/list-page?hall_id=2&time={}&resource_name=&resource_id=&min_capacity=&max_capacity=&p=1&page_size=50&sort_type=&start_time_period=&end_time_period=&available_resources=0'.format(self.time_str)
        rep = self.REQ.get(url, headers=self.headers)
        try:
            e = rep.json()
        except:
            return ''
        if len(rep.json()['d']['list'])!=0:
            weekday = datetime.now().weekday()+1+1
            for i in rep.json()['d']['list']:
                if weekday == 7 and i['name'] == '周日大巴车预约':
                    log("周日大巴车预约")
                    return str(i['id'])
                if weekday == 5 and i['name'] == '周五大巴车预约':
                    log("周五大巴车预约")
                    return str(i['id'])
        else:
            log('暂时没有校车信息！')
            return ''

    def getZW(self):
        url = 'https://reservation.scnu.edu.cn/site/reservation/resource-info-margin?resource_id={}&start_time={}&end_time={}'.format(self.resource_id,
            self.time_str, self.time_str)
        data = self.REQ.get(url, headers=self.headers)
        data = data.json()
        info = list(data['d'].values())[0]
        info = info if self.type else info[::-1]
        for item in info:
            if item['row']['status'] == 1:
                log("找到空座位")
                log(item)
                if self.yuyue(item['date'], item['time_id'], item['sub_id']):
                    return True
        return False



    def yuyue(self,date, time_id, sub_id):
        # 需要验证码验证则填入code参数
        if self.is_verify:
            code = self.getCode()
        url = 'https://reservation.scnu.edu.cn/site/reservation/launch'
        datas = {
            'resource_id': self.resource_id,
            'code': '' if not self.is_verify else code,
            'remarks': '',
            'deduct_num': '',
            'data': json.dumps([{"date": date, "period": time_id, "sub_resource_id": sub_id}])
        }
        rep = self.REQ.post(url, data=datas, headers=self.headers)
        rep_json = rep.json()
        if rep_json['m'] == '操作成功':
            log("恭喜你预约成功！")
            return True
        else:
            log("预约失败！")
            return False
    def getCode(self):
        url = f"https://reservation.scnu.edu.cn/site/login/code?v={int(time.time() * 1000)}"
        rep = requests.get(url,headers=self.headers,cookies=self.cookies)
        result =  self.ocr.classification(rep.content)
        log(f"验证码识别结果：{result}")
        self.verify = result
        return result
def getDateTime():
    T = time.strftime('%Y-%m-%d', time.localtime()).split('-')
    T[-1] = str(int(T[-1]) +1)
    T_Str = '-'.join(T)
    return T_Str
def getTime():
    T = time.strftime('%H:%M:%S',time.localtime()).split(':')
    return T

def md52(data):
    data = hashlib.md5(str(data).encode('utf-8')).hexdigest()
    data = hashlib.md5(str(data).encode('utf-8')).hexdigest()
    return data


if __name__ == '__main__':
    log("本程序仅供学习交流,禁止用于其他用途,请于24小时内删除")
    log("作者：saiGou_14H")

    try:
        config = configparser.ConfigParser()  # 实例化解析对象
        config.read("config.ini", encoding='utf-8')  # 读文件
        account = config.get('Login', 'account')
        password = config.get('Login', 'password')
        type = config.get('Config', 'type')
        is_verify = config.get('Config', 'is_verify')
        try:
            type = True if type == '1' else False
            is_verify = True if is_verify == '1' else False
        except Exception as e:
            log("config.ini配置文件格式错误！")
        log("检测到config.ini配置文件,账号密码已自动填充！")
    except Exception as e:
        log("未检测到config.ini配置文件或配置文件格式错误,请手动输入配置信息！")
        account = input(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]请输入账号：')
        password = input(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]请输入密码：')
        type = 1
        is_verify = 0
        while True:
            type = input(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]是否优先前排,反之后排[1是 0否]:')
            if type == '1' or type == '0':
                type = True if type == '1' else False
                break
            else:
                log("输入错误，请重新输入!")
        while True:
            is_verify = input(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]是否需要验证码验证[1是 0否]:')
            if is_verify == '1' or is_verify == '0':
                is_verify = True if is_verify == '1' else False
                break
            else:
                log("输入错误，请重新输入!")
    print(getDateTime())
    if account !="20233709057":
        x = md52(getDateTime())
        s = input(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]请输入密钥：')
    if account == "20233709057" or x == s:
        log("密钥验证成功")

        bus = BUS(getDateTime(), account, password, type, is_verify)
        if bus.isLogin:
            input(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]回车以开始倒计时')
            log(f'正在进行中时（请勿关闭）')
            pre_s_time = -1
            while True:
                try:
                    # 获取当前时间
                    T = getTime()
                    if T[1] >= '29' and T[0] >= '17':
                        s = 60 - int(T[2])
                        if pre_s_time != s and T[0] == '17' and T[1] == '29':
                            log(f"倒计时：{s}")
                            pre_s_time = s
                        if bus.run():
                            break
                except Exception as err:
                    log(err)
    else:
        log("密钥验证失败")
    input(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]请按回车键关闭程序')

