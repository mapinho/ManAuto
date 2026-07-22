from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.selecionar_organizacao, name="selecionar_organizacao"),
]
