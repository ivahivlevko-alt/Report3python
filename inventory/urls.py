from django.urls import path
from . import views as v

urlpatterns = [
    path('', v.dashboard, name='dashboard'),

    path('products/', v.ProductList.as_view(), name='product_list'),
    path('products/add/', v.ProductCreate.as_view(), name='product_create'),
    path('products/<int:pk>/', v.ProductDetail.as_view(), name='product_detail'),
    path('products/<int:pk>/edit/', v.ProductUpdate.as_view(), name='product_update'),
    path('products/<int:pk>/delete/', v.ProductDelete.as_view(), name='product_delete'),

    path('categories/', v.CategoryList.as_view(), name='category_list'),
    path('categories/add/', v.CategoryCreate.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', v.CategoryUpdate.as_view(), name='category_update'),
    path('categories/<int:pk>/delete/', v.CategoryDelete.as_view(), name='category_delete'),


    path('orders/', v.OrderList.as_view(), name='order_list'),
    path('orders/add/', v.order_create, name='order_create'),
    path('orders/<int:pk>/', v.order_detail, name='order_detail'),
    path('orders/<int:pk>/status/', v.order_change_status, name='order_change_status'),
]
