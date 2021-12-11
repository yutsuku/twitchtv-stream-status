import sys
import re
import json
import time
import argparse
import random
import traceback
from datetime import datetime
from urllib import request
from requests import ConnectionError
from socket import gethostbyname, gaierror

def custom_sleep(start_time, attempts, timeout_max_sleep):
    wasted_time = int(time.time() - start_time)
    sleep_time = 60 + (60 * attempts / 2)

    if timeout_max_sleep > 0 and sleep_time > timeout_max_sleep:
        sleep_time = timeout_max_sleep

    jitter = int(sleep_time * 0.1) or 1
    jitter = random.randrange(0, jitter)

    if random.randrange(0, 1) == 1:
        sleep_time = sleep_time + jitter
    else:
        sleep_time = sleep_time - jitter
        if sleep_time < 0:
            if timeout_max_sleep > 0:
                sleep_time = timeout_max_sleep
            else:
                sleep_time = 60
    return sleep_time, wasted_time

def get_stream_status(full_url, client_id):
    # https://twitch.tv/some_user => some_user
    full_url = full_url.split('/')[3]

    data = json.dumps([{
        "operationName": "UseLive",
        "variables": {
            "channelLogin": full_url
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "639d5f11bfb8bf3053b424d9ef650d04c4ebb7d94711d644afb08fe9a0fad5d9"
            }
        }
    }]).encode('utf8')

    req = request.Request('https://gql.twitch.tv/gql', data=data)
    req.add_header('Client-Id', client_id)

    result = None
    status = None
    startTime = None

    try:
        res = request.urlopen(req)
        result = json.loads(res.read().decode('utf8'))
    except:
        pass

    if result is None:
        return result, startTime

    try:
        status = result['playabilityStatus']['status']
    except:
        pass

    try:
        status = result[0]['data']['user']['stream']['__typename']
    except:
        pass

    try:
        startTime = result[0]['data']['user']['stream']['createdAt']
    except:
        pass

    return status, startTime

def get_client_id(url, quiet=False):
    if not quiet:
        print('Fetching page...')

    regex_client_id = r"clientId=\"([^\"]+)\""
    page_source = None
    client_id = None

    try:
        page_source = request.urlopen(url).read().decode('utf8')
    except:
        return client_id
        pass

    client_id = re.findall(regex_client_id, page_source, re.MULTILINE)

    if len(client_id) == 0:
        client_id = None
    else:
        client_id = client_id[0]

    return client_id

def is_stream_online(url, connection_timeout, quiet=False, wait=False, verbose=False, timeout_max_sleep=0):
    client_id = None
    start_time = time.time()
    attempts = 0

    while True:
        attempts += 1
        if verbose:
            print('[{}] Attempting to fetch basic information. Attempt {}'.format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), attempts))
        client_id = get_client_id(url, quiet)

        if client_id:
            break
        else:
            sleep_time, wasted_time = custom_sleep(start_time, attempts, timeout_max_sleep)

            if not wait:
                raise Exception('Unable to fetch base info after {} seconds and {} attempts'.format(wasted_time, attempts))
            if time.time() > start_time + connection_timeout:
                raise Exception('Unable to fetch base info after {} seconds and {} attempts'.format(wasted_time, attempts))
            time.sleep(sleep_time)

    if verbose:
        print('Client ID:', client_id)

    if not quiet:
        print('Checking for stream status')

    attempts = 0

    while True:
        attempts += 1
        if verbose:
            print('[{}] Fetching stream status. Attempt {}'.format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), attempts))

        status, startTime = get_stream_status(url, client_id)
        is_online = status

        if not quiet:
            print(status)

        if not wait or is_online:
            return is_online

        if time.time() > start_time + connection_timeout:
            raise Exception('Unable to fetch stream status after {} seconds and {} attempts'.format(wasted_time, attempts))

        if wait and not is_online:
            sleep_time, wasted_time = custom_sleep(start_time, attempts, timeout_max_sleep)
            if verbose:
                print('zZz... ', sleep_time)
            time.sleep(sleep_time)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-q', '--quiet', help='Do not output anything to stdout', action='store_true')
    group.add_argument('--verbose', help='Print heartbeat to stdout for debugging', action='store_true')

    parser.add_argument('-w', '--wait', help='Keep polling until the stream starts, then exit', action='store_true')
    parser.add_argument('--timeout', help='How long to wait in case network fails (in seconds). 5 minutes by default', type=int, nargs='?', const=300, default=300)
    parser.add_argument('--timeout-max-sleep', help='Maximum allowed idle time (in seconds) between failed network requests. Infinite by default', type=int, nargs='?', const=0, default=0)
    parser.add_argument('url', help='https://twitch.tv/your_profile', type=str)

    args = parser.parse_args()

    if args.verbose:
        print(args)
    try:
        if is_stream_online(args.url, args.timeout, quiet=args.quiet, wait=args.wait, verbose=args.verbose, timeout_max_sleep=args.timeout_max_sleep):
            sys.exit(0)
    except Exception as e:
        if not args.quiet:
            print('Terminating')
            if hasattr(e, 'message'):
                print(e.message)
            else:
                print(e)
            traceback.print_exception(type(e), e, e.__traceback__)
        pass
    sys.exit(2)
