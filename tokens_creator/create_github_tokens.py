#!/usr/bin/env python
import os
import sys
import requests
import json
import re
import random
import string
import urllib.parse
import simpleaudio as sa
from time import sleep
from selenium import webdriver
from datetime import datetime

aai_token = os.environ['AAI_TOKEN']
browser_user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:81.0) Gecko/20100101 Firefox/81.0'

# Helper functions
def get_current_epoch():
    return float(datetime.now().strftime('%s.%f'))


def get_random_number(start, end):
    return int(random.random()*(end-start)+start)


def get_random_alphanumeric_string(length):
    letters_and_digits = string.ascii_lowercase + string.digits
    result_str = ''.join((random.choice(letters_and_digits)
                          for i in range(length)))
    return result_str


# GetNada API Functions
def get_messages(email):
    response = requests.get(f'https://getnada.com/api/v1/inboxes/{email}')
    data = json.loads(response.content)
    return [[msg_obj['uid'], msg_obj['s']] for msg_obj in data['msgs']]


def get_email_content(uid):
    response = requests.get(f'https://getnada.com/api/v1/messages/{uid}')
    data = json.loads(response.content)
    return data['html']


def get_verification_link(email):
    verification_email_uid = ''
    while not verification_email_uid:
        messages = get_messages(email)
        for uid, subject in messages:
            if re.match(r'^.*github.*verify.*email.*$', subject, re.IGNORECASE):
                verification_email_uid = uid

        if verification_email_uid:
            content = get_email_content(
                verification_email_uid).replace('\n', '')
            if re.match(r'^.*href="(https://github.com/users/[^"]+confirm_verification[^"]+)".*$', content):
                url = re.sub(
                    r'^.*href="(https://github.com/users/[^"]+confirm_verification[^"]+)".*$', r'\1', content)
                return url
            else:
                return ''
        else:
            sleep(1)

# Transcribes audio files using the API of AssemblyAI
def transcribe_audio(audio_data):
    # upload audio file to AssemblyAI
    try:
        response = requests.post('https://api.assemblyai.com/v2/upload',
                                 headers={'authorization': aai_token},
                                 data=audio_data,
                                 )
        audio_url = json.loads(response.content)['upload_url']

        # Submit audio file for transcription
        response = requests.post('https://api.assemblyai.com/v2/transcript',
                                 json={"audio_url": audio_url},
                                 headers={
                                     "authorization": aai_token,
                                     "content-type": "application/json"
                                 },
                                 )
        audio_file_id = json.loads(response.content)['id']

        while True:
            response = requests.get(f'https://api.assemblyai.com/v2/transcript/{audio_file_id}',
                                    headers={'authorization': aai_token},
                                    )
            data = json.loads(response.content)
            status = data['status']
            print(f'\rTranscribing audio file             : {status} ', end='')
            if status == 'completed':
                print(f'\rTranscribing audio file             : Done        ')
                captcha = re.sub(r'[^0-9]', '', data['text'])
                return captcha
            else:
                sleep(1)
    except:
        return ''


# Captcha Functions
def generate_funcaptcha_token(session_token):
    return urllib.parse.unquote_plus(f'{session_token}%7Cr%3Dus-east-1%7Cmetabgclr%3Dtransparent%7Cmaintxtclr%3D%2523cbccce%7Cmainbgclr%3D%2523fafbfc%7Cguitextcolor%3D%252324292e%7Cmetaiconclr%3D%2523cbccce%7Cmeta_height%3D311%7Cmeta_width%3D450%7Cmeta%3D10%7Cpk%3D69A21A01-CC7B-B9C6-0F9A-E7FA06677FFC%7Cat%3D40%7Catp%3D2%7Ccdn_url%3Dhttps%3A%2F%2Fcdn.arkoselabs.com%2Ffc%7Clurl%3Dhttps%3A%2F%2Faudio-us-east-1.arkoselabs.com%7Csurl%3Dhttps%3A%2F%2Fapi.funcaptcha.com')


