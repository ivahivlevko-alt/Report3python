from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db import transaction
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import (CreateView, DeleteView, DetailView, ListView, UpdateView)

from .forms import CategoryForm, OrderItemFormSet, ProductForm
from .models import Category, Order, Product
from .permissions import is_admin


# ---------- Доступ ----------
class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Лише для адміністратора. Решті — повідомлення й повернення на головну."""

    def test_func(self):
        return is_admin(self.request.user)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, 'У вас немає прав для цієї дії.')
            return redirect('dashboard')
        return super().handle_no_permission()


class TitleMixin:
    title = ''

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = self.title
        return ctx


class SafeDeleteView(AdminRequiredMixin, DeleteView):
    """Видалення лише через POST; якщо запис використовується — зрозуміла помилка."""
    template_name = 'confirm_delete.html'

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'Не можна видалити: запис використовується в інших даних.')
            return redirect(self.success_url)
        messages.success(self.request, 'Запис видалено.')
        return response


@login_required
def dashboard(request):
    ctx = {
        'products_count': Product.objects.count(),
        'categories_count': Category.objects.count(),
        'orders_count': Order.objects.count(),
        'unpaid_count': Order.objects.filter(status=Order.UNPAID).count(),
        'recent_orders': Order.objects.all()[:5],
        'low_stock': Product.objects.filter(stock_quantity__lt=Product.LOW_STOCK)
                                    .order_by('stock_quantity')[:8],
    }
    return render(request, 'dashboard.html', ctx)


class CategoryList(LoginRequiredMixin, ListView):
    template_name = 'categories/list.html'
    paginate_by = 15

    def get_queryset(self):
        return Category.objects.annotate(products_n=Count('products')).order_by('name')


class CategoryCreate(AdminRequiredMixin, TitleMixin, CreateView):
    model, form_class, template_name = Category, CategoryForm, 'form.html'
    title, success_url = 'Нова категорія', reverse_lazy('category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Категорію створено.')
        return super().form_valid(form)


class CategoryUpdate(AdminRequiredMixin, TitleMixin, UpdateView):
    model, form_class, template_name = Category, CategoryForm, 'form.html'
    title, success_url = 'Редагування категорії', reverse_lazy('category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Зміни збережено.')
        return super().form_valid(form)


class CategoryDelete(SafeDeleteView):
    model, success_url = Category, reverse_lazy('category_list')


class ProductList(LoginRequiredMixin, ListView):
    template_name = 'products/list.html'
    paginate_by = 15

    def get_queryset(self):
        qs = Product.objects.select_related('category')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        category = self.request.GET.get('category', '')
        if category.isdigit():
            qs = qs.filter(category_id=int(category))
        if self.request.GET.get('low'):
            qs = qs.filter(stock_quantity__lt=Product.LOW_STOCK)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = Category.objects.all()
        return ctx


class ProductDetail(LoginRequiredMixin, DetailView):
    model = Product
    template_name = 'products/detail.html'


class ProductCreate(AdminRequiredMixin, TitleMixin, CreateView):
    model, form_class, template_name = Product, ProductForm, 'form.html'
    title, success_url = 'Новий товар', reverse_lazy('product_list')

    def form_valid(self, form):
        messages.success(self.request, 'Товар додано.')
        return super().form_valid(form)


class ProductUpdate(AdminRequiredMixin, TitleMixin, UpdateView):
    model, form_class, template_name = Product, ProductForm, 'form.html'
    title, success_url = 'Редагування товару', reverse_lazy('product_list')

    def form_valid(self, form):
        messages.success(self.request, 'Зміни збережено.')
        return super().form_valid(form)


class ProductDelete(SafeDeleteView):
    model, success_url = Product, reverse_lazy('product_list')


class OrderList(LoginRequiredMixin, ListView):
    template_name = 'orders/list.html'
    paginate_by = 15

    def get_queryset(self):
        qs = Order.objects.select_related('created_by')
        if self.request.GET.get('status'):
            qs = qs.filter(status=self.request.GET['status'])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = Order.STATUSES
        return ctx


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related('created_by'), pk=pk)
    return render(request, 'orders/detail.html',
                  {'order': order, 'items': order.items.select_related('product')})


@login_required
def order_create(request):
    """Створення замовлення («кошик» з довільною кількістю товарів).
    Залишки тут лише перевіряються; списуються при переході в статус «Оплачене»."""
    order = Order()
    if request.method == 'POST':
        formset = OrderItemFormSet(request.POST, instance=order)
        if formset.is_valid():
            with transaction.atomic():
                order.created_by = request.user
                order.save()
                for item in formset.save(commit=False):
                    item.order = order
                    item.unit_price = item.product.price   # ціна на момент замовлення
                    item.save()
                order.recalculate_total()
            messages.success(request, f'Замовлення №{order.pk} створено.')
            return redirect('order_detail', pk=order.pk)
    else:
        formset = OrderItemFormSet(instance=order)
    return render(request, 'orders/form.html', {'formset': formset})


@login_required
@require_POST
def order_change_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    try:
        order.change_status(request.POST.get('status'))
        messages.success(request, 'Статус оновлено.')
    except (ValidationError, KeyError) as e:
        messages.error(request, e.messages[0] if hasattr(e, 'messages') else 'Некоректний статус.')
    return redirect('order_detail', pk=pk)
