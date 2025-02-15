#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
# forked from SJang1/korea-covid-19-remaining-vaccine-macro
#
# major modified
# - async programming on vaccine find, reservation
# - logging result, error
# - timeout and retry on vaccine find

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
skip_config = False

search_time = 0.1  # 잔여백신을 해당 시간마다 한번씩 검색합니다. 단위: 초
urllib3.disable_warnings()
logging.basicConfig(filename='vaccine-run-kakao.log', level=logging.INFO, format='%(asctime)s %(message)s')

cookiejar = browser_cookie3.chrome(domain_name=".kakao.com")

# 기존 입력 값 로딩
def load_config():
    config_parser = configparser.ConfigParser()
    if os.path.exists('config.ini') and not skip_config:
        try:
            config_parser.read('config.ini')

            while True:
                skip_input = str.lower(input("기존에 입력한 정보로 재검색하시겠습니까? Y/N : "))
                if skip_input == "y":
                    skip_input = True
                    break
                elif skip_input == "n":
                    skip_input = False
                    break
                else:
                    print("Y 또는 N을 입력해 주세요.")

            if skip_input:
                # 설정 파일이 있으면 최근 로그인 정보 로딩
                configuration = config_parser['config']
                previous_used_type = configuration["VAC"]
                previous_top_x = configuration["topX"]
                previous_top_y = configuration["topY"]
                previous_bottom_x = configuration["botX"]
                previous_bottom_y = configuration["botY"]
                return previous_used_type, previous_top_x, previous_top_y, previous_bottom_x, previous_bottom_y
            else:
                return None, None, None, None, None
        except ValueError:
            print("config 에러 발생 : ", ValueError)
            return None, None, None, None, None
    return None, None, None, None, None


#TODO: get new cookie after login

def check_user_info_loaded():
    print("사용자 정보를 불러오고 있습니다.")

    while True:
        user_info_api = 'https://vaccine.kakao.com/api/v1/user'
        user_info_response = requests.get(user_info_api, headers=Headers.headers_vacc, cookies=cookiejar, verify=False)
        user_info_json = json.loads(user_info_response.text)
        if user_info_json.get('error'):
            logging.info("사용자 정보를 불러오는데 실패하였습니다.")
            print("사용자 정보를 불러오는데 실패하였습니다.")
            print("Chrome 브라우저에서 카카오에 제대로 로그인되어있는지 확인해주세요.")
            print("로그인이 되어 있는데도 안된다면, 카카오톡에 들어가서 잔여백신 알림 신청을 한번 해보세요. 정보제공 동의가 나온다면 동의 후 다시 시도해주세요.")
            '''
            webbrowser.open('https://accounts.kakao.com/login?continue=https://vaccine-map.kakao.com/map2?v=1')
            login_try = str.lower(input("로그인을 완료하셨습니까? Y/N"))
            if login_try == "y":
                self.cookiejar = browser_cookie3.chrome(domain_name=".kakao.com")
                continue
            elif "y" == str.lower(input("종료하시겠습니까? Y/N")):
                close()
            else:
                print("입력이 잘못되었습니다. 사용자 정보를 다시 불러옵니다.")
            '''
            close()
        else:
            user_info = user_info_json.get("user")

            if user_info['status'] == "NORMAL":
                logging.info("사용자 정보를 불러오는데 성공했습니다.")
                print("사용자 정보를 불러오는데 성공했습니다.")
                break
            else:
                print("이미 접종이 완료되었거나 예약이 완료된 사용자입니다.")
                logging.info("이미 접종이 완료되었거나 예약이 완료된 사용자입니다.")
                close()
