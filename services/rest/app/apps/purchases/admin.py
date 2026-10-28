from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.purchases.models import Purchase


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).select_related("user", "product")

    list_display = (
        "id",
        "status",
        "user_info",
        "product_info",
    )
    fields = (
        "id",
        "user",
        "product",
        "status",
        "transaction_id",
        "response_description",
        "created_at",
        "updated_at",
    )
    list_display_links = (
        "id",
        "status",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )
    list_filter = ("status",)
    search_fields = (
        "user__id",
        "user__username",
        "user__email",
    )

    @admin.display(description="Юзер")
    def user_info(self, obj: Purchase) -> str:
        return f"{obj.user.id}: {obj.user.email} {obj.user.username}"

    @admin.display(description="Продукт")
    def product_info(self, obj: Purchase) -> str:
        return f"{obj.product.id}: {obj.product.title}"