def get_session_token():
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(
            "https://octocaptcha.com/?origin_page=github_signup&responsive=true&require_ack=true")
        while not re.match(r'.*https://api.funcaptcha.com/fc/gc/\?token=([^&]+)&amp;.*$', driver.page_source.replace('\n', '')):
            sleep(0.1)
        session_token = re.sub(
            r'.*https://api.funcaptcha.com/fc/gc/\?token=([^&]+)&amp;.*$', r'\1', driver.page_source.replace('\n', ''))
    except KeyboardInterrupt:
        driver.close()
        raise(KeyboardInterrupt)

    driver.close()
    return session_token


def get_audio_challenge(session_token):
    response = requests.get(f'https://api.funcaptcha.com/fc/get_audio/?session_token={session_token}&analytics_tier=40&r=us-east-1&game=0&language=en')
    return response.content


def verify_captcha(session_token, captcha):
    response = requests.post('https://api.funcaptcha.com/fc/audio/',
                             headers={'User-Agent': browser_user_agent,
                                      'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
                                      },
                             data=f'analytics_tier=40&language=en&r=us-east-1&response={captcha}&audio_type=2&session_token={session_token}'
                             )
    try:
        result = json.loads(response.content.decode())['response']
    except KeyError:
        print(f'Response = {response.content}')
        return False
    return result == 'correct'


# Github Functions
def verify_email(verification_link, cookies):
    response = requests.get(
        verification_link,
        headers={'User-Agent': browser_user_agent},
        cookies=cookies,
    )
    return response.status_code == 200


def create_api_token(cookies):
    response = requests.get(
        'https://github.com/settings/tokens/new', cookies=cookies)
    html = response.content.decode().replace('\n', '')
    cookies.update(response.cookies)

    if not re.match(r'^.*name="authenticity_token" value="([^"]+)".*$', html):
        print('Error finding authenticity_token in html')
        return ''
    auth_token = re.sub(
        r'^.*name="authenticity_token" value="([^"]+)".*$', r'\1', html)
    response = requests.post(
        'https://github.com/settings/tokens',
        cookies=cookies,
        headers={'User-Agent': browser_user_agent},
        data=f'authenticity_token={urllib.parse.quote_plus(auth_token)}&oauth_access%5Bdescription%5D=test123&oauth_access%5Bscopes%5D%5B%5D=repo&oauth_access%5Bscopes%5D%5B%5D=write%3Apackages&oauth_access%5Bscopes%5D%5B%5D=read%3Apackages&oauth_access%5Bscopes%5D%5B%5D=delete%3Apackages&oauth_access%5Bscopes%5D%5B%5D=admin%3Aorg&oauth_access%5Bscopes%5D%5B%5D=admin%3Apublic_key&oauth_access%5Bscopes%5D%5B%5D=admin%3Arepo_hook&oauth_access%5Bscopes%5D%5B%5D=admin%3Aorg_hook&oauth_access%5Bscopes%5D%5B%5D=gist&oauth_access%5Bscopes%5D%5B%5D=notifications&oauth_access%5Bscopes%5D%5B%5D=user&oauth_access%5Bscopes%5D%5B%5D=delete_repo&oauth_access%5Bscopes%5D%5B%5D=write%3Adiscussion&oauth_access%5Bscopes%5D%5B%5D=admin%3Aenterprise&oauth_access%5Bscopes%5D%5B%5D=workflow&oauth_access%5Bscopes%5D%5B%5D=admin%3Agpg_key',
    )

    html = response.content.decode().replace('\n', '')
    if not re.match(r'^.*class="token">([^<]+)<.*$', html):
        return ''
    else:
        new_token = re.sub(r'^.*class="token">([^<]+)<.*$', r'\1', html)

    return new_token


