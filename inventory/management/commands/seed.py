from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from inventory.models import Category, Order, OrderItem, Product
from inventory.permissions import WORKER_GROUP

PRODUCTS = {
    'Молочні продукти': [('Молоко 2.5% 900 мл', 42.90, 120), ('Сир кисломолочний 5%', 38.50, 8),
                         ('Йогурт натуральний', 24.00, 45), ('Масло вершкове 180 г', 89.90, 30)],
    'Напої': [('Вода мінеральна 1.5 л', 24.00, 200), ('Сік яблучний 1 л', 51.00, 60),
              ('Чай чорний 25 пак.', 62.00, 7)],
    'Хліб і випічка': [('Хліб пшеничний', 22.00, 40), ('Круасан', 18.00, 5), ('Багет', 27.50, 25)],
    'Бакалія': [('Гречка 1 кг', 56.00, 80), ('Рис 1 кг', 49.00, 70), ('Олія соняшникова 1 л', 72.00, 55)],
}


class Command(BaseCommand):
    help = 'Створює групу, двох користувачів (admin, worker) і демонстраційні дані'

    def handle(self, *args, **options):
        User = get_user_model()
        worker_g, _ = Group.objects.get_or_create(name=WORKER_GROUP)
        # у системі лише два користувачі: admin і worker
        User.objects.exclude(username__in=['admin', 'worker']).filter(is_superuser=False).delete()
        Group.objects.exclude(name=WORKER_GROUP).delete()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin12345')
        if not User.objects.filter(username='worker').exists():
            User.objects.create_user('worker', password='worker12345').groups.add(worker_g)

        for cname, items in PRODUCTS.items():
            cat, _ = Category.objects.get_or_create(name=cname)
            for name, price, qty in items:
                Product.objects.get_or_create(name=name, defaults=dict(
                    category=cat, price=price, stock_quantity=qty))
        if not Order.objects.exists():
            for lines, status in [
                ([('Молоко 2.5% 900 мл', 2), ('Хліб пшеничний', 1), ('Гречка 1 кг', 2)], Order.PAID),
                ([('Гречка 1 кг', 3), ('Олія соняшникова 1 л', 1)], Order.UNPAID),
                ([('Вода мінеральна 1.5 л', 6), ('Круасан', 2), ('Сік яблучний 1 л', 2)], Order.PAID)]:
                order = Order.objects.create(created_by=User.objects.get(username='worker'))
                for pname, qty in lines:
                    p = Product.objects.get(name=pname)
                    OrderItem.objects.create(order=order, product=p, quantity=qty, unit_price=p.price)
                order.recalculate_total()
                if status == Order.PAID:
                    order.change_status(status)
        self.stdout.write(self.style.SUCCESS(
            'Готово. Користувачі: admin/admin12345, worker/worker12345'))
