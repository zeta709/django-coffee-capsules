from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

from coffee_capsules.models import Capsule, Purchase

def index(request):
	return HttpResponse("index")

def detail(request, purchase_id):
	purchase = get_object_or_404(Purchase, pk=purchase_id)
	myset = purchase.choice_set.all()
	return HttpResponse("HAHA %s" % purchase_id)
	#return render(request, 'coffee_capsules/detail.html', {'event': event})
