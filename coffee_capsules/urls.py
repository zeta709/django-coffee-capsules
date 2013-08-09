from django.conf.urls import patterns, url

from coffee_capsules import views

urlpatterns = patterns(
    '',
    url(r'^$', views.IndexView.as_view(), name='index'),
    # capsule
    url(r'^capsule/$', views.CapsuleList.as_view(), name='capsule_list'),
    url(r'^capsule/add/$', views.edit_capsule, name='add_capsule'),
    url(r'^capsule/edit/(?P<myid>\d+)/$', views.edit_capsule,
        name='edit_capsule'),
    # purchase
    url(r'^new_purchase/$', views.new_purchase, name='new_purchase'),
    url(r'^(?P<myid>\d+)/$', views.detail, name='detail'),
    url(r'^(?P<myid>\d+)/request/$', views.request, name='request'),
)