'''


def check_user_info_loaded():
    user_info_api = 'https://vaccine.kakao.com/api/v1/user'
    user_info_response = requests.get(user_info_api, headers=Headers.headers_vacc, cookies=cookiejar, verify=False)
    user_info_json = json.loads(user_info_response.text)

    if user_info_json.get('error'):
        logging.info("사용자 정보를 불러오는데 실패하였습니다.")
        print("사용자 정보를 불러오는데 실패하였습니다.")
        print("Chrome 브라우저에서 카카오에 제대로 로그인되어있는지 확인해주세요.")
        print("로그인이 되어 있는데도 안된다면, 카카오톡에 들어가서 잔여백신 알림 신청을 한번 해보세요. 정보제공 동의가 나온다면 동의 후 다시 시도해주세요.")
        close()
    else:
        user_info = user_info_json.get("user")
        for key in user_info:
            value = user_info[key]
            # print(key, value)
            if key != 'status':
                continue
            if key == 'status' and value == "NORMAL":
                logging.info("사용자 정보를 불러오는데 성공했습니다.")
                print("사용자 정보를 불러오는데 성공했습니다.")
                break
            else:
                logging.info("이미 접종이 완료되었거나 예약이 완료된 사용자입니다.")
                print("이미 접종이 완료되었거나 예약이 완료된 사용자입니다.")
                close()
'''


def input_config():
    if skip_config:
        vaccine_type = "VEN00013"
        top_x = 126.87761193824504
        top_y = 37.49369473195565
        bottom_x = 126.87214034327664
        bottom_y = 37.49806590215318
        return vaccine_type, top_x, top_y, bottom_x, bottom_y

    vaccine_type = None
    while vaccine_type is None:
        print("아래 예약이 가능한 백신종류입니다.")
        print("화이자          : 1")
        print("모더나          : 2")
        print("아스크라제네카    : 3")
        print("얀센            : 4")

        user_input = input("예약시도 진행할 백신을 알려주세요.")
        if user_input == 1:
            vaccine_type = "VEN00013"
        elif user_input == 2:
            vaccine_type = "VEN00014"
        elif user_input == 3:
            vaccine_type = "VEN00015"
        elif user_input == 4:
            vaccine_type = "VEN00016"
        else:
            print("올바른 백신을 골라주세요.")
            vaccine_type = None

    print("잔여백신을 조회할 범위(좌표)를 입력하세요. ")
    top_x = None
    while top_x is None:
        top_x = input(f"조회할 범위의 좌측상단 경도(x)값을 넣어주세요. ex) 127.~~: ").strip()

    top_y = None
    while top_y is None:
        top_y = input(f"조회할 범위의 좌측상단 위도(y)값을 넣어주세요 ex) 37.~~: ").strip()

    bottom_x = None
    while bottom_x is None:
        bottom_x = input(f"조회할 범위의 우측하단 경도(x)값을 넣어주세요 ex) 127.~~: ").strip()

    bottom_y = None
    while bottom_y is None:
        bottom_y = input(f"조회할 범위의 우측하단 위도(y)값을 넣어주세요 ex) 37.~~: ").strip()

    dump_config(vaccine_type, top_x, top_y, bottom_x, bottom_y)
    return vaccine_type, top_x, top_y, bottom_x, bottom_y


def dump_config(vaccine_type, top_x, top_y, bottom_x, bottom_y):
    config_parser = configparser.ConfigParser()
    config_parser['config'] = {}
    conf = config_parser['config']
    conf['VAC'] = vaccine_type
    conf["topX"] = top_x
    conf["topY"] = top_y
    conf["botX"] = bottom_x
    conf["botY"] = bottom_y

    with open("config.ini", "w") as config_file:
        config_parser.write(config_file)


def close():
    print("프로그램을 종료하겠습니다.")
    input("Press Enter to close...")
    sys.exit()



def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def play_tada():
    playsound(resource_path('tada.mp3'))


def pretty_print(json_string):
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



def main():
    check_user_info_loaded()
    previous_used_type, previous_top_x, previous_top_y, previous_bottom_x, previous_bottom_y = load_config()
    if previous_used_type is None:
        vaccine_type, top_x, top_y, bottom_x, bottom_y = input_config()
    else:
        vaccine_type, top_x, top_y, bottom_x, bottom_y = previous_used_type, previous_top_x, previous_top_y, previous_bottom_x, previous_bottom_y
    asyncio.run(find_vaccine(vaccine_type, top_x, top_y, bottom_x, bottom_y))
    close()


# ===================================== run ===================================== #
if __name__ == '__main__':
    main()
