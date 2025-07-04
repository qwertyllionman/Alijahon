from django.contrib import admin

from apps.models import Category, Product, SiteSettings, Order, Payment


# Register your models here.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    exclude = 'slug',

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    exclude = 'slug',

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    pass

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    pass

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = 'card_number', 'user', 'amount',  'status', 'receipt'

    def save_model(self, request, obj, form, change):
        if obj.status == Payment.PaymentStatus.CANCEL:
            user = obj.user
            user.balance += obj.amount
            user.save()
        obj.save()