from django.db.models import Q
from apps.crops.models import CropListing

class MarketplaceFilterService:
    @staticmethod
    def filter_listings(params):
        qs = CropListing.objects.filter(
            status=CropListing.Status.ACTIVE,
            quantity_remaining__gt=0
        ).select_related('farmer', 'farmer__farmer_profile', 'category')

        # Keyword search across title, variety, description, category, district, state
        q = params.get('q')
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(variety__icontains=q) |
                Q(description__icontains=q) |
                Q(category__name__icontains=q) |
                Q(district__icontains=q) |
                Q(state__icontains=q)
            )

        # Category filter
        cat = params.get('category')
        if cat:
            qs = qs.filter(category__slug=cat)

        # State filter
        state = params.get('state')
        if state:
            qs = qs.filter(state__iexact=state)

        # District filter
        district = params.get('district')
        if district:
            qs = qs.filter(district__iexact=district)

        # Price range filters
        min_price = params.get('min_price')
        if min_price:
            try:
                qs = qs.filter(price_per_unit__gte=float(min_price))
            except (ValueError, TypeError):
                pass

        max_price = params.get('max_price')
        if max_price:
            try:
                qs = qs.filter(price_per_unit__lte=float(max_price))
            except (ValueError, TypeError):
                pass

        # Quantity filter
        min_qty = params.get('min_quantity')
        if min_qty:
            try:
                qs = qs.filter(quantity_remaining__gte=float(min_qty))
            except (ValueError, TypeError):
                pass

        # Quality grade filter
        grade = params.get('grade')
        if grade:
            qs = qs.filter(quality_grade=grade)

        # Harvest date filters
        harvest_before = params.get('harvest_before')
        if harvest_before:
            qs = qs.filter(expected_harvest_date__lte=harvest_before)

        harvest_after = params.get('harvest_after')
        if harvest_after:
            qs = qs.filter(expected_harvest_date__gte=harvest_after)

        # Verified farmer only filter
        verified_only = params.get('verified_only')
        if verified_only in ['1', 'true', 'on']:
            qs = qs.filter(farmer__farmer_profile__is_verified=True)

        # Farming type (e.g. ORGANIC, NATURAL, CONVENTIONAL)
        farming_type = params.get('farming_type')
        if farming_type:
            qs = qs.filter(farming_type=farming_type)

        # Sorting
        sort = params.get('sort', 'newest')
        valid_sorts = {
            'newest': '-created_at',
            'price_low': 'price_per_unit',
            'price_high': '-price_per_unit',
            'quantity_high': '-quantity_remaining',
            'harvest_soon': 'expected_harvest_date',
        }
        order_by_field = valid_sorts.get(sort, '-created_at')
        qs = qs.order_by(order_by_field)

        return qs
