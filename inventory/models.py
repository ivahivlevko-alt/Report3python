from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.conf import settings
from django.db import models, transaction
from django.db.models import F
from decimal import Decimal


class Category(models.Model):
    name = models.CharField('Назва', max_length=100, unique=True)
    description = models.TextField('Опис', blank=True)

    class Meta:
        verbose_name = 'Категорія'
        verbose_name_plural = 'Категорії'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    LOW_STOCK = 10  # поріг «товар закінчується»

    name = models.CharField('Назва', max_length=150)
    description = models.TextField('Опис', blank=True)
    price = models.DecimalField('Ціна, грн', max_digits=10, decimal_places=2,
                                validators=[MinValueValidator(Decimal('0'))])
    stock_quantity = models.PositiveIntegerField('Кількість на складі', default=0)
    category = models.ForeignKey(Category, on_delete=models.PROTECT,
                                 related_name='products', verbose_name='Категорія')
    created_at = models.DateTimeField('Дата додавання', auto_now_add=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товари'
        ordering = ['name']

    @property
    def is_low_stock(self):
        return self.stock_quantity < self.LOW_STOCK

    def __str__(self):
        return self.name


class Order(models.Model):
    UNPAID, PAID = 'unpaid', 'paid'
    STATUSES = [(UNPAID, 'Неоплачене'), (PAID, 'Оплачене')]
    # Дозволені переходи: оплатити або повернути в неоплачені
    TRANSITIONS = {UNPAID: [PAID], PAID: [UNPAID]}

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, verbose_name='Оформив')
    created_at = models.DateTimeField('Дата', auto_now_add=True)
    status = models.CharField('Статус', max_length=20, choices=STATUSES, default=UNPAID)
    total_amount = models.DecimalField('Сума, грн', max_digits=12, decimal_places=2, default=0)
    # Позначка, що товари вже списано зі складу (захист від повторного списання)
    stock_deducted = models.BooleanField(default=False, editable=False)

    class Meta:
        verbose_name = 'Замовлення'
        verbose_name_plural = 'Замовлення'
        ordering = ['-created_at']

    def __str__(self):
        return f'Замовлення №{self.pk}'

    @property
    def next_statuses(self):
        names = dict(self.STATUSES)
        return [(s, names[s]) for s in self.TRANSITIONS[self.status]]

    def recalculate_total(self):
        self.total_amount = sum((i.subtotal for i in self.items.all()), Decimal('0'))
        self.save(update_fields=['total_amount'])

    @transaction.atomic
    def change_status(self, new_status):
        """Змінює статус і керує залишками на складі.

        - «Оплачене»: товари списуються зі складу (лише один раз).
        - «Неоплачене» (повернення з оплаченого): товари повертаються на склад.
        """
        order = Order.objects.select_for_update().get(pk=self.pk)
        if new_status not in order.TRANSITIONS.get(order.status, []):
            raise ValidationError('Такий перехід статусу неможливий.')
        items = list(order.items.select_related('product'))

        if new_status == self.PAID and not order.stock_deducted:
            products = {p.pk: p for p in Product.objects.select_for_update()
                        .filter(pk__in=[i.product_id for i in items])}
            for i in items:
                have = products[i.product_id].stock_quantity
                if have < i.quantity:
                    raise ValidationError(
                        f'Недостатньо товару «{i.product}»: на складі {have}, потрібно {i.quantity}.')
            for i in items:
                Product.objects.filter(pk=i.product_id).update(
                    stock_quantity=F('stock_quantity') - i.quantity)
            order.stock_deducted = True

        elif new_status == self.UNPAID and order.stock_deducted:
            for i in items:
                Product.objects.filter(pk=i.product_id).update(
                    stock_quantity=F('stock_quantity') + i.quantity)
            order.stock_deducted = False

        order.status = new_status
        order.save(update_fields=['status', 'stock_deducted'])
        self.status, self.stock_deducted = order.status, order.stock_deducted


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT,
                                related_name='order_items', verbose_name='Товар')
    quantity = models.PositiveIntegerField('Кількість', validators=[MinValueValidator(1)])
    unit_price = models.DecimalField('Ціна на момент замовлення', max_digits=10,
                                     decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Позиція замовлення'
        verbose_name_plural = 'Позиції замовлення'
        constraints = [models.UniqueConstraint(fields=['order', 'product'],
                                               name='uniq_product_in_order')]

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f'{self.product} × {self.quantity}'
