from django.contrib import admin

from coffee_capsules.models import Capsule, Purchase, PurchaseItem
from coffee_capsules.models import Request, RequestGroup, RequestGroupItem

# NOTE
# readonly-for-existing-items-only-in-django-admin-inline
# http://stackoverflow.com/questions/4343535


class MyAdmin(admin.ModelAdmin):
    my_readonly_update = ()

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + self.my_readonly_update
        return self.readonly_fields


class MyNoDeleteAdmin(MyAdmin):
    actions = None  # remove all actions

    def has_delete_permission(self, request, obj=None):
        return False


class MyNoAddOrDeleteAdmin(admin.ModelAdmin):
    actions = None  # remove all actions

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class MyReadonlyAdmin(MyNoAddOrDeleteAdmin):
    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        return False


class CapsuleAdmin(MyNoDeleteAdmin):
    fields = ('name', 'price')
    list_display = ('name', 'price')
    #my_readonly_update = ('name', )


# This is my idea!
#
# I want to add a new item, but I don't want to modify an existing item.
# 1. Using Inline with readonly_fields, a new item cannot be added
# 2. Using Inline witout readonly_fields, an exisiting item can be modified
#
# Solution: Use two Inline's
#
class PurchaseItemInline_0(admin.TabularInline):
    def has_add_permission(self, request, obj=None):
        return False
    fields = ('capsule', 'price', 'quantity_accepted',
              'quantity_grouped', 'quantity_queued')
    readonly_fields = ('purchase', 'capsule', 'quantity_accepted',
                       'quantity_grouped', 'quantity_queued')
    model = PurchaseItem
    extra = 0


class PurchaseItemInline_1(admin.TabularInline):
    def has_change_permission(self, request, obj=None):
        return False
    fields = ('capsule', 'price')
    model = PurchaseItem
    extra = 5


class PurchaseAdmin(MyAdmin):
    fieldsets = [
        (None, {'fields': ['name', 'g_unit', 'p_unit', 'u_unit']}),
        ('Date information', {'fields':
                              ['begin_date', 'end_date', 'is_closed']}),
    ]
    list_display = ('name', 'begin_date', 'end_date',
                    'g_unit', 'p_unit', 'u_unit', 'is_closed', )
    inlines = [PurchaseItemInline_0, PurchaseItemInline_1]


class PurchaseItemAdmin(MyAdmin):
    readonly_fields = ('quantity_accepted',
                       'quantity_grouped', 'quantity_queued')
    my_readonly_update = ('purchase', 'capsule')
    fieldsets = [
        (None, {'fields': ['purchase', 'capsule', 'price']}),
        ('Quantity', {'fields': ['quantity_accepted',
                                 'quantity_grouped', 'quantity_queued']}),
    ]
    list_filter = ['purchase']
    list_display = ('purchase', 'capsule', 'price',
                    'quantity_accepted', 'quantity_grouped', 'quantity_queued')


class RequestAdmin(MyNoDeleteAdmin):
    readonly_fields = ('quantity_accepted', 'quantity_grouped')
    my_readonly_update = ('purchaseitem', 'user', 'quantity_queued')
    fieldsets = [
        (None, {'fields': ['purchaseitem', 'user']}),
        ('Quantity', {'fields':
                      ['quantity_accepted',
                       'quantity_grouped', 'quantity_queued']}),
    ]
    list_filter = ['purchaseitem__purchase']
    list_display = ('purchaseitem', 'user', 'quantity_accepted',
                    'quantity_grouped', 'quantity_queued', 'date', )


class RequestGroupAdmin(MyReadonlyAdmin):
    list_filter = ['purchaseitem__purchase']
    list_display = ('purchaseitem', 'priority',
                    'quantity_accepted', 'quantity_grouped', 'date')


class RequestGroupItemAdmin(MyReadonlyAdmin):
    list_display = ('requestgroup', 'request', 'quantity')


admin.site.register(Capsule, CapsuleAdmin)
admin.site.register(Purchase, PurchaseAdmin)
admin.site.register(Request, RequestAdmin)

#
admin.site.register(PurchaseItem, PurchaseItemAdmin)
admin.site.register(RequestGroup, RequestGroupAdmin)
admin.site.register(RequestGroupItem, RequestGroupItemAdmin)
