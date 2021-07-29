#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
# forked from SJang1/korea-covid-19-remaining-vaccine-macro
#
# major modified
# - async programming on vaccine find, reservation
# - logging result, error
# - timeout and retry on vaccine find
# - design pattern refactoring

# minor modified
# - console print formatting
# - adding debugging config
# - refactoring on duplicated or unnecessary code
'''

import asyncio
import webbrowser
import aiohttp
import logging

import browser_cookie3
import requests
import configparser
import json
import os
import sys
import time
from playsound import playsound
from datetime import datetime

import urllib3

# skip config for test or debug

search_time = 0.1  # 잔여백신을 해당 시간마다 한번씩 검색합니다. 단위: 초
urllib3.disable_warnings()
logging.basicConfig(filename='vaccine-run-kakao.log', level=logging.INFO, format='%(asctime)s %(message)s')


def close():
    print("프로그램을 종료하겠습니다.")
    input("Press Enter to close...")


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def play_tada():
    playsound(resource_path('tada.mp3'))


def json_print(json_string):
    json_object = json.loads(json_string)
    for org in json_object["organizations"]:
        if org.get('status') == "CLOSED" or org.get('status') == "EXHAUSTED":
            continue
        print(
            f"잔여갯수: {org.get('leftCounts')}\t상태: {org.get('status')}\t기관명: {org.get('orgName')}\t주소: {org.get('address')}")


class Headers:
    headers_map = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=utf-8",
        "Origin": "https://vaccine-map.kakao.com",
        "Accept-Language": "en-us",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 KAKAOTALK 9.3.8",
        "Referer": "https://vaccine-map.kakao.com/",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "Keep-Alive",
        "Keep-Alive": "timeout=5, max=1000"
    }
    headers_vacc = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=utf-8",
        "Origin": "https://vaccine.kakao.com",
        "Accept-Language": "en-us",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 KAKAOTALK 9.3.8",
        "Referer": "https://vaccine.kakao.com/",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "Keep-Alive",
        "Keep-Alive": "timeout=5, max=1000"
    }


async def try_reservation(vaccine_type, organization):

    if organization.get('status') != "AVAILABLE" and organization.get('leftCounts') == 0:
        return False

    logging.info(organization)
    print("%s에 %s를 예약을 진행합니다." % (organization['orgName'], vaccine_type))

    organization_code = organization.get('orgCode')
    reservation_url = 'https://vaccine.kakao.com/api/v1/reservation'
    data = {"from": "Map", "vaccineCode": vaccine_type, "orgCode": organization_code, "distance": "null"}

    cookies = requests.utils.dict_from_cookiejar(cookiejar)

    async with aiohttp.ClientSession() as session:
        async with session.post(reservation_url, data=json.dumps(data), headers=Headers.headers_vacc, cookies=cookies, verify_ssl=False) as response:
            response_json = await response.json()
            logging.info(response_json)

            if 'code' in response_json:
                if response_json['code'] == "SUCCESS":
                    print("신청이 완료되었습니다.")
                    organization_code_success = response_json.get("organization")
                    logging.info("SUCCESS %s %s" % (organization['orgName'], vaccine_type))
                    print(
                        f"병원이름: {organization_code_success.get('orgName')}\t전화번호: {organization_code_success.get('phoneNumber')}\t주소: {organization_code_success.get('address')}\t운영시간: {organization_code_success.get('openHour')}")
                    play_tada()
                    return True
                else:
                    print(response_json['desc'])
                    return False
            else:
                print("ERROR. 응답이 없습니다.")
                return False



async def find_vaccine(vaccine_type, top_x, top_y, bottom_x, bottom_y):
    url = 'https://vaccine-map.kakao.com/api/v2/vaccine/left_count_by_coords'
    data = {"bottomRight": {"x": bottom_x, "y": bottom_y}, "onlyLeft": False, "order": "latitude",
            "topLeft": {"x": top_x, "y": top_y}}

    print("--------------------------------------------------")
    print("잔여백신 조회를 시작하겠습니다.")

    while True:
        try:
            time.sleep(search_time)
            start_time = time.time()
            try:
                response = requests.post(url, data=json.dumps(data), headers=Headers.headers_map, verify=False, timeout=5)
                json_data = json.loads(response.text).get("organizations")
            except requests.exceptions.Timeout:
                print("병원 검색이 원활하지 않습니다. 재검색 하겠습니다.")
                continue
            end_time = time.time()

            print("--------------------------------------------------")
            print(datetime.now())
            print("조회 병원 수 : %d " % len(json_data), "검색 시간 : %s 초" % round((end_time-start_time), 3))

# Future Work
# need managing each 'try_reservation' async
# one of them return True(as 'success'), then cancel others
            result = await asyncio.gather(*[try_reservation(vaccine_type, x) for x in json_data])
            if True in result:
                break

        except requests.exceptions.ConnectionError as connectionerror:
            print("Connecting Error : ", connectionerror)
            logging.error(connectionerror)
            close()

        except requests.exceptions.HTTPError as httperror:
            print("Http Error : ", httperror)
            logging.error(httperror)
            close()

        except requests.exceptions.SSLError as sslerror:
            print("SSL Error : ", sslerror)
            logging.error(sslerror)
            close()

        except requests.exceptions.RequestException as error:
            print("AnyException : ", error)
            logging.error(error)
            close()


class kakao_user_info:
    def __init__(self):
        self._user_cookiejar = None
        self._user_cookie = None
        self._user_name = ""
        self._user_status = ""

    def load(self):
        self.__load_cookie()
        self.__load_kakao_info()

    def __load_cookie(self):
        self._user_cookiejar = browser_cookie3.chrome(domain_name=".kakao.com")
        self._user_cookie = requests.utils.dict_from_cookiejar(self._user_cookiejar)

    def __reload_cookie(self):
        self.__load_cookie()

    def __load_kakao_info(self):
        while True:
            user_info_api = 'https://vaccine.kakao.com/api/v1/user'
            user_info_response = requests.get(user_info_api, headers=Headers.headers_vacc, cookies=self._user_cookiejar, verify=False)
            user_info_json = json.loads(user_info_response.text)

            if user_info_json.get('error'):
                logging.info("사용자 정보를 불러오는데 실패하였습니다.")
                print("사용자 정보를 불러오는데 실패하였습니다.")
                print("Chrome 브라우저에서 카카오에 제대로 로그인되어있는지 확인해주세요.")
                print("로그인이 되어 있는데도 안된다면, 카카오톡에 들어가서 잔여백신 알림 신청을 한번 해보세요. 정보제공 동의가 나온다면 동의 후 다시 시도해주세요.")

                webbrowser.open('https://accounts.kakao.com/login?continue=https://vaccine-map.kakao.com/map2?v=1')
                login_try = str.lower(input("로그인을 완료하셨습니까? Y/N"))
                if login_try == "y":
                    self.__reload_cookie()
                    continue
                elif "y" == str.lower(input("종료하시겠습니까? Y/N")):
                    return False
                else:
                    print("입력이 잘못되었습니다. 사용자 정보를 다시 불러옵니다.")
            else:
                user_info = user_info_json.get("user")
                self._user_name = user_info['name']
                self._user_status = user_info['status']

                logging.info("사용자 정보를 불러오는데 성공했습니다.")
                print("사용자 정보를 불러오는데 성공했습니다.")
                break
        return True



    def get_cookiejar(self):
        return self._user_cookiejar

    def get_cookie(self):
        return self._user_cookie

    def get_user_status(self):
        return self._user_status



class vaccine_reservation:
    def __init__(self):

    async def try_reservation(self):

    async def find_vaccine(self):


class config_vaccine_reservation:
    def __init__(self):
        self._vaccine_type = ""
        self._top_left_longitude = ""
        self._top_left_latitude = ""
        self._bottom_right_longitude = ""
        self._bottom_right_latitude = ""

    def __dump_config(self, vaccine_type,
                    _top_left_longitude, _top_left_latitude,
                    _bottom_right_longitude, _bottom_right_latitude):
        config_parser = configparser.ConfigParser()
        config_parser['config'] = {}
        conf = config_parser['config']
        conf['vaccine_type'] = vaccine_type
        conf['top_left_longitude'] = _top_left_longitude
        conf['top_left_latitude'] = _top_left_latitude
        conf['bottom_right_longitude'] = _bottom_right_longitude
        conf['bottom_right_latitude'] = _bottom_right_latitude

        with open("config.ini", "w") as config_file:
            config_parser.write(config_file)
        return True

    def __set_config(self):
        while True:
            print("\n아래 예약이 가능한 백신종류입니다.")
            print("화이자          : 1")
            print("모더나          : 2")
            print("아스크라제네카    : 3")
            print("얀센            : 4")

            user_input = input("예약시도 진행할 백신을 알려주세요.")
            if user_input == 1:
                self._vaccine_type = "VEN00013"
                break
            elif user_input == 2:
                self._vaccine_type = "VEN00014"
                break
            elif user_input == 3:
                self._vaccine_type = "VEN00015"
                break
            elif user_input == 4:
                self._vaccine_type = "VEN00016"
                break
            else:
                print("올바른 백신을 골라주세요.")

        print("\n잔여백신을 조회할 범위(좌표)를 입력하세요. ")

        self._top_left_longitude = input(f"조회할 범위의 좌측상단 경도(x)값을 넣어주세요. ex) 127.~~: ").strip()
        print(self._top_left_longitude)

        self._top_left_latitude = input(f"조회할 범위의 좌측상단 위도(y)값을 넣어주세요 ex) 37.~~: ").strip()
        print(self._top_left_latitude)

        self._bottom_right_longitude = input(f"조회할 범위의 우측하단 경도(x)값을 넣어주세요 ex) 127.~~: ").strip()
        print(self._bottom_right_longitude)

        self._bottom_right_latitude = input(f"조회할 범위의 우측하단 위도(y)값을 넣어주세요 ex) 37.~~: ").strip()
        print(self._bottom_right_latitude)

        self.__dump_config(self._vaccine_type,
                           self._top_left_longitude, self._top_left_latitude,
                           self._bottom_right_longitude, self._bottom_right_latitude)
        return True

    def load_config(self):
        config_parser = configparser.ConfigParser()
        while os.path.exists('config.ini'):
            try:
                config_parser.read('config.ini')
                config = config_parser['config']
                pre_vaccine_type = config['vaccine_type']
                pre_top_left_longitude = config['top_left_longitude']
                pre_top_left_latitude = config['top_left_latitude']
                pre_bottom_right_longitude = config['bottom_right_longitude']
                pre_bottom_right_latitude = config['bottom_right_latitude']

            except configparser.Error as error:
                logging.warning(error)
                print("설정파일을 읽는동안 에러가 발생하였습니다.")
                print("설정을 다시 입력해주세요.")
                return self.__set_config()

            print("----------------------------------------")
            print("예약할 백신 : %s" % pre_vaccine_type)
            print("조회할 좌측상단 경도(x)값 : %s" % pre_top_left_longitude)
            print("조회할 좌측상단 위도(y)값 : %s" % pre_top_left_latitude)
            print("조회할 우측하단 경도(x)값 : %s" % pre_bottom_right_longitude)
            print("조회할 우측하단 위도(y)값 : %s" % pre_bottom_right_latitude)
            use_dump_config = str.lower(input("기존에 입력한 위 정보로 재검색하시겠습니까? Y/N : "))

            if use_dump_config == "y":
                self._vaccine_type = pre_vaccine_type
                self._top_left_longitude = pre_top_left_longitude
                self._top_left_latitude = pre_top_left_latitude
                self._bottom_right_longitude = pre_bottom_right_longitude
                self._bottom_right_latitude = pre_bottom_right_latitude
                return True
            elif use_dump_config == "n":
                return self.__set_config()
            else:
                print("잘못된 입력입니다. Y 또는 N을 입력해 주세요.")

        print("백신조회를 위한 기본설정을 진행하겠습니다.")
        self.__set_config()



def main():
    print("사용자 정보를 불러오고 있습니다.")
    user_info = kakao_user_info()
    user_info.load()

    if user_info.get_user_status() == None:
        logging.info("사용자 정보가 올바르지 않습니다.")
        print("사용자 정보가 올바르지 않습니다.")
        return close()
    elif user_info.get_user_status() == "ALREADY_RESERVED":
        logging.info("이미 접종이 완료되었거나 예약이 완료된 사용자입니다.")
        print("이미 접종이 완료되었거나 예약이 완료된 사용자입니다.")
        return close()


    #load config

    #search and reserve vaccine




    asyncio.run(find_vaccine(vaccine_type, top_x, top_y, bottom_x, bottom_y))





    return close()


# ===================================== run ===================================== #
if __name__ == '__main__':
    main()
