from collections import Counter
from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory, BaseInlineFormSet
from .models import Category, Product, Order, OrderItem


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-select' if isinstance(
                field.widget, forms.Select) else 'form-control')


class CategoryForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class ProductForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'price', 'stock_quantity']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}

    def clean_price(self):
        price = self.cleaned_data['price']
        if price < 0:
            raise ValidationError('Ціна не може бути від\'ємною.')
        return price


class OrderItemForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(stock_quantity__gt=0)
        self.fields['product'].label_from_instance = (
            lambda p: f'{p.name} — {p.price} грн (залишок {p.stock_quantity})')
        self.fields['product'].empty_label = '— оберіть товар —'
        self.fields['quantity'].widget.attrs['min'] = 1


class BaseItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        totals = Counter()
        for form in self.forms:
            data = form.cleaned_data
            if data.get('product'):
                if data['product'] in totals:
                    raise ValidationError('Один товар не можна додавати двічі.')
                totals[data['product']] = data['quantity']
        if not totals:
            raise ValidationError('Додайте хоча б одну позицію.')
        for product, qty in totals.items():
            if qty > product.stock_quantity:
                raise ValidationError(
                    f'Недостатньо товару «{product}»: на складі {product.stock_quantity}, замовлено {qty}.')


OrderItemFormSet = inlineformset_factory(
    Order, OrderItem, form=OrderItemForm, formset=BaseItemFormSet,
    extra=3, can_delete=False)
