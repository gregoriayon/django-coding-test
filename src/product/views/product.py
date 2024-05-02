from django.views.generic import TemplateView, ListView, DetailView
from django.shortcuts import render, HttpResponse
from django.core.paginator import Paginator

from rest_framework.generics import CreateAPIView, RetrieveAPIView, RetrieveUpdateAPIView
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_200_OK
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from product.models import (
    Variant, 
    Product,
    ProductVariant, 
    ProductVariantPrice,
    ProductImage,
)
from product.serializers import ProductSerializer


class CreateProductView(TemplateView):
    template_name = 'products/create.html'

    def get_context_data(self, **kwargs):
        context = super(CreateProductView, self).get_context_data(**kwargs)
        variants = Variant.objects.filter(active=True).values('id', 'title')
        context['product'] = True
        context['variants'] = list(variants.all())
        return context
    


class ProductListView(ListView):
    template_name = 'products/list.html'
    model = Product
    context_object_name = "products"
    paginate_by = 2

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        variants = Variant.objects.filter(active=True)
        options_list = []
        if variants:
            for i in variants:
                options = i.productvariant_set.all().order_by("-variant_title").values_list("variant_title", flat=True).distinct()
                options_list.append({i.title: options})

        context["options_list"] = options_list
        return context


def get_product_search_list(request):
    title = request.POST.get("title", "")
    variant = request.POST.get("variant", "")
    price_from = request.POST.get("price_from", "")
    price_to = request.POST.get("price_to", "")
    date = request.POST.get("date", "")

    search_list = Product.objects.all()

    if title:
        search_list = search_list.filter(title__icontains=title).distinct()
    if variant:
        search_list = search_list.filter(productvariant__variant_title=variant).distinct()
    if price_from:
        search_list = search_list.filter(productvariantprice__price__gte=float(price_from)).distinct()
    if price_to:
        search_list = search_list.filter(productvariantprice__price__lte=float(price_to)).distinct()
    if date:
        search_list = search_list.filter(created_at__date=date).distinct()
    
    

    page_number = request.GET.get('page')
    items_per_page = 2
    paginator = Paginator(search_list, items_per_page)
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj":page_obj
    }

    return render(request, "products/search_result.html", context)



