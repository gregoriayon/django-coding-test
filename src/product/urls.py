from django.urls import path
from django.views.generic import TemplateView

from product.views.product import (
    CreateProductView,
    EditProductView,
    ProductListView,

    CreateProductAPIView,
    EditProductAPIView,
    RetrieveProductAPIView,

    get_product_search_list
)
from product.views.variant import VariantView, VariantCreateView, VariantEditView

app_name = "product"
API_URL_PREFIX = "api"

urlpatterns = [
    # Variants URLs
    path('variants/', VariantView.as_view(), name='variants'),
    path('variant/create', VariantCreateView.as_view(), name='create.variant'),
    path('variant/<int:id>/edit', VariantEditView.as_view(), name='update.variant'),

    # Products URLs
    path('create/', CreateProductView.as_view(), name='create.product'),
    path("edit/<int:pk>/", EditProductView.as_view(), name="edit.product"),
    path('list/', ProductListView.as_view(), name='list.product'),
    
    path("search/", get_product_search_list, name="product_search_list"),

    path(f"{API_URL_PREFIX}/create/", CreateProductAPIView.as_view()),
    path(f"{API_URL_PREFIX}/edit/<int:pk>/", EditProductAPIView.as_view()),
    path(f"{API_URL_PREFIX}/retrive/<int:pk>/", RetrieveProductAPIView.as_view()),
]
