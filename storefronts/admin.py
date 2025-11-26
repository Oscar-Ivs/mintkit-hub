from django.contrib import admin
from .models import Storefront


@admin.register(Storefront)
class StorefrontAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_active', 'slug', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug', 'owner__user__username')
    prepopulated_fields = {'slug': ('name',)}
