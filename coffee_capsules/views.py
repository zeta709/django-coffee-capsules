from django.core.urlresolvers import reverse

from django.http import HttpResponseRedirect

from django.shortcuts import render, get_object_or_404
from django.views import generic

from django.db import connection, transaction

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required

from django.forms import forms
from django.forms.models import modelform_factory
from django.forms.models import modelformset_factory
from django.forms.models import inlineformset_factory

from coffee_capsules.models import Capsule, Purchase, PurchaseItem, Request
from coffee_capsules.forms import PurchaseForm, PurchaseItemForm, MyRequestForm

from django.utils import timezone


class IndexView(generic.ListView):
    template_name = 'coffee_capsules/index.html'
    context_object_name = 'purchase_list'

    def get_queryset(self):
        return Purchase.objects.order_by('-pk')


class CapsuleList(generic.ListView):
    template_name = 'coffee_capsules/capsule_list.html'
    context_object_name = 'capsule_list'

    def get_queryset(self):
        return Capsule.objects.order_by('pk')


@login_required
@permission_required('coffee_capsules.add_capsule', raise_exception=True)
def edit_capsule(request, myid=None):
    template_name = 'coffee_capsules/edit_capsule.html'
    if myid:
        capsule = get_object_or_404(Capsule, pk=myid)
    else:
        capsule = Capsule()
    # fi
    CapsuleForm = modelform_factory(Capsule)
    #### POST method
    if request.method == 'POST':
        form = CapsuleForm(request.POST, instance=capsule)
        if form.is_valid():
            form.save()
        else:
            context = {'form': form,}
            return render(request, template_name, context)
        # fi
        return HttpResponseRedirect(reverse('coffee_capsules:capsule_list'))
    #### NOT POST method
    form = CapsuleForm(instance=capsule)
    context = {'form': form,}
    return render(request, template_name, context)


@login_required
@permission_required('coffee_capsules.add_purchase', raise_exception=True)
@transaction.commit_on_success
def new_purchase(request):
    template_name = 'coffee_capsules/new_purchase.html'
    all_capsule_list = Capsule.objects.order_by('pk')
    n_of_capsules = len(all_capsule_list)
    ## Use formset factory
    PurchaseFormSet = modelformset_factory(Purchase, form=PurchaseForm,
                                           extra=1)
    PurchaseItemFormset = inlineformset_factory(Purchase, PurchaseItem,
                                                form=PurchaseItemForm,
                                                fk_name="purchase",
                                                extra=n_of_capsules)
    #### POST method
    if request.method == 'POST':
        formset = PurchaseFormSet(request.POST, prefix='purchase')
        formset2 = PurchaseItemFormset(request.POST, prefix='purchaseitem')
        ## For a new instance creation, empty form should not be permitted
        for i in range(0, formset.total_form_count()):
            formset.forms[i].empty_permitted = False
        ## Validation and save
        has_error = False
        while True:
            if not formset.is_valid():
                has_error = True
                break
            ## Don't save the instance yet
            purchase_instances = formset.save(commit=False)
            if len(purchase_instances) != 1:
                has_error = True
                break
            ## PurchaseItemFormset requires purchase_instance
            ## for correct validation and save
            formset2 = PurchaseItemFormset(request.POST, prefix='purchaseitem',
                               instance=purchase_instances[0])
            if not formset2.is_valid():
                has_error = True
                break
            ## Save all instances
            purchase_instances[0].save()
            purchaseitem_instances = formset2.save(commit=False)
            for purchaseitem_instance in purchaseitem_instances:
                purchaseitem_instance.save()
            ## Exit from loop
            break
        ## HTTP response
        if not has_error:
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
    #### NOT POST method
    formset = PurchaseFormSet(queryset=Purchase.objects.none(),
                              prefix='purchase')
    ## Initialize formset with all capsules
    initial = []
    for capsule in all_capsule_list:
        initial.append({'capsule': capsule.id,
                        'price': capsule.price,
                        'default_price': capsule.price,
                        })
    formset2 = PurchaseItemFormset(initial=initial, prefix='purchaseitem')
    ## context
    context = {
        'formset': formset,
        'formset2': formset2,
        'capsule_list': all_capsule_list,
    }
    return render(request, template_name, context)


