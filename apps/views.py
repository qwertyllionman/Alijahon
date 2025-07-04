from datetime import datetime, timedelta
from itertools import product
from os import eventfd_write

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import check_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q, F
from django.db.models.aggregates import Count, Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView, ListView, FormView, UpdateView, DetailView, CreateView

from apps.forms import AuthForm, ProfileModelForm, ChangePasswordForm, OrderModelForm, ThreadModelForm, \
    PaymentModelForm, OrderUpdateModelForm
from apps.models import Category, Product, User, Region, District, Order, WishList, Thread, SiteSettings, Payment


# Create your views here.
class HomeListView(ListView):
    queryset = Category.objects.all()
    template_name = 'apps/home.html'
    context_object_name = "categories"

    def get_context_data(self, *args, **kwargs):
        data = super().get_context_data(*args, **kwargs)
        data['products'] = Product.objects.all()
        return data


class AuthFormView(FormView):
    form_class = AuthForm
    success_url = reverse_lazy("home")
    template_name = "apps/auth/auth-page.html"

    def form_valid(self, form):
        user = form.user
        login(self.request, user)
        return super().form_valid(form)

    def form_invalid(self, form):
        for error in form.errors.values():
            messages.error(self.request, error)
        return super().form_invalid(form)


class LogoutView(View):
    def get(self, request):
        logout(self.request)
        return redirect('auth')


class ProductListView(ListView):
    queryset = Product.objects.select_related('category').all().filter()
    template_name = 'apps/product-list.html'
    context_object_name = 'products'

    def get_queryset(self):
        c_slug = self.request.GET.get('category_slug')
        query = super().get_queryset()
        if c_slug:
            query = query.filter(category__slug=c_slug)
        return query

    def get_context_data(self, *args, **kwargs):
        data = super().get_context_data(*args, **kwargs)
        data['categories'] = Category.objects.all()
        data['c_slug'] = self.request.GET.get('category_slug')

        return data


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    queryset = User.objects.all()
    template_name = 'apps/auth/profile.html'
    success_url = reverse_lazy('profile')
    form_class = ProfileModelForm
    pk_url_kwarg = None
    context_object_name = 'user'

    def get_object(self, *args, **kwargs):
        return self.request.user

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['regions'] = Region.objects.all()
        return data

    def form_invalid(self, form):
        for error in form.errors.values():
            messages.error(self.request, error)
        return super().form_invalid(form)


def district_view(request):
    region_id = request.GET.get("region_id")
    districts = District.objects.filter(region_id=region_id).values("id", "name")
    data = [{"id": district.get("id"), "name": district.get("name")} for district in districts]
    return JsonResponse(data, safe=False)


class UserChangePasswordView(LoginRequiredMixin, FormView):
    form_class = ChangePasswordForm
    template_name = 'apps/auth/profile.html'
    success_url = reverse_lazy("profile")

    def form_valid(self, form):
        old_password = form.cleaned_data.get("old_password")
        user = self.request.user
        if not check_password(user.password, old_password):
            messages.error(self.request, "Old password is invalid!")
            return super().form_invalid(form)
        form.update(user=user)
        return super().form_valid(form)

    def form_invalid(self, form):
        for error in form.errors.values():
            messages.error(self.request, error)
        return super().form_invalid(form)


class SearchProductListView(ListView):
    queryset = Product.objects.all()
    template_name = 'apps/search-product-list.html'
    context_object_name = 'products'

    def get_queryset(self):
        search = self.request.GET.get('search')
        query = Product.objects.filter(
            Q(title__icontains=search) | Q(description__icontains=search) | Q(category__name__icontains=search))
        return query.distinct()


class OrderFormView(CreateView):
    queryset = Product.objects.all()
    form_class = OrderModelForm
    template_name = 'apps/order/order-form.html'
    context_object_name = 'product'
    slug_url_kwarg = 'slug'

    def form_valid(self, form):
        order = form.save(commit=False)
        order.customer = self.request.user
        order.save()
        site = SiteSettings.objects.first()
        return render(self.request, "apps/order/order-receive.html", context={"order": order, "site": site})

    def form_invalid(self, form):
        for error in form.errors.values():
            messages.error(self.request, error)
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        product_slug = self.kwargs.get('slug')
        data = super().get_context_data(**kwargs)
        data['product'] = Product.objects.get(slug=product_slug)
        return data


