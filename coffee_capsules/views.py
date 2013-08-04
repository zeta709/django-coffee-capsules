from django.core.urlresolvers import reverse

from django.http import HttpResponseRedirect, HttpResponse
from django.http import Http404

from django.shortcuts import render, get_object_or_404, render_to_response
from django.views import generic

from django.db import connection, transaction

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from django.forms.models import modelformset_factory
from django.forms.models import inlineformset_factory

from coffee_capsules.models import Capsule, Purchase, PurchaseItem, Request
from coffee_capsules.forms import PurchaseForm

from django.utils import timezone

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

from django.forms import forms
@login_required
@transaction.commit_on_success
def new_purchase(request):
	template_name = 'coffee_capsules/new_purchase.html'
	all_capsule_list = Capsule.objects.order_by('pk')
	n_of_capsules = len(all_capsule_list)
	#### formset factory
	PurchaseFormSet = modelformset_factory(Purchase, form=PurchaseForm, extra=1)
	PurchaseItemFormset = inlineformset_factory(Purchase, PurchaseItem, fk_name="purchase", extra=n_of_capsules)
	#### post
	if request.method == 'POST':
		has_error = False
		formset = PurchaseFormSet(request.POST, prefix='purchase')
		formset2 = PurchaseItemFormset(request.POST, prefix='purchaseitem')
		if formset.is_valid():
			purchase_instances = formset.save(commit=False)
			if len(purchase_instances) is 0:
				has_error = True
				messages.error(request, 'Error: empty')
			else:
				formset2 = PurchaseItemFormset(request.POST, prefix='purchaseitem',
							       instance=purchase_instances[0])
				if formset2.is_valid():
					purchase_instances[0].save()
					purchaseitem_instances = formset2.save(commit=False)
					for purchaseitem_instance in purchaseitem_instances:
						purchaseitem_instance.save()
				else:
					has_error = True
		else:
			has_error = True
		if has_error is False:
			messages.success(request, 'Success')
			return HttpResponseRedirect(reverse('coffee_capsules:index'))
		else:
			messages.error(request, 'Error')
			context = {
				'formset': formset,
				'formset2': formset2,
				'capsule_list': all_capsule_list,
			}
			return render(request, template_name, context)
	#### not post
	formset = PurchaseFormSet(queryset=Purchase.objects.none(), prefix='purchase')
	## initial
	initial = []
	for capsule in all_capsule_list:
		initial.append({'capsule': capsule.id, 'price': capsule.price})
	formset2 = PurchaseItemFormset(initial=initial, prefix='purchaseitem')
	##### context
	context = {
		'formset': formset,
		'formset2': formset2,
		'capsule_list': all_capsule_list,
		}
	return render(request, template_name, context)

@login_required
def purchase_request(request, myid):
	purchase = get_object_or_404(Purchase, pk=myid)
	has_error = False
	if purchase.is_not_open():
		has_error = True
		messages.error(request, 'The purchase is not yet open')
	if purchase.is_ended():
		has_error = True
		messages.error(request, 'The purchase is aleady ended')
	if has_error is False:
		purchaseitem_list = purchase.purchaseitem_set.order_by('capsule__pk')
		value_list = []
		value_sum = 0
		for purchaseitem in purchaseitem_list:
			name = "capsule_" + str(purchaseitem.capsule.id)
			try:
				value = int(request.POST[name])
			except ValueError:
				value = 0
				has_error = True
				messages.error(request, 'Wrong values')
				break
			if value < 0:
				has_error = True
				messages.error(request, 'Values cannot be negative')
				break
			if value%(purchase.u_unit) != 0:
				has_error = True
				messages.error(request, 'Each value should be multiples of ' + str(purchase.u_unit))
				break
			value_sum += value
			value_list.append(value)
	if has_error is False and value_sum <= 0:
		has_error = True
		messages.error(request, 'Sum of values must be greather than 0')
	if has_error is False:
		messages.success(request, 'Success')
		for i, purchaseitem in enumerate(purchaseitem_list):
			if value_list[i] > 0:
				new_request = Request(purchaseitem=purchaseitem, user=request.user, quantity_queued=value_list[i])
				new_request.save()
	return HttpResponseRedirect(reverse('coffee_capsules:detail', args=(purchase.id,)))