@login_required
@transaction.commit_on_success
def request(request, myid):
    template_name = 'coffee_capsules/request.html'
    purchase = get_object_or_404(Purchase, pk=myid)
    purchaseitem_list = purchase.purchaseitem_set.order_by('capsule__pk')
    available_capsule_list = []
    for purchaseitem in purchaseitem_list:
        available_capsule_list.append(purchaseitem.capsule)
    RequestFormset = modelformset_factory(Request, form=MyRequestForm,
                                          extra=len(available_capsule_list))
    #### POST method
    if request.method == 'POST':
        formset = RequestFormset(request.POST)
        if formset.is_valid():
            request_instances = formset.save(commit=False)
            for request_instance in request_instances:
                request_instance.user = request.user
                request_instance.save()
            messages.success(request, 'Success')
            return HttpResponseRedirect(reverse('coffee_capsules:detail',
                                                args=(purchase.id,)))
        else:
            messages.error(request, 'Error')
            context = {
                'formset': formset,
            }
            return render(request, template_name, context)
    #### NOT POST method
    ## Initialize formset with all capsules
    initial = []
    for purchaseitem in purchaseitem_list:
        initial.append({'purchaseitem': purchaseitem, 'user': request.user})
    formset = RequestFormset(queryset=Request.objects.none(), initial=initial)
    context = {
        'formset': formset,
    }
    return render(request, template_name, context)


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
    query_str_capsule = (
        'SELECT "coffee_capsules_capsule"."id", "name"'
        ' FROM "coffee_capsules_capsule"'
        ' INNER JOIN "coffee_capsules_purchaseitem" ON '
        ' ("coffee_capsules_capsule"."id"'
        ' = "coffee_capsules_purchaseitem"."capsule_id")'
        ' WHERE "coffee_capsules_purchaseitem"."purchase_id" = %s'
        ' ORDER BY "coffee_capsules_capsule"."id"'
    )
    cursor.execute(query_str_capsule, [myid])
    capsule_list = cursor.fetchall()
    #### make query string for selection
    aggregate_str = (
        '"SUM(CASE WHEN capsule_id=" || coffee_capsules_capsule.id'
        ' || " THEN coffee_capsules_request.{0}'
        ' ELSE 0 END) AS {1}"'
        ' || coffee_capsules_capsule.id AS {2}'
    )
    from_str = (
        ' FROM "coffee_capsules_capsule"'
        ' INNER JOIN "coffee_capsules_purchaseitem" ON '
        ' ("coffee_capsules_capsule"."id"'
        ' = "coffee_capsules_purchaseitem"."capsule_id")'
        ' WHERE "coffee_capsules_purchaseitem"."purchase_id" = %s'
        ' ORDER BY "coffee_capsules_capsule"."id"'
    )
    if not agq:
        inner_str = 'SELECT '\
                + aggregate_str.format('quantity_accepted', 'qty_a_', 'ca')\
                + from_str
        query_str_0 = 'SELECT'\
                + ' group_concat(ca, ", ") AS gc'\
                + ' FROM (' + inner_str + ')'
    else:
        inner_str = 'SELECT '\
                + aggregate_str.format('quantity_accepted', 'qty_a_', 'ca')\
                + ', '\
                + aggregate_str.format('quantity_grouped', 'qty_g_', 'cg')\
                + ', '\
                + aggregate_str.format('quantity_queued', 'qty_q_', 'cq')\
                + from_str
        query_str_0 = 'SELECT'\
                + ' group_concat(ca || ", " || cg || ", " || cq, ", ") AS gc'\
                + ' FROM (' + inner_str + ')'
    # fi
    cursor.execute(query_str_0, [myid])
    select_str = cursor.fetchall()[0][0]
    if select_str is None:
        select_str = 'COUNT(*)'
    #### get pivot table
    query_str_1 = 'SELECT auth_user.username, ' + select_str
    if not agq:
        query_str_1 += (
            ', SUM(coffee_capsules_request.quantity_accepted) AS SUM_a'
            ', SUM(coffee_capsules_purchaseitem.price'
            ' * coffee_capsules_request.quantity_accepted) AS GT_a'
        )
    else:
        query_str_1 += (
            ', SUM(coffee_capsules_request.quantity_accepted) AS SUM_a'
            ', SUM(coffee_capsules_request.quantity_grouped) AS SUM_g'
            ', SUM(coffee_capsules_request.quantity_queued) AS SUM_q'
            ', SUM(coffee_capsules_purchaseitem.price'
            ' * coffee_capsules_request.quantity_accepted) AS GT_a'
            ', SUM(coffee_capsules_purchaseitem.price'
            ' * coffee_capsules_request.quantity_grouped) AS GT_g'
            ', SUM(coffee_capsules_purchaseitem.price'
            ' * coffee_capsules_request.quantity_queued) AS GT_q'
        )
    # fi
    query_str_1 += (
        ' FROM "coffee_capsules_request"'
        ' INNER JOIN "coffee_capsules_purchaseitem" ON '
        ' ("coffee_capsules_request"."purchaseitem_id"'
        ' = "coffee_capsules_purchaseitem"."id")'
        ' INNER JOIN "auth_user" ON'
        ' ("coffee_capsules_request"."user_id" = "auth_user"."id")'
        ' WHERE "coffee_capsules_purchaseitem"."purchase_id" = %s'
        ' GROUP BY coffee_capsules_request.user_id'
    )
    cursor.execute(query_str_1, [myid])
    request_list = cursor.fetchall()
    #### get total row
    total_row = [sum(x) if i > 0 else 'Total' for i, x
                 in enumerate(zip(*request_list))]
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