class OrderListView(LoginRequiredMixin, ListView):
    queryset = Order.objects.all().order_by("-created_at")
    template_name = 'apps/order/order-list.html'
    context_object_name = 'orders'

    def get_queryset(self):
        query = super().get_queryset().filter(customer=self.request.user)
        return query


def wishlist_view(request, pk):
    query = WishList.objects.filter(product_id=pk, user=request.user)
    clicked = False
    if not query.exists():
        clicked = True
        WishList.objects.create(user=request.user, product_id=pk)
    else:
        query.delete()
    return JsonResponse({"clicked": clicked})


class WishListView(ListView):
    queryset = WishList.objects.all()
    template_name = 'apps/auth/wishlist.html'
    context_object_name = 'wishlist'

    def get_queryset(self):
        query = super().get_queryset().filter(user=self.request.user)
        return query


class MarketListView(ListView):
    queryset = Product.objects.all()
    template_name = 'apps/market/market-list.html'
    context_object_name = 'products'

    def get_queryset(self):
        category_slug = self.request.GET.get("category_slug")
        query = super().get_queryset()
        if category_slug == "top":
            query = query.annotate(order_count=Count("orders")).order_by('-order_count')
        elif category_slug:
            query = query.filter(category__slug=category_slug)
        return query

    def get_context_data(self, *args, **kwargs):
        data = super().get_context_data(*args, **kwargs)
        data['categories'] = Category.objects.all()
        data['c_slug'] = self.request.GET.get('category_slug')
        return data


class ThreadCreateView(CreateView):
    queryset = Thread.objects.all()
    template_name = 'apps/market/market-list.html'
    form_class = ThreadModelForm
    context_object_name = 'threads'
    success_url = reverse_lazy("thread-list")

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['products'] = Product.objects.all()
        data['categories'] = Category.objects.all()
        return data

    def form_valid(self, form):
        thread = form.save(commit=False)
        thread.owner = self.request.user
        thread.save()
        return super().form_valid(form)

    def form_invalid(self, form):
        for error in form.errors.values():
            messages.error(self.request, error)
        return super().form_invalid(form)


class ThreadListView(LoginRequiredMixin, ListView):
    queryset = Thread.objects.all()
    template_name = 'apps/market/thread-list.html'
    context_object_name = 'threads'

    def get_queryset(self):
        query = super().get_queryset().filter(owner=self.request.user)
        return query


class ThreadDetailView(DetailView):
    pk_url_kwarg = 'pk'
    queryset = Thread.objects.all()
    template_name = 'apps/order/order-form.html'
    context_object_name = 'thread'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        thread = data.get("thread")
        thread.visit_count += 1
        thread.save()
        data['product'] = self.object.product
        return data


class StatisticListView(LoginRequiredMixin, ListView):
    queryset = Thread.objects.all()
    template_name = 'apps/market/statistics.html'
    context_object_name = 'threads'

    def get_queryset(self):
        period = self.request.GET.get('period')
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
        today_end = datetime(now.year, now.month, now.day, 23, 59, 59)

        # Yesterday
        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_end - timedelta(days=1)

        # Weekly
        week_start = today_start - timedelta(days=6)
        week_end = today_end

        # Monthly
        month_start = today_start - timedelta(days=29)
        month_end = today_end

        # All time
        all_start = datetime(2000, 1, 1, 0, 0, 0)
        all_end = today_end

        datetime_map = {
            "today": [today_start, today_end],
            "last_day": [yesterday_start, yesterday_end],
            "wekly": [week_start, week_end],
            "monthly": [month_start, month_end],
            "all": [all_start, all_end]
        }
        filter_time = datetime_map.get(period)

        query = Thread.objects.all().filter(owner=self.request.user).annotate(
            new_count=Count('orders',
                            filter=Q(orders__status=Order.StatusType.NEW) & Q(orders__updated_at__range=filter_time)),
            ready_count=Count('orders', filter=Q(orders__status=Order.StatusType.READY_TO_DELIVERY) & Q(
                orders__updated_at__range=filter_time)),
            delivering_count=Count('orders', filter=Q(orders__status=Order.StatusType.DELIVERING) & Q(
                orders__updated_at__range=filter_time)),
            delivered_count=Count('orders', filter=Q(orders__status=Order.StatusType.DELIVERED) & Q(
                orders__updated_at__range=filter_time)),
            not_call_count=Count('orders', filter=Q(orders__status=Order.StatusType.NOT_CALL) & Q(
                orders__updated_at__range=filter_time)),
            canceled_count=Count('orders', filter=Q(orders__status=Order.StatusType.CANCELED) & Q(
                orders__updated_at__range=filter_time)),
            archived_count=Count('orders', filter=Q(orders__status=Order.StatusType.ARCHIVED) & Q(
                orders__updated_at__range=filter_time)),
        ).values("visit_count",
                 "product__title",
                 "name",
                 "new_count",
                 "ready_count",
                 "delivering_count",
                 "delivered_count",
                 "not_call_count",
                 "canceled_count",
                 "archived_count",
                 )
        return query

    def get_context_data(self, *args, **kwargs):
        tmp = self.get_queryset().aggregate(
            visit_total=Sum('visit_count'),
            new_total=Sum('new_count'),
            ready_total=Sum('ready_count'),
            delivering_total=Sum('delivering_count'),
            not_call_total=Sum('not_call_count'),
            delivered_total=Sum('delivered_count'),
            canceled_total=Sum('canceled_count'),
            archived_total=Sum('archived_count')
        )
        data = super().get_context_data()
        data.update(tmp)
        return data