class CreateProductAPIView(CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            product = serializer.save()
            self.create_product_variants(
                product, request.data.get("product_variant", [])
            )
            self.create_product_variant_prices(
                product, request.data.get("product_variant_prices", [])
            )
            return Response(serializer.data, status=HTTP_201_CREATED)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


    def create_product_variants(self, product, variant_data_list):
        for variant_data in variant_data_list:
            variant = Variant.objects.get(id=variant_data.get("option"))
            for variant_title in variant_data.get("tags", []):
                ProductVariant.objects.create(
                    variant_title=variant_title, product=product, variant=variant
                )

    def create_product_variant_prices(self, product, variant_price_data_list):
        for price_data in variant_price_data_list:
            titles = price_data.get("title", "").split("/")
            product_variants = []
            for title in titles:
                if title:
                    product_variant = ProductVariant.objects.filter(
                        variant_title=title, product=product
                    ).first()
                    if product_variant:
                        product_variants.append(product_variant)
            ProductVariantPrice.objects.create(
                product_variant_one=(
                    product_variants[0] if len(product_variants) > 0 else None
                ),
                product_variant_two=(
                    product_variants[1] if len(product_variants) > 1 else None
                ),
                product_variant_three=(
                    product_variants[2] if len(product_variants) > 2 else None
                ),
                price=price_data.get("price"),
                stock=price_data.get("stock"),
                product=product,
            )
    


class EditProductView(DetailView):
    template_name = "products/edit.html"
    model = Product

    def get_context_data(self, **kwargs):
        context = super(EditProductView, self).get_context_data(**kwargs)
        variants = Variant.objects.filter(active=True).values("id", "title")
        context["product"] = True
        context["variants"] = list(variants.all())
        return context
    



class EditProductAPIView(RetrieveUpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def put(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)

        if serializer.is_valid():
            product = serializer.save()
            self.update_product_variants(product, request.data)
            return Response(serializer.data, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


    def update_product_variants(self, product, data):
        updated_variants = data.get("product_variant", [])
        existing_variants = product.productvariant_set.values_list(
            "variant__id", flat=True
        )
        variants_to_remove = set(existing_variants) - set(
            variant["option"] for variant in updated_variants
        )
        removable_tags = []
        for variant_data in updated_variants:
            variant = Variant.objects.get(id=variant_data["option"])
            prod_variants = product.productvariant_set.filter(variant=variant)
            existing_tags = set(
                prod_variant.variant_title for prod_variant in prod_variants
            )
            updated_tags = set(variant_data["tags"])
            tags_to_add = updated_tags - existing_tags
            tags_to_remove = existing_tags - updated_tags

            # Add new variant tags
            for tag in tags_to_add:
                ProductVariant.objects.create(
                    product=product, variant=variant, variant_title=tag
                )

            # Remove variant tags
            removable_tags.append(
                ProductVariant.objects.filter(
                    product=product, variant=variant, variant_title__in=tags_to_remove
                )
            )

        # Create or update product variant prices
        self.create_or_update_product_variant_prices(
            product, data.get("product_variant_prices", [])
        )

        # Delete product variants
        for queryset in removable_tags:
            queryset.delete()

        # Delete variants
        product.productvariant_set.filter(variant__id__in=variants_to_remove).delete()

    def create_or_update_product_variant_prices(self, product, variant_price_data_list):
        updated_variant_titles = set(
            variant_price["title"] for variant_price in variant_price_data_list
        )
        existing_variant_titles = set(
            self.get_variant_price_title(existing_variant_price)
            for existing_variant_price in product.productvariantprice_set.all()
        )

        variant_prices_to_add = updated_variant_titles - existing_variant_titles
        variant_prices_to_remove = existing_variant_titles - updated_variant_titles
        variant_prices_to_update = existing_variant_titles - variant_prices_to_remove

        # Update existing product variant
        for variant_price_title in variant_prices_to_update:
            title_list = [title for title in variant_price_title.split("/") if title]
            product_variant_price_qs = ProductVariantPrice.objects.filter(
                product=product
            )
            for product_variant_price in product_variant_price_qs:
                is_prod_variant_exists = self.lists_are_equal(
                    title_list, self.get_variant_price_title_list(product_variant_price)
                )
                if is_prod_variant_exists:
                    new_variant_data = self.get_new_variant_data(
                        variant_price_data_list, variant_price_title
                    )
                    product_variant_price.price = new_variant_data.get("price")
                    product_variant_price.stock = new_variant_data.get("stock")
                    product_variant_price.save()

        # Create new product variant price
        for variant_price_title in variant_prices_to_add:
            title_list = [title for title in variant_price_title.split("/") if title]
            product_variant_qs = ProductVariant.objects.filter(
                product=product, variant_title__in=title_list
            )
            new_variant_data = self.get_new_variant_data(
                variant_price_data_list, variant_price_title
            )
            ProductVariantPrice.objects.create(
                product=product,
                product_variant_one=(
                    product_variant_qs[0] if product_variant_qs else None
                ),
                product_variant_two=(
                    product_variant_qs[1] if len(product_variant_qs) > 1 else None
                ),
                product_variant_three=(
                    product_variant_qs[2] if len(product_variant_qs) > 2 else None
                ),
                price=new_variant_data.get("price"),
                stock=new_variant_data.get("stock"),
            )

        # Remove product variant price
        for variant_price_title in variant_prices_to_remove:
            title_list = [title for title in variant_price_title.split("/") if title]
            product_variant_price_qs = ProductVariantPrice.objects.filter(
                product=product
            )
            for product_variant_price in product_variant_price_qs:
                is_prod_variant_exists = self.lists_are_equal(
                    title_list, self.get_variant_price_title_list(product_variant_price)
                )
                if is_prod_variant_exists:
                    product_variant_price.delete()

    def get_variant_price_title_list(self, variant_price):
        return list(
            filter(
                None,
                [
                    (
                        variant_price.product_variant_one.variant_title
                        if variant_price.product_variant_one
                        else None
                    ),
                    (
                        variant_price.product_variant_two.variant_title
                        if variant_price.product_variant_two
                        else None
                    ),
                    (
                        variant_price.product_variant_three.variant_title
                        if variant_price.product_variant_three
                        else None
                    ),
                ],
            )
        )

    def get_variant_price_title(self, variant_price):
        return "/".join(self.get_variant_price_title_list(variant_price)) + "/"

    def lists_are_equal(self, lst1, lst2):
        return sorted(lst1) == sorted(lst2)

    def get_new_variant_data(self, variant_price_data_list, variant_price_title):
        return next(
            (
                item
                for item in variant_price_data_list
                if item["title"] == variant_price_title
            ),
            None,
        )




class RetrieveProductAPIView(RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def retrieve(self, request, *args, **kwargs):
        product = self.get_object()
        serializer = self.get_serializer(product)
        data = serializer.data

        product_variant = self.get_product_variants(product)
        data["product_variant"] = product_variant

        product_variant_prices = self.get_product_variant_prices(product)
        data["product_variant_prices"] = product_variant_prices

        return Response(data)

    def get_product_variants(self, product):
        product_variants = []
        for variant in Variant.objects.all():
            prod_variants = product.productvariant_set.filter(variant=variant)
            tags = [prod_variant.variant_title for prod_variant in prod_variants]
            if tags:
                product_variants.append({"option": variant.id, "tags": tags})
        return product_variants

    def get_product_variant_prices(self, product):
        product_variant_prices = []
        for product_price in product.productvariantprice_set.all():
            title = (
                "/".join(
                    filter(
                        None,
                        [
                            (
                                product_price.product_variant_one.variant_title
                                if product_price.product_variant_one
                                else None
                            ),
                            (
                                product_price.product_variant_two.variant_title
                                if product_price.product_variant_two
                                else None
                            ),
                            (
                                product_price.product_variant_three.variant_title
                                if product_price.product_variant_three
                                else None
                            ),
                        ],
                    )
                )
                + "/"
            )
            product_variant_prices.append(
                {
                    "title": title,
                    "price": product_price.price,
                    "stock": product_price.stock,
                }
            )
        return product_variant_prices

    
