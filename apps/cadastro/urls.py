from django.urls import path

from . import views

app_name = "cadastro"

urlpatterns = [
    path("", views.index, name="frota"),
    path("ativo/<int:ativo_id>/numero/", views.atualizar_numero, name="atualizar_numero"),
    path("ativo/<int:ativo_id>/select/", views.atualizar_select, name="atualizar_select"),
    path("ativo/<int:ativo_id>/classe/", views.atualizar_classe, name="atualizar_classe"),
    path("ativo/<int:ativo_id>/oficina/", views.atualizar_oficina, name="atualizar_oficina"),
    path("ativo/<int:ativo_id>/garantia/", views.atualizar_garantia, name="atualizar_garantia"),
]
