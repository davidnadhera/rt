from django.urls import path
from . import views

app_name = 'railtour'
urlpatterns = [
    path("",views.trasy, name='trasy'),
    path('stanice', views.stanice, name='stanice'),
    path('spojeni', views.spojeni, name='spojeni'),
    path('odjezdy', views.odjezdy, name='odjezdy'),
]