import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from .models import Category, Product


class SupermarketUITests(StaticLiveServerTestCase):
    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.maximize_window()
        self.driver.implicitly_wait(5)
        get_user_model().objects.create_user('worker', password='worker12345')
        category = Category.objects.create(name='Напої')
        self.water = Product.objects.create(
            name='Вода', price=Decimal('10.50'), stock_quantity=5, category=category)
        self.juice = Product.objects.create(
            name='Сік', price=Decimal('20.00'), stock_quantity=8, category=category)

    def tearDown(self):
        self.pause(3)
        self.driver.quit()

    def pause(self, seconds=1.5):
        time.sleep(seconds)

    def login(self):
        self.driver.get(self.live_server_url + '/accounts/login/')
        self.pause()
        self.driver.find_element(By.ID, 'id_username').send_keys('worker')
        self.pause()
        self.driver.find_element(By.ID, 'id_password').send_keys('worker12345')
        self.pause()
        self.driver.find_element(By.CSS_SELECTOR, 'form button.btn-brand').click()
        self.pause()

    def test_01_login_with_valid_credentials(self):
        self.login()
        title = self.driver.find_element(By.CSS_SELECTOR, 'h1.page-title').text
        user = self.driver.find_element(By.CSS_SELECTOR, '.user-meta .name').text
        self.assertEqual(title, 'Панель керування')
        self.assertEqual(user, 'worker')

    def test_02_create_order_and_pay(self):
        self.login()
        self.driver.find_element(By.CSS_SELECTOR, 'h1.page-title')
        self.driver.get(self.live_server_url + '/orders/add/')
        self.pause()
        Select(self.driver.find_element(By.ID, 'id_items-0-product')).select_by_value(str(self.water.pk))
        self.pause()
        self.driver.find_element(By.ID, 'id_items-0-quantity').send_keys('2')
        self.pause()
        Select(self.driver.find_element(By.ID, 'id_items-1-product')).select_by_value(str(self.juice.pk))
        self.pause()
        self.driver.find_element(By.ID, 'id_items-1-quantity').send_keys('1')
        self.pause()
        self.driver.find_element(By.CSS_SELECTOR, '#order-form button.btn-brand').click()
        self.pause()

        message = self.driver.find_element(By.CSS_SELECTOR, '.alert-success').text
        status = self.driver.find_element(By.CSS_SELECTOR, 'span.badge.fs-6').text
        self.assertIn('створено', message)
        self.assertEqual(status, 'Неоплачене')

        self.driver.find_element(By.XPATH, "//button[contains(., 'Оплачене')]").click()
        WebDriverWait(self.driver, 10).until(
            EC.text_to_be_present_in_element((By.CSS_SELECTOR, 'span.badge.fs-6'), 'Оплачене'))
        self.pause()

        self.water.refresh_from_db()
        self.juice.refresh_from_db()
        self.assertEqual(self.water.stock_quantity, 3)
        self.assertEqual(self.juice.stock_quantity, 7)