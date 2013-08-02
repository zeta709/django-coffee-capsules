from django.http import HttpResponse
from django.http import Http404

from django.shortcuts import render, get_object_or_404
from django.views import generic

from coffee_capsules.models import Capsule, Purchase, PurchaseItem

class IndexView(generic.ListView):
	template_name = 'coffee_capsules/index.html'
	context_object_name = 'purchase_list'
	def get_queryset(self):
		return Purchase.objects.order_by('-pk')

#class DetailView(generic.ListView):
#	template_name = 'context_object_name/detail.html'
#	context_object_name = 'purchase_item_list'
#	def get_queryset(self):
#		return PurchaseItem.objects.filter(pk=pk)

def detail(request, myid):
	purchaseitem_list = PurchaseItem.objects.filter(purchase=myid).order_by('capsule__pk')
	template_name = 'coffee_capsules/detail.html'
	context = {'purchaseitem_list': purchaseitem_list}
	return render(request, template_name, context)