@login_required
@transaction.commit_on_success
def detail(request, myid):
	agq = True
	template_name = 'coffee_capsules/detail.html'
	purchase = get_object_or_404(Purchase, pk=myid)
	purchaseitem_list = purchase.purchaseitem_set.order_by('capsule__pk')
	#### raw db connection
	cursor = connection.cursor()
	#### get capsule list
	query_str_capsule = 'SELECT coffee_capsules_capsule.id, name FROM coffee_capsules_capsule'\
			+ ' INNER JOIN "coffee_capsules_purchaseitem" ON '\
			+ ' ("coffee_capsules_capsule"."id" = "coffee_capsules_purchaseitem"."capsule_id")'\
			+ ' WHERE "coffee_capsules_purchaseitem"."purchase_id" = %s'
	cursor.execute(query_str_capsule, [myid])
	capsule_list = cursor.fetchall()
	#print("==capsule_list==")
	#print(capsule_list)
	#print("================")
	#### make query string for selection
	if agq == False:
		query_str_0 = 'SELECT group_concat(ca, ", ") AS gc'\
			+ ' FROM (SELECT'\
			+ ' "SUM(CASE WHEN capsule_id=" || coffee_capsules_capsule.id || " THEN coffee_capsules_request.quantity_accepted ELSE 0 END) AS qty_a_" || coffee_capsules_capsule.id AS ca'\
			+ ' FROM coffee_capsules_capsule'\
			+ ' INNER JOIN "coffee_capsules_purchaseitem" ON '\
			+ ' ("coffee_capsules_capsule"."id" = "coffee_capsules_purchaseitem"."capsule_id")'\
			+ ' WHERE "coffee_capsules_purchaseitem"."purchase_id" = %s)'
		cursor.execute(query_str_0, [myid])
		select_str = cursor.fetchall()[0][0]
	else:
		query_str_0 = 'SELECT group_concat(ca || ", " || cg || ", " || cq, ", ") AS gc'\
			+ ' FROM (SELECT'\
			+ ' "SUM(CASE WHEN capsule_id=" || coffee_capsules_capsule.id || " THEN coffee_capsules_request.quantity_accepted ELSE 0 END) AS qty_a_" || coffee_capsules_capsule.id AS ca'\
			+ ', "SUM(CASE WHEN capsule_id=" || coffee_capsules_capsule.id || " THEN coffee_capsules_request.quantity_grouped ELSE 0 END) AS qty_g_" || coffee_capsules_capsule.id AS cg'\
			+ ', "SUM(CASE WHEN capsule_id=" || coffee_capsules_capsule.id || " THEN coffee_capsules_request.quantity_queued ELSE 0 END) AS qty_q_" || coffee_capsules_capsule.id AS cq'\
			+ ' FROM coffee_capsules_capsule'\
			+ ' INNER JOIN "coffee_capsules_purchaseitem" ON '\
			+ ' ("coffee_capsules_capsule"."id" = "coffee_capsules_purchaseitem"."capsule_id")'\
			+ ' WHERE "coffee_capsules_purchaseitem"."purchase_id" = %s)'
		cursor.execute(query_str_0, [myid])
		select_str = cursor.fetchall()[0][0]
	if select_str is None:
		select_str = 'COUNT(*)'
	#### get pivot table
	query_str_1 = 'SELECT auth_user.username, ' + select_str
	if agq == False:
		query_str_1 += ', SUM(coffee_capsules_request.quantity_accepted) AS SUM_a'\
			+ ', SUM(coffee_capsules_purchaseitem.price * coffee_capsules_request.quantity_accepted) AS GT_a'
	else:
		query_str_1 += ', SUM(coffee_capsules_request.quantity_accepted) AS SUM_a'\
			+ ', SUM(coffee_capsules_request.quantity_grouped) AS SUM_a'\
			+ ', SUM(coffee_capsules_request.quantity_queued) AS SUM_a'\
			+ ', SUM(coffee_capsules_purchaseitem.price * coffee_capsules_request.quantity_accepted) AS GT_a'\
			+ ', SUM(coffee_capsules_purchaseitem.price * coffee_capsules_request.quantity_grouped) AS GT_a'\
			+ ', SUM(coffee_capsules_purchaseitem.price * coffee_capsules_request.quantity_queued) AS GT_a'
	query_str_1 += ' FROM "coffee_capsules_request"'\
		+ ' INNER JOIN "coffee_capsules_purchaseitem" ON '\
		+ ' ("coffee_capsules_request"."purchaseitem_id" = "coffee_capsules_purchaseitem"."id")'\
		+ ' INNER JOIN "auth_user" ON ("coffee_capsules_request"."user_id" = "auth_user"."id")'\
		+ ' WHERE "coffee_capsules_purchaseitem"."purchase_id" = %s'\
		+ ' GROUP BY coffee_capsules_request.user_id'
	cursor.execute(query_str_1, [myid])
	request_list = cursor.fetchall()
	#print("==request_list==")
	#for i in request_list:
	#	print(i)
	#	print("----------------")
	#print("================")
	#### get total row
	zipped = zip(*request_list)
	total_row = [0 for i in range(len(zipped))]
	#print(zipped)
	for i in range(1,len(zipped)):
		total_row[i] = zipped[i][0]
		for j in range(1,len(zipped[i])):
			total_row[i] += zipped[i][1]
	if len(zipped) > 0:
		total_row[0] = "Total"
	##### context
	context = {
		'agq': agq,
		'purchase': purchase,
		'purchaseitem_list': purchaseitem_list,
		'capsule_list': capsule_list,
		'request_list': request_list,
		'total_row': total_row,
		}
	return render(request, template_name, context)
