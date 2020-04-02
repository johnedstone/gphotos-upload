#!/usr/bin/env python

import logging
import sys

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from settings.chrome_settings import chrome_options, executable_path

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(level=logging.INFO)
def get_source(driver):
    import time
    time.sleep(5)
    logging.info('source: {}'.format(driver.page_source))
    driver.save_screenshot('screenshot_source.png')
    sys.exit()

def open(*args, **kwargs):
    try:
        driver = webdriver.Chrome(executable_path=executable_path,
            options=chrome_options)
        args = list(args)
        auth_url = args[0]
        # auth_url = 'https://www.whatismybrowser.com/detect/is-javascript-enabled'
        driver.get(auth_url)
        logging.debug('Page Title: {}'.format(driver.title))
        logging.debug('Current URL: {}'.format(driver.current_url))
        screenshot = 'screenshot_waiting_for_email.png'
        driver.save_screenshot(screenshot)
        logging.debug('Screenshot: {}'.format(screenshot))

        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "Email")))
        element.send_keys('put_email_here')

        screenshot = 'screenshot_with_email.png'
        driver.save_screenshot(screenshot)
        logging.debug('Screenshot: {}'.format(screenshot))

        # alright_next = driver.find_element_by_xpath('//span[normalize-space(text()) = "Next"]')
        alright_next = driver.find_element_by_id('next')
        alright_next.click()
        screenshot = 'screenshot_waiting_on_passwd.png'
        driver.save_screenshot(screenshot)

        logging.debug('Screenshot: {}'.format(screenshot))
        logging.debug('source: {}'.format(driver.page_source))

        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "Passwd")))
        element.send_keys('put_password_here')
        sign_in = driver.find_element_by_id('signIn')
        sign_in.click()
        screenshot = 'screenshot_logged_in.png'
        driver.save_screenshot(screenshot)
        logging.debug('Screenshot: {}'.format(screenshot))

    except Exception as e:
        logging.error('Opening ...: {}'.format(e))
    finally:
        driver.quit()
        sys.exit('boo')

# vim: ai et ts=4 sw=4 sts=4 nu