class CompetitionListView(ListView):
    queryset = User.objects.all()
    template_name = 'apps/market/competition.html'
    context_object_name = 'sellers'

    def get_queryset(self):
        query = super().get_queryset().annotate(order_count=Count('threads__orders', filter=Q(
            threads__orders__status=Order.StatusType.DELIVERED))).filter(order_count__gte=1).values(
            "order_count", "first_name", "last_name")
        return query

    def get_context_data(self, *args, **kwargs):
        data = super().get_context_data(*args, **kwargs)
        data['site'] = SiteSettings.objects.first()
        return data

class PaymentCreateView(LoginRequiredMixin, CreateView):
    template_name = 'apps/payment/pay-form.html'
    form_class = PaymentModelForm
    success_url = reverse_lazy('pay-form')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['payments'] = Payment.objects.filter(user=self.request.user)
        return data

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        user.balance -= form.instance.amount
        user.save()
        return super().form_valid(form)

    def form_invalid(self, form):
        for error in form.errors.values():
            messages.error(self.request, error)
        return super().form_invalid(form)


class OperatorOrderListView(ListView):
    queryset = Order.objects.all()
    template_name = 'apps/operator/operator-page.html'
    context_object_name = 'orders'

    def get_context_data(self, *args, **kwargs):
        data =  super().get_context_data(*args, **kwargs)
        data['status'] = Order.StatusType.values
        data['categories'] = Category.objects.all()
        data['regions'] = Region.objects.all()
        category_id = self.request.GET.get('category_id')
        district_id = self.request.GET.get('district_id')
        if category_id:
            data['category_id'] = int(category_id)
        if district_id:
            data['district_id'] = int(district_id)
        return data

    def get_queryset(self):
        status = self.request.GET.get('status', 'new')
        category_id = self.request.GET.get('category_id')
        district_id = self.request.GET.get('district_id')
        Order.objects.filter(operator=self.request.user).update(hold=False)
        query = super().get_queryset()
        if category_id:
            query = Order.objects.filter(product__category_id=category_id)
        if district_id:
            query = Order.objects.filter(district_id=district_id)
        if status != 'new':
            query = query.filter(operator=self.request.user, status=status)
        else:
            query = query.filter(status=status)
        return query

class OrderUpdateView(UpdateView):
    queryset = Order.objects.all()
    template_name = 'apps/operator/order-change.html'
    context_object_name = 'order'
    pk_url_kwarg = "pk"
    form_class = OrderUpdateModelForm
    success_url = reverse_lazy('operator-orders')




    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['regions'] = Region.objects.all()
        data['operator'] = self.request.user
        return data

    def get(self, request, *args, **kwargs):
        return_data = super().get(request, *args, **kwargs)
        self.object.hold = True
        self.object.save()
        return return_data

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['order'] = self.object
        return kwargs