from django.contrib import admin

from coffee_capsules.models import Capsule, Purchase, PurchaseItem, Request, RequestGroup

class CapsuleAdmin(admin.ModelAdmin):
	list_display = ('name', )

class PurchaseItemInline(admin.TabularInline):
	model = PurchaseItem
	extra = 5

class PurchaseAdmin(admin.ModelAdmin):
	fieldsets = [
		(None, {'fields': ['name']}),
		('Date information', {'fields': ['begin_date', 'end_date', 'is_closed']}),
	]
	list_display = ('name', 'begin_date', 'end_date', 'is_closed', )
	inlines = [PurchaseItemInline]

class PurchaseItemAdmin(admin.ModelAdmin):
	list_filter = ['purchase']
	list_display = ('purchase', 'capsule', 'price', 'quantity_accepted', 'quantity_grouped', 'quantity_queued')

class RequestAdmin(admin.ModelAdmin):
	list_filter = ['purchaseitem__purchase']
	list_display = ('purchaseitem', 'quantity_accepted', 'quantity_grouped', 'quantity_queued', 'date', 'user', )

class RequestGroupAdmin(admin.ModelAdmin):
	list_filter = ['purchaseitem__purchase']
	list_display = ('purchaseitem', 'priority', 'quantity', 'is_accepted', 'date', )

admin.site.register(Capsule, CapsuleAdmin)
admin.site.register(Purchase, PurchaseAdmin)
admin.site.register(PurchaseItem, PurchaseItemAdmin)
admin.site.register(Request, RequestAdmin)
admin.site.register(RequestGroup, RequestGroupAdmin)
