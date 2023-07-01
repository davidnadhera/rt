from django.urls import path, register_converter
from . import ajax_views, converters

register_converter(converters.FloatUrlParameterConverter, 'float')

app_name = 'ajax'
urlpatterns = [
    path('detail/<int:id>/<float:koef>', ajax_views.detail, name='detail'),
    path('detail_trasy/<int:id>', ajax_views.detail_trasy, name='detail_trasy'),
    path('change_doba1', ajax_views.change_doba1, name='change_doba1'),
    path('change_doba2', ajax_views.change_doba2, name='change_doba2'),
    path('change_active', ajax_views.change_active, name='change_active'),
    path('ajax/iterace', ajax_views.iterace, name='iterace'),
    path('ajax/pocet_tras', ajax_views.pocet_tras, name='pocet_tras'),
    path('ajax/fetch_trasy', ajax_views.fetch_trasy, name='fetch_trasy'),
    path('ajax/zastavit', ajax_views.zastavit, name='zastavit'),
    path('ajax/vypocet_tras', ajax_views.vypocet_tras, name='vypocet_tras')
]