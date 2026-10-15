from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .forms import ProductForm
from .models import Category, Order, OrderItem, Product
from .permissions import WORKER_GROUP


class BaseCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser('a', password='p')
        self.worker = User.objects.create_user('w', password='p')
        self.worker.groups.add(Group.objects.create(name=WORKER_GROUP))
        self.cat = Category.objects.create(name='Напої')
        self.p1 = Product.objects.create(name='Вода', price=Decimal('10.50'), stock_quantity=5, category=self.cat)
        self.p2 = Product.objects.create(name='Сік', price=Decimal('20.00'), stock_quantity=3, category=self.cat)

    def login(self, user):
        self.client.force_login(user)

    def make_order(self, lines):
        order = Order.objects.create()
        for product, qty in lines:
            OrderItem.objects.create(order=order, product=product, quantity=qty, unit_price=product.price)
        order.recalculate_total()
        return order

    def stock(self, p):
        p.refresh_from_db()
        return p.stock_quantity


class ValidationTests(BaseCase):
    def test_negative_price_rejected(self):
        f = ProductForm({'name': 'X', 'category': self.cat.pk, 'price': '-1', 'stock_quantity': 1})
        self.assertFalse(f.is_valid())

    def test_negative_stock_rejected(self):
        f = ProductForm({'name': 'X', 'category': self.cat.pk, 'price': '1', 'stock_quantity': -3})
        self.assertFalse(f.is_valid())


class OrderLogicTests(BaseCase):
    def test_default_status_is_unpaid(self):
        self.assertEqual(self.make_order([(self.p1, 1)]).status, Order.UNPAID)

    def test_total_uses_item_prices(self):
        o = self.make_order([(self.p1, 2), (self.p2, 1)])
        self.assertEqual(o.total_amount, Decimal('41.00'))

    def test_price_snapshot_survives_price_change(self):
        o = self.make_order([(self.p1, 1)])
        self.p1.price = Decimal('99.00'); self.p1.save()
        o.recalculate_total()
        self.assertEqual(o.total_amount, Decimal('10.50'))

    def test_no_deduction_while_unpaid(self):
        self.make_order([(self.p1, 2)])
        self.assertEqual(self.stock(self.p1), 5)

    def test_paying_deducts_all_basket_items(self):
        o = self.make_order([(self.p1, 2), (self.p2, 1)])
        o.change_status(Order.PAID)
        self.assertEqual((self.stock(self.p1), self.stock(self.p2)), (3, 2))

    def test_paying_twice_is_refused_and_does_not_double_deduct(self):
        o = self.make_order([(self.p1, 2)])
        o.change_status(Order.PAID)
        with self.assertRaises(ValidationError):
            o.change_status(Order.PAID)
        self.assertEqual(self.stock(self.p1), 3)

    def test_back_to_unpaid_restores_stock(self):
        o = self.make_order([(self.p1, 2)])
        o.change_status(Order.PAID)
        o.change_status(Order.UNPAID)
        self.assertEqual(self.stock(self.p1), 5)
        o.change_status(Order.PAID)      # можна оплатити знову, списання знову одне
        self.assertEqual(self.stock(self.p1), 3)

    def test_insufficient_stock_on_payment(self):
        o = self.make_order([(self.p1, 4)])
        self.make_order([(self.p1, 4)]).change_status(Order.PAID)
        with self.assertRaises(ValidationError):
            o.change_status(Order.PAID)
        self.assertEqual(self.stock(self.p1), 1)

    def test_unique_product_per_order(self):
        o = self.make_order([(self.p1, 1)])
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderItem.objects.create(order=o, product=self.p1, quantity=1, unit_price=1)


