from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/connections/", views.test_connections, name="test-connections"),
    path("api/tables/", views.list_tables, name="list-tables"),
    path("api/columns/", views.get_columns, name="get-columns"),
    path("api/migrate/", views.run_migration, name="run-migration"),
    path("api/preview/", views.preview_migration, name="preview-migration"),
]
