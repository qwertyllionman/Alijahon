import datetime
import re

from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.forms import Form, ModelForm
from django.forms.fields import CharField
from django.views.generic import FormView

from apps.models import User, Order, Product, Thread, SiteSettings, Payment


class AuthForm(Form):
    phone_number = CharField(max_length=255)
    password = CharField(max_length=8)

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get("phone_number")
        return re.sub("/D", "", phone_number)


    def clean(self):
        data = self.cleaned_data
        password = data.get("password")
        phone_number = data.get("phone_number")
        query = User.objects.filter(phone_number=phone_number)
        if query.exists():
            user = query.first()
            if check_password(password, user.password):
                self.user = user
            else:
                raise ValidationError("Wrong Password!")
        else:
            user = self.save()
            self.user = user
        return data

    def save(self):
        data = self.cleaned_data
        user = User.objects.create(phone_number=data.get('phone_number'))
        user.set_password(data.get('password'))
        user.save()
        return user

class ProfileModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProfileModelForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
    class Meta:
        model = User
        fields = 'first_name', 'last_name', 'district', 'address', 'telegram_id', 'about'


class ChangePasswordForm(Form):
    old_password=CharField(max_length=255)
    new_password=CharField(max_length=255)
    confirm_password=CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_confirm_password(self):
        new_password=self.cleaned_data.get("new_password")
        confirm_password=self.cleaned_data.get("confirm_password")
        if  new_password != confirm_password:
            raise ValidationError("Password is not matching with new password!")
        return confirm_password

    def update(self, user):
        new_password = self.cleaned_data.get("new_password")
        user.set_password(new_password)
        user.save()

class OrderModelForm(ModelForm):
    
    def __init__(self, *args, **kwargs):
        super().__init__( *args, **kwargs)
        self.fields['total'].required = False
        self.fields['thread'].required = False


    class Meta:
        model = Order
        fields = 'phone_number', 'fullname', 'product', 'total', 'thread'

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        return re.sub('/D', "", phone_number)

    def clean_total(self):
        product = self.cleaned_data.get("product")
        thread_id = self.data.get("thread", -1)
        site = SiteSettings.objects.first()
        total_price = product.price + site.delivery_price
        thread = Thread.objects.filter(pk=thread_id).first()
        if thread:
            total_price -= thread.discount
        return total_price


class ThreadModelForm(ModelForm):
    class Meta:
        model = Thread
        fields = "name", "product", "discount"

    def clean_discount(self):
        discount = self.cleaned_data.get("discount")
        product = self.cleaned_data.get("product")
        if product.seller_price <= discount:
            raise ValidationError("Exceed discount limit!")
        return discount

class PaymentModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__( *args, **kwargs)
        self.fields['user'].required = False

    class Meta:
        model = Payment
        fields = 'amount', 'card_number', 'user'

    def clean_user(self):
        return self.user

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        user = self.user
        if amount > user.balance:
            raise ValidationError("Mablag' yetarli emas !")
        return amount


class OrderUpdateModelForm(ModelForm):
    class Meta:
        model = Order
        fields = 'quantity', 'district', 'status', 'comment', 'delivery_date', 'operator'

    def __init__(self, *args, **kwargs):
        self.order = kwargs.pop('order', None)
        self.operator = kwargs.pop('operator', None)
        super().__init__( *args, **kwargs)

    def clean_operator(self):
        return self.operator


    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        order = self.order
        site = SiteSettings.objects.first()
        if order.product.quantity < quantity:
                raise ValidationError("Product soni yetarli emas!")

        if order.thread:
            order.total = order.thread.discount_price * quantity + site.delivery_price
        else:
            order.total = order.product.price * quantity + site.delivery_price
        order.save()
        return quantity

    def clean_delivery_date(self):
        delivery_date = self.cleaned_data.get('delivery_date')

        if  delivery_date and datetime.date.today() > delivery_date:
            raise ValidationError("Yetqazish vaqti noto'g'ri!")
        return delivery_date