class ViewTests(BaseCase):
    def order_post(self, lines):
        data = {'items-TOTAL_FORMS': len(lines), 'items-INITIAL_FORMS': 0,
                'items-MIN_NUM_FORMS': 0, 'items-MAX_NUM_FORMS': 1000}
        for i, (product, qty) in enumerate(lines):
            data[f'items-{i}-product'] = product.pk
            data[f'items-{i}-quantity'] = qty
        return self.client.post(reverse('order_create'), data)

    def test_login_required(self):
        self.assertEqual(self.client.get(reverse('product_list')).status_code, 302)

    def test_basket_with_many_products(self):
        self.login(self.worker)
        extra = [Product.objects.create(name=f'Т{i}', price=Decimal('1.00'), stock_quantity=9,
                                        category=self.cat) for i in range(6)]
        self.order_post([(self.p1, 1), (self.p2, 2)] + [(p, 3) for p in extra])
        o = Order.objects.get()
        self.assertEqual(o.items.count(), 8)
        self.assertEqual(o.total_amount, Decimal('10.50') + Decimal('40.00') + Decimal('18.00'))
        self.assertEqual(o.created_by, self.worker)
        self.assertEqual(self.stock(self.p1), 5)

    def test_order_more_than_stock_refused(self):
        self.login(self.worker)
        r = self.order_post([(self.p1, 6)])
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)

    def test_same_product_twice_refused(self):
        self.login(self.worker)
        self.order_post([(self.p1, 1), (self.p1, 1)])
        self.assertEqual(Order.objects.count(), 0)

    def test_empty_basket_refused(self):
        self.login(self.worker)
        self.client.post(reverse('order_create'), {
            'items-TOTAL_FORMS': 2, 'items-INITIAL_FORMS': 0,
            'items-MIN_NUM_FORMS': 0, 'items-MAX_NUM_FORMS': 1000})
        self.assertEqual(Order.objects.count(), 0)

    def test_status_change_via_post_only(self):
        self.login(self.worker)
        o = self.make_order([(self.p1, 1)])
        url = reverse('order_change_status', args=[o.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url, {'status': 'paid'})
        o.refresh_from_db()
        self.assertEqual(o.status, Order.PAID)
        self.assertEqual(self.stock(self.p1), 4)

    def test_worker_cannot_edit_products(self):
        self.login(self.worker)
        self.assertEqual(self.client.get(reverse('product_list')).status_code, 200)
        r = self.client.post(reverse('product_create'), {
            'name': 'X', 'category': self.cat.pk, 'price': '1', 'stock_quantity': 1})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Product.objects.filter(name='X').exists())

    def test_admin_crud_product(self):
        self.login(self.admin)
        self.client.post(reverse('product_create'), {
            'name': 'Нова', 'category': self.cat.pk, 'price': '5', 'stock_quantity': 2})
        p = Product.objects.get(name='Нова')
        self.client.post(reverse('product_delete', args=[p.pk]))
        self.assertFalse(Product.objects.filter(pk=p.pk).exists())

    def test_protected_product_not_deleted(self):
        self.login(self.admin)
        self.make_order([(self.p1, 1)])
        self.client.post(reverse('product_delete', args=[self.p1.pk]))
        self.assertTrue(Product.objects.filter(pk=self.p1.pk).exists())

    def test_search_and_filters(self):
        self.login(self.worker)
        r = self.client.get(reverse('product_list'), {'q': 'Сік'})
        self.assertContains(r, 'Сік'); self.assertNotContains(r, 'Вода')
        self.make_order([(self.p1, 1)]).change_status(Order.PAID)
        r = self.client.get(reverse('order_list'), {'status': 'unpaid'})
        self.assertContains(r, 'Замовлень немає')

    def test_no_customer_pages(self):
        self.login(self.admin)
        self.assertEqual(self.client.get('/customers/').status_code, 404)

    def test_dashboard(self):
        self.login(self.worker)
        r = self.client.get(reverse('dashboard'))
        self.assertContains(r, 'Панель керування')
        self.assertNotContains(r, 'Клієнт')


class ProductFilterTests(BaseCase):
    def test_non_numeric_category_filter_does_not_crash(self):
        self.login(self.worker)
        r = self.client.get(reverse('product_list'), {'category': 'abc'})
        self.assertEqual(r.status_code, 200)
