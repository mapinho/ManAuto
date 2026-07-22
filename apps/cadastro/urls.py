from django.urls import path

from . import views

app_name = "cadastro"

urlpatterns = [
    path("frota/", views.frota, name="frota"),
    path("frota/ativo/<int:ativo_id>/numero/", views.atualizar_numero, name="atualizar_numero"),
    path("frota/ativo/<int:ativo_id>/select/", views.atualizar_select, name="atualizar_select"),
    path("frota/ativo/<int:ativo_id>/classe/", views.atualizar_classe, name="atualizar_classe"),
    path("frota/ativo/<int:ativo_id>/oficina/", views.atualizar_oficina, name="atualizar_oficina"),
    path(
        "frota/ativo/<int:ativo_id>/garantia/", views.atualizar_garantia, name="atualizar_garantia"
    ),
    path("pessoas/", views.pessoas, name="pessoas"),
    path(
        "pessoas/<int:pessoa_id>/numero/",
        views.pessoas_atualizar_numero,
        name="pessoas_atualizar_numero",
    ),
    path(
        "pessoas/<int:pessoa_id>/select/",
        views.pessoas_atualizar_select,
        name="pessoas_atualizar_select",
    ),
    path(
        "pessoas/<int:pessoa_id>/oficina/",
        views.pessoas_atualizar_oficina,
        name="pessoas_atualizar_oficina",
    ),
]