def create_new_account(user, email, password, funcaptcha_token):
    response = requests.get('https://github.com/join')
    html = response.content.decode().replace('\n', '')
    cookies = response.cookies

    authenticity_token = ''
    timestamp = ''
    timestamp_secret = ''
    required_field = ''
    for line in html.split('\n'):
        if re.match(r'^.*name="authenticity_token" value="([^"]+)".*$', line):
            authenticity_token = re.sub(
                r'^.*name="authenticity_token" value="([^"]+)".*$', r'\1', line)

        if re.match(r'^.*name="timestamp_secret" value="([^"]+)".*$', line):
            timestamp_secret = re.sub(
                r'^.*name="timestamp_secret" value="([^"]+)".*$', r'\1', line)

        if re.match(r'^.*name="timestamp" value="([^"]+)".*$', line):
            timestamp = re.sub(
                r'^.*name="timestamp" value="([^"]+)".*$', r'\1', line)

        if re.match(r'^.*type="text" name="(required_field_[^"]+)".*$', line):
            required_field = re.sub(
                r'^.*type="text" name="(required_field_[^"]+)".*$', r'\1', line)

    data = f'authenticity_token={urllib.parse.quote_plus(authenticity_token)}&user%5Blogin%5D={user}&user%5Bemail%5D={urllib.parse.quote_plus(email)}&user%5Bpassword%5D={urllib.parse.quote_plus(password)}&source=form-join&{required_field}=&timestamp={timestamp}&timestamp_secret={timestamp_secret}&octocaptcha-token={urllib.parse.quote_plus(funcaptcha_token)}'

    response = requests.post('https://github.com/join',
                             headers={'User-Agent': browser_user_agent,
                                      'Content-Type': 'application/x-www-form-urlencoded',
                                      'Origin': 'https://github.com',
                                      'Referer': 'https://github.com/join',
                                      },
                             data=data,
                             cookies=cookies,
                             allow_redirects=False,
                             )
    if 'cookies' in vars(response):
        cookies.update(response.cookies)

    if response.status_code == 302:
        return cookies


# Main
def main():

    one_time_email_domain = 'tafmail.com'

    saved_time = ''
    current_time = get_current_epoch()
    while True:
        print('Generating random user details      : ', end='')
        sys.stdout.flush()

        user = get_random_alphanumeric_string(get_random_number(8, 20))
        email = password = f'{user}@{one_time_email_domain}'
        print(email)

        print('Requesting Funcaptcha session token : ', end='')
        sys.stdout.flush()
        session_token = get_session_token()
        print(session_token)

        print('Requesting audio challange          : ', end='')
        sys.stdout.flush()
        audio_data = get_audio_challenge(session_token)
        print('Done')

        print('Transcribing audio file             : ', end='')
        sys.stdout.flush()
        captcha = transcribe_audio(audio_data)
        if not captcha:
            print('transcription failed')
            print('-'*40)
            saved_time = ''
            continue

        print(f'Captcha                             : {captcha}')

        current_time = get_current_epoch()
        if saved_time and current_time-saved_time < 61:
            diff = current_time-saved_time
            print(f'Sleeping {int(61-diff)} seconds to avoid rate limit..')
            sleep(61-diff)

        print('Verifying captcha is correct        : ', end='')
        sys.stdout.flush()
        result = verify_captcha(session_token, captcha)
        print(result)
        saved_time = get_current_epoch()

        if not result:
            print('-'*40)
            saved_time = ''
            continue
        funcaptcha_token = generate_funcaptcha_token(session_token)

        print('Creating a new account              : ', end='')
        sys.stdout.flush()
        cookies = create_new_account(user, email, password, funcaptcha_token)
        if not cookies:
            print('Failed')
            print('-'*40)
            saved_time = ''
            continue
        print(f'Success at {datetime.now()}')

        print('Looking for verification link       : ', end='')
        sys.stdout.flush()
        verification_link = get_verification_link(email)
        if not verification_link:
            print('Not found')
            print('-'*40)
            saved_time = ''
            continue
        print('Found')

        print('Verifying account                   : ', end='')
        sys.stdout.flush()
        if not verify_email(verification_link, cookies):
            print(f'Error')
            print('-'*40)
            saved_time = ''
            continue
        print('Success')

        print('Creating new API Token              : ', end='')
        sys.stdout.flush()
        api_token = create_api_token(cookies)
        print(api_token)
        with open('tokens-list.txt', 'a') as tokens_file:
            tokens_file.write(f'{api_token}\n')

        print('-'*40)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\r  \nInterrupted by Ctrl+C! \n")
