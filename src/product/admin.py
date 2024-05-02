from django.contrib import admin
from product.models import (
    Product, 
    Variant, 
    ProductVariant, 
    ProductImage, 
    ProductVariantPrice
)


# Register your models here.

admin.site.register(Product)
admin.site.register(Variant)
admin.site.register(ProductVariant)
admin.site.register(ProductImage)
admin.site.register(ProductVariantPrice)
