from django.contrib import admin
from django.urls import path, include

from apps.views import HomeListView, AuthFormView, LogoutView, OrderFormView, wishlist_view, ProductListView, \
    ProfileUpdateView, OrderListView, district_view, UserChangePasswordView, SearchProductListView, WishListView, \
    MarketListView, ThreadCreateView, ThreadListView, ThreadDetailView, StatisticListView, CompetitionListView, PaymentCreateView, \
    OperatorOrderListView, OrderUpdateView

urlpatterns = [
    path('', HomeListView.as_view(), name="home"),
    path('product-list', ProductListView.as_view(), name="product-list"),
    path('district_list', district_view, name='district-list'),
    path('search', SearchProductListView.as_view(), name='search'),
]

# ---------------------------------- Auth ------------------------------------------------
urlpatterns += [
    path('auth', AuthFormView.as_view(), name="auth"),
    path('auth/logout', LogoutView.as_view(), name='logout'),
    path('user/profile', ProfileUpdateView.as_view(), name='profile'),
    path('change-password', UserChangePasswordView.as_view(), name='change-password'),

]
# ---------------------- Orders --------------------------------------------------------
urlpatterns += [
    path('order-list', OrderListView.as_view(), name="order-list"),
    path('order-form/<str:slug>', OrderFormView.as_view(), name='order-form'),
]
# ---------------------- WishList --------------------------------------------------------
urlpatterns += [
    path('wishlist/<int:pk>', wishlist_view, name="wishlist"),
    path('wishlist/', WishListView.as_view(), name="wish"),

]
# ---------------------- Market --------------------------------------------------------
urlpatterns += [
    path('market-list', MarketListView.as_view(), name="market-list"),
    path('thread-form', ThreadCreateView.as_view(), name="thread-form"),
    path('thread-list', ThreadListView.as_view(), name="thread-list"),
    path('thread/<int:pk>', ThreadDetailView.as_view(), name="thread"),
    path('thread/statistic', StatisticListView.as_view(), name="thread-statistic"),
    path('thread/competition', CompetitionListView.as_view(), name="thread-competition"),

]
# ---------------------------------------- Payment -------------------------------------------
urlpatterns += [
    path("pay-form", PaymentCreateView.as_view(), name='pay-form')
]
# --------------------------------------- Operator --------------------------------------------
urlpatterns += [
    path('operator/order/list',  OperatorOrderListView.as_view(), name='operator-orders'),
    path('operator/order/update/<int:pk>',  OrderUpdateView.as_view(), name='order-detail')

]