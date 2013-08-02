from django.http import HttpResponse
from django.http import Http404

from django.shortcuts import render, get_object_or_404
from django.views import generic

from coffee_capsules.models import Capsule, Purchase, PurchaseItem, Request

from django.db import connection, transaction

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

@transaction.commit_on_success
def detail(request, myid):
	template_name = 'coffee_capsules/detail.html'
	purchaseitem_list = PurchaseItem.objects.filter(purchase=myid).order_by('capsule__pk')
	# raw db connection
	cursor = connection.cursor()
	# get capsule list
	query_str_capsule = 'SELECT id, name FROM coffee_capsules_capsule'
	cursor.execute(query_str_capsule)
	capsule_list = cursor.fetchall()
	#print("==capsule_list==")
	#print(capsule_list)
	#print("================")
	# make query string for selection
	query_str_0 = 'SELECT group_concat(c, ", ") AS gc'\
		+ ' FROM (SELECT "SUM(CASE WHEN capsule_id=" || id || " THEN coffee_capsules_request.quantity_accepted ELSE 0 END) AS qty_ac_" || id AS c'\
		+ ' FROM coffee_capsules_capsule)'
	cursor.execute(query_str_0)
	selec_str = cursor.fetchall()[0][0]
	# get pivot table
	query_str_1 = 'SELECT auth_user.username, '\
		+ selec_str\
		+ ', SUM(coffee_capsules_request.quantity_accepted) AS SUM'\
		+ ', SUM(coffee_capsules_purchaseitem.price * coffee_capsules_request.quantity_accepted) AS GT'\
		+ ' FROM "coffee_capsules_request"'\
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
	# get total row
	zipped = zip(*request_list)
	total_row = [0 for i in range(len(zipped))]
	for i in range(1,len(zipped)):
		total_row[i] = zipped[i][0] + zipped[i][1]
	if len(zipped) > 0:
		total_row[0] = "Total"
	# context
	context = {
		'purchaseitem_list': purchaseitem_list,
		'capsule_list': capsule_list,
		'request_list': request_list,
		'total_row': total_row,
		}
	return render(request, template_name, context)
