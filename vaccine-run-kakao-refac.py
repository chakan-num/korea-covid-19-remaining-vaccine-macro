#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
# forked from SJang1/korea-covid-19-remaining-vaccine-macro
#
# major modified
 - async programming on vaccine find, reservation
 - logging result, error
 - timeout and retry on vaccine find
 - design pattern refactoring

# minor modified
 - console print formatting
 - adding debugging config
'''

import asyncio
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

# skip config for debug
debug_config = False

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
            f"잔여갯수: {org.get('leftCounts')}\t"
            f"상태: {org.get('status')}\t"
            f"기관명: {org.get('orgName')}\t"
            f"주소: {org.get('address')}")


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
            user_info_response = requests.get(user_info_api,
                                              headers=Headers.headers_vacc, cookies=self._user_cookiejar,
                                              verify=False)
            user_info_json = json.loads(user_info_response.text)

            if user_info_json.get('error'):
                logging.info("사용자 정보를 불러오는데 실패하였습니다.")
                print("사용자 정보를 불러오는데 실패하였습니다.")
                print("Chrome 브라우저에서 카카오에 제대로 로그인되어있는지 확인해주세요.")
                print("로그인이 되어 있는데도 안된다면, 카카오톡에 들어가서 잔여백신 알림 신청을 한번 해보세요. "
                      "정보제공 동의가 나온다면 동의 후 다시 시도해주세요.")

                # TODO: cookie reload after login
                '''
                webbrowser.open('https://accounts.kakao.com/login?continue=https://vaccine-map.kakao.com/map2?v=1')
                login_try = str.lower(input("로그인을 완료하셨습니까? Y/N"))
                if login_try == "y":
                    self.__reload_cookie()
                    continue
                elif "y" == str.lower(input("종료하시겠습니까? Y/N")):
                    return False
                else:
                    print("입력이 잘못되었습니다. 사용자 정보를 다시 불러옵니다.")
                '''
                return False
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
    def __init__(self, user_info):
        self._user_info = user_info
        self._config = config_vaccine_reservation()
        self._config.load_config()

        self.search_interval = 0.1  # 잔여백신을 해당 시간마다 한번씩 검색합니다. 단위: 초
        self.request_error_count = 0
        self.request_error_limit = 5

    async def find_vaccine(self):
        url = 'https://vaccine-map.kakao.com/api/v2/vaccine/left_count_by_coords'
        data = {"bottomRight": {"x": self._config.bottom_right_longitude,
                                "y": self._config.bottom_right_latitude},
                "topLeft": {"x": self._config.top_left_longitude,
                            "y": self._config.top_left_latitude},
                "onlyLeft": False, "order": "latitude"}

        print("--------------------------------------------------")
        print("잔여백신 조회를 시작하겠습니다.")

        while True:
            try:
                await asyncio.sleep(self.search_interval)
                start_time = time.time()
                try:
                    response = requests.post(url,
                                             data=json.dumps(data), headers=Headers.headers_map,
                                             verify=False, timeout=5)
                    json_data = json.loads(response.text).get("organizations")
                except requests.exceptions.Timeout:
                    print("병원 검색이 원활하지 않습니다. 재검색 하겠습니다.")
                    continue
                end_time = time.time()

                print("--------------------------------------------------")
                print(datetime.now())
                print("조회 병원 수 : %d " % len(json_data),
                      "검색 시간 : %s 초" % round((end_time - start_time), 3))

                # Future Work
                # need managing each 'try_reservation' async
                # one of them return True(as 'success'), then cancel others
                result = await asyncio.gather(*[self._try_reservation(org) for org in json_data])
                if True in result:
                    break

            except requests.exceptions.RequestException as error:
                print("RequestException : ", error)
                logging.warning(error)
                self.request_error_count += 1
                if self.request_error_count >= self.request_error_limit:
                    logging.error("too many request error")
                    break
                else:
                    continue
            except Exception as exception:
                print("Exception : ", exception)
                logging.error("Exception error : %s" % exception)
                sys.exit(-1)

    async def _try_reservation(self, org):
        if org.get('status') != "AVAILABLE" and org.get('leftCounts') == 0:
            return False

        logging.info("잔여백신 병원정보 : %s" % org)
        print("%s에 %s를 예약을 진행합니다." % (org['orgName'], self._config.vaccine_type))

        organization_code = org.get('orgCode')
        reservation_url = 'https://vaccine.kakao.com/api/v1/reservation'
        data = {"from": "Map", "vaccineCode": self._config.vaccine_type, "orgCode": organization_code,
                "distance": "null"}

        async with aiohttp.ClientSession() as session:
            async with session.post(reservation_url, data=json.dumps(data), headers=Headers.headers_vacc,
                                    cookies=self._user_info.get_cookie(), verify_ssl=False) as response:
                response_json = await response.json()
                logging.info(response_json)

                if 'code' in response_json:
                    if response_json['code'] == "SUCCESS":
                        print("신청이 완료되었습니다.")
                        organization_code_success = response_json.get("organization")
                        logging.info("SUCCESS %s %s" % (org['orgName'], self._config.vaccine_type))
                        print(
                            f"병원이름: {organization_code_success.get('orgName')}\t"
                            f"전화번호: {organization_code_success.get('phoneNumber')}\t"
                            f"주소: {organization_code_success.get('address')}\t"
                            f"운영시간: {organization_code_success.get('openHour')}")
                        play_tada()
                        return True
                    else:
                        print(response_json['desc'])
                        return False
                else:
                    print("ERROR. 응답이 없습니다.")
                    return False


class config_vaccine_reservation:
    def __init__(self):
        self.vaccine_type = ""
        self.top_left_longitude = ""
        self.top_left_latitude = ""
        self.bottom_right_longitude = ""
        self.bottom_right_latitude = ""

    def __dump_config(self):
        config_parser = configparser.ConfigParser()
        config_parser['config'] = {}
        conf = config_parser['config']
        conf['vaccine_type'] = self.vaccine_type
        conf['top_left_longitude'] = self.top_left_longitude
        conf['top_left_latitude'] = self.top_left_latitude
        conf['bottom_right_longitude'] = self.bottom_right_longitude
        conf['bottom_right_latitude'] = self.bottom_right_latitude

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
            try:
                user_input = int(user_input)
            except ValueError:
                print("올바른 백신을 골라주세요.")

            if user_input == 1:
                self.vaccine_type = "VEN00013"
                break
            elif user_input == 2:
                self.vaccine_type = "VEN00014"
                break
            elif user_input == 3:
                self.vaccine_type = "VEN00015"
                break
            elif user_input == 4:
                self.vaccine_type = "VEN00016"
                break
            else:
                print("올바른 백신을 골라주세요.")

        print("\n잔여백신을 조회할 범위(좌표)를 입력하세요. ")

        self.top_left_longitude = \
            input(f"조회할 범위의 좌측상단 경도(x)값을 넣어주세요. ex) 127.~~: ").strip()
        print(self.top_left_longitude)

        self.top_left_latitude = \
            input(f"조회할 범위의 좌측상단 위도(y)값을 넣어주세요 ex) 37.~~: ").strip()
        print(self.top_left_latitude)

        self.bottom_right_longitude = \
            input(f"조회할 범위의 우측하단 경도(x)값을 넣어주세요 ex) 127.~~: ").strip()
        print(self.bottom_right_longitude)

        self.bottom_right_latitude = \
            input(f"조회할 범위의 우측하단 위도(y)값을 넣어주세요 ex) 37.~~: ").strip()
        print(self.bottom_right_latitude)

        self.__dump_config()
        return True

    def load_config(self):
        if debug_config:
            self.vaccine_type = "VEN00013"
            '''2
            self.top_left_longitude = 126.87761193824504
            self.top_left_latitude = 37.49369473195565
            self.bottom_right_longitude = 126.87214034327664
            self.bottom_right_latitude = 37.49806590215318
            '''
            self.top_left_longitude = 126.91759051002093
            self.top_left_latitude = 37.47654763831696
            self.bottom_right_longitude = 126.83878401599266
            self.bottom_right_latitude = 37.539490173708266
            return True

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
                self.vaccine_type = pre_vaccine_type
                self.top_left_longitude = pre_top_left_longitude
                self.top_left_latitude = pre_top_left_latitude
                self.bottom_right_longitude = pre_bottom_right_longitude
                self.bottom_right_latitude = pre_bottom_right_latitude
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

    if user_info.get_user_status() is None:
        logging.info("사용자 정보가 올바르지 않습니다.")
        print("사용자 정보가 올바르지 않습니다.")
        return close()
    elif user_info.get_user_status() == "ALREADY_RESERVED":
        logging.info("이미 접종이 완료되었거나 예약이 완료된 사용자입니다.")
        print("이미 접종이 완료되었거나 예약이 완료된 사용자입니다.")
        return close()

    vacc_reserve = vaccine_reservation(user_info)
    asyncio.run(vacc_reserve.find_vaccine())

    return close()


# ===================================== run ===================================== #
if __name__ == '__main__':
    main()
