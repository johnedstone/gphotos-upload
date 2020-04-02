'''
References:
https://crossbrowsertesting.com/blog/test-automation/automate-login-with-selenium/
'''

import os
from selenium.webdriver.chrome.options import Options

CHROM_VERBOSITY = 0 # default was 99
CHROM_VERBOSITY = 99 # default was 99

# 1280,1696
# 1920,1280
ORIGINAL_WINDOW_SIZE_WIDTH = 1920
ORIGINAL_WINDOW_SIZE_HEIGHT = 1080

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size={}x{}'.format(
        ORIGINAL_WINDOW_SIZE_WIDTH,
        ORIGINAL_WINDOW_SIZE_HEIGHT))
#chrome_options.add_argument('--start-fullscreen')
chrome_options.add_argument('--user-data-dir=/tmp/user-data')
chrome_options.add_argument('--hide-scrollbars')
chrome_options.add_argument('--enable-logging')
chrome_options.add_argument('--log-level=0')
chrome_options.add_argument('--v={}'.format(CHROM_VERBOSITY))
chrome_options.add_argument('--single-process')
chrome_options.add_argument('--data-path=/tmp/data-path')
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument('--homedir=/tmp')
chrome_options.add_argument('--disk-cache-dir=/tmp/cache-dir')

executable_path = os.getcwd() + '/bin/chromedriver'

# Default: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.116 Safari/537.36
# chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:73.0) Gecko/20100101 Firefox/73.0')
# Default: chrome_options.add_argument('--enable-javascript')
#application/x-www-form-urlencoded;charset=utf-8
# chrome_options.add_argument('User-Agent=Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:74.0) Gecko/20100101 Firefox/74.0')
#chrome_options.add_argument('User-Agent=Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.10136')
#chrome_options.add_argument('Content-Type=application/x-www-form-urlencoded;charset=utf-8')
#chrome_options.add_argument('Accept-Language=en-US,en;q=0.5')
#chrome_options.add_argument('Accept-Encoding=gzip, deflate, br')
