import json
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Avg, Count
from apps.crops.models import CropListing, CropCategory
from apps.buyers.models import SavedCrop
from apps.reviews.models import Review
from .services import MarketplaceFilterService

def index(request):
    qs = MarketplaceFilterService.filter_listings(request.GET)
    categories = CropCategory.objects.filter(is_active=True)
    
    # States and Districts for dynamic filter dropdowns
    states = CropListing.objects.filter(
        status=CropListing.Status.ACTIVE
    ).values_list('state', flat=True).distinct().order_by('state')
    
    districts = CropListing.objects.filter(
        status=CropListing.Status.ACTIVE
    ).values_list('district', flat=True).distinct().order_by('district')
    
    # Map markers list for Leaflet interactive map view
    map_markers = []
    for c in qs.filter(latitude__isnull=False, longitude__isnull=False)[:50]:
        map_markers.append({
            'id': str(c.id),
            'title': c.title,
            'price': float(c.price_per_unit),
            'unit': c.unit,
            'quantity': float(c.quantity_remaining),
            'district': c.district,
            'state': c.state,
            'lat': float(c.latitude),
            'lng': float(c.longitude),
            'url': f"/marketplace/crop/{c.id}/",
            'is_verified': bool(c.farmer.farmer_profile.is_verified) if hasattr(c.farmer, 'farmer_profile') else False
        })
    
    # Pagination (12 listings per page)
    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Wishlist IDs for authenticated buyers
    user_saved_crop_ids = set()
    if request.user.is_authenticated and request.user.is_buyer:
        user_saved_crop_ids = set(
            SavedCrop.objects.filter(buyer=request.user).values_list('crop_listing_id', flat=True)
        )

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'states': states,
        'districts': districts,
        'quality_grades': CropListing.QualityGrade.choices,
        'farming_types': CropListing.FarmingType.choices,
        'total_count': paginator.count,
        'user_saved_crop_ids': user_saved_crop_ids,
        'filters': request.GET,
        'map_markers_json': json.dumps(map_markers),
    }
    return render(request, 'marketplace/index.html', context)

def crop_detail(request, pk):
    crop = get_object_or_404(
        CropListing.objects.select_related('farmer', 'farmer__farmer_profile', 'category'),
        pk=pk
    )
    
    # Increment view counter
    crop.views_count += 1
    crop.save(update_fields=['views_count'])

    # Track recently viewed crops in user session
    recently_viewed = request.session.get('recently_viewed_crops', [])
    str_pk = str(crop.pk)
    if str_pk in recently_viewed:
        recently_viewed.remove(str_pk)
    recently_viewed.insert(0, str_pk)
    request.session['recently_viewed_crops'] = recently_viewed[:10]
    request.session.modified = True

    # Check if saved to wishlist
    is_saved = False
    if request.user.is_authenticated and request.user.is_buyer:
        is_saved = SavedCrop.objects.filter(buyer=request.user, crop_listing=crop).exists()

    # Farmer reviews & rating
    farmer_reviews = Review.objects.filter(reviewee=crop.farmer)
    rating_data = farmer_reviews.aggregate(avg=Avg('rating'), count=Count('id'))
    farmer_rating = round(rating_data['avg'], 1) if rating_data['avg'] else 5.0
    reviews_count = rating_data['count'] or 0

    # Additional gallery images
    gallery = crop.gallery_images.all()

    # Similar produce recommendations
    related_crops = CropListing.objects.filter(
        category=crop.category,
        status=CropListing.Status.ACTIVE
    ).exclude(id=crop.id)[:4]

    # Other active listings by the same farmer
    farmer_other_crops = CropListing.objects.filter(
        farmer=crop.farmer,
        status=CropListing.Status.ACTIVE
    ).exclude(id=crop.id)[:4]

    context = {
        'crop': crop,
        'is_saved': is_saved,
        'gallery': gallery,
        'farmer_rating': farmer_rating,
        'reviews_count': reviews_count,
        'farmer_reviews': farmer_reviews[:3],
        'related_crops': related_crops,
        'farmer_other_crops': farmer_other_crops,
    }
    return render(request, 'marketplace/crop_detail.html', context)
