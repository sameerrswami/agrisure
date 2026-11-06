from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import User
from apps.farmers.models import FarmerProfile
from apps.farmers.services import FarmerDashboardService
from apps.buyers.models import BuyerProfile, SavedCrop
from apps.buyers.services import BuyerDashboardService
from apps.crops.models import CropCategory, CropListing, CropImage
from apps.contracts.models import Contract
from apps.payments.models import Payment

class MarketplaceAndDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Categories
        self.cereal_cat = CropCategory.objects.create(name='Cereals', slug='cereals')
        self.pulse_cat = CropCategory.objects.create(name='Pulses', slug='pulses')

        # Farmer 1
        self.farmer1 = User.objects.create_user(
            email='farmer1@agrisure.in',
            password='Password123!',
            first_name='Ramesh',
            last_name='Kumar',
            role=User.Role.FARMER,
            phone='9812345678',
            email_verified=True
        )
        self.farmer1_profile = FarmerProfile.objects.create(
            user=self.farmer1,
            farm_name='Shri Ram Farms',
            farm_size=Decimal('15.5'),
            state='Punjab',
            district='Ludhiana',
            verification_status=FarmerProfile.VerificationStatus.VERIFIED,
            is_verified=True
        )

        # Farmer 2 (Unverified)
        self.farmer2 = User.objects.create_user(
            email='farmer2@agrisure.in',
            password='Password123!',
            first_name='Suresh',
            last_name='Patel',
            role=User.Role.FARMER,
            phone='9812345679',
            email_verified=True
        )
        self.farmer2_profile = FarmerProfile.objects.create(
            user=self.farmer2,
            farm_name='Patel Agro',
            farm_size=Decimal('8.0'),
            state='Gujarat',
            district='Anand',
            verification_status=FarmerProfile.VerificationStatus.NOT_SUBMITTED,
            is_verified=False
        )

        # Buyer
        self.buyer = User.objects.create_user(
            email='buyer@agrisure.in',
            password='Password123!',
            first_name='Anil',
            last_name='Sharma',
            role=User.Role.BUYER,
            phone='9812345680',
            email_verified=True
        )
        self.buyer_profile = BuyerProfile.objects.create(
            user=self.buyer,
            company_name='ITC Agri Sourcing',
            preferred_crops='Basmati Rice, Wheat',
            preferred_locations='Punjab, Haryana',
            required_quantities='500 Quintals'
        )

        # Crops
        self.crop1 = CropListing.objects.create(
            farmer=self.farmer1,
            category=self.cereal_cat,
            title='Organic Basmati Rice 1121',
            variety='Basmati 1121',
            farming_type=CropListing.FarmingType.ORGANIC,
            is_organic=True,
            quantity_available=Decimal('500.00'),
            quantity_remaining=Decimal('500.00'),
            unit=CropListing.Unit.QUINTAL,
            price_per_unit=Decimal('4200.00'),
            status=CropListing.Status.ACTIVE,
            state='Punjab',
            district='Ludhiana',
            expected_harvest_date=date.today() + timedelta(days=20),
            latitude=Decimal('30.9010'),
            longitude=Decimal('75.8573')
        )

        self.crop2 = CropListing.objects.create(
            farmer=self.farmer2,
            category=self.pulse_cat,
            title='Desi Chana Chickpeas',
            variety='Desi',
            farming_type=CropListing.FarmingType.CONVENTIONAL,
            is_organic=False,
            quantity_available=Decimal('200.00'),
            quantity_remaining=Decimal('200.00'),
            unit=CropListing.Unit.QUINTAL,
            price_per_unit=Decimal('5500.00'),
            status=CropListing.Status.ACTIVE,
            state='Gujarat',
            district='Anand',
            expected_harvest_date=date.today() + timedelta(days=45),
            latitude=Decimal('22.5645'),
            longitude=Decimal('72.9289')
        )

    # 1. Marketplace Filtering & Searching Tests
    def test_marketplace_keyword_search(self):
        """Test searching crops by keyword finds matching listings."""
        response = self.client.get(reverse('marketplace:index'), {'q': 'Basmati'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Organic Basmati Rice 1121')
        self.assertNotContains(response, 'Desi Chana Chickpeas')

    def test_marketplace_category_filter(self):
        """Test filtering by category slug."""
        response = self.client.get(reverse('marketplace:index'), {'category': 'pulses'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Desi Chana Chickpeas')
        self.assertNotContains(response, 'Organic Basmati Rice 1121')

    def test_marketplace_verified_farmers_only_filter(self):
        """Test verified farmer filter excludes unverified farmer crops."""
        response = self.client.get(reverse('marketplace:index'), {'verified_only': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Organic Basmati Rice 1121')
        self.assertNotContains(response, 'Desi Chana Chickpeas')

    def test_marketplace_price_range_filter(self):
        """Test filtering with min and max prices."""
        response = self.client.get(reverse('marketplace:index'), {'min_price': '5000'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Desi Chana Chickpeas')
        self.assertNotContains(response, 'Organic Basmati Rice 1121')

    def test_marketplace_sort_by_price(self):
        """Test sorting by price low to high."""
        response = self.client.get(reverse('marketplace:index'), {'sort': 'price_low'})
        self.assertEqual(response.status_code, 200)
        listings = list(response.context['page_obj'])
        self.assertEqual(listings[0].price_per_unit, Decimal('4200.00'))
        self.assertEqual(listings[1].price_per_unit, Decimal('5500.00'))

    # 2. Crop Detail & Session Tracking Tests
    def test_crop_detail_view_and_session_tracking(self):
        """Test viewing crop increments views_count and records session history."""
        initial_views = self.crop1.views_count
        response = self.client.get(reverse('marketplace:crop_detail', kwargs={'pk': self.crop1.pk}))
        self.assertEqual(response.status_code, 200)
        
        self.crop1.refresh_from_db()
        self.assertEqual(self.crop1.views_count, initial_views + 1)
        self.assertIn(str(self.crop1.pk), self.client.session['recently_viewed_crops'])

    # 3. Wishlist Tests (Prompt 2 Section 8)
    def test_wishlist_toggle_and_duplicate_prevention(self):
        """Test adding and removing crops from buyer wishlist without duplicates."""
        self.client.login(email='buyer@agrisure.in', password='Password123!')
        
        # Add to wishlist
        response = self.client.get(reverse('buyers:toggle_wishlist', kwargs={'crop_id': self.crop1.pk}))
        self.assertEqual(SavedCrop.objects.filter(buyer=self.buyer, crop_listing=self.crop1).count(), 1)
        
        # Second click removes it (toggle behavior)
        response = self.client.get(reverse('buyers:toggle_wishlist', kwargs={'crop_id': self.crop1.pk}))
        self.assertEqual(SavedCrop.objects.filter(buyer=self.buyer, crop_listing=self.crop1).count(), 0)

    # 4. Crop Management & Security Tests (Prompt 2 Section 3)
    def test_farmer_crop_creation(self):
        """Test farmer creating a new crop listing."""
        self.client.login(email='farmer1@agrisure.in', password='Password123!')
        response = self.client.post(reverse('crops:create'), {
            'title': 'Sharbati Premium Wheat',
            'category': str(self.cereal_cat.pk),
            'variety': 'Sharbati',
            'farming_type': CropListing.FarmingType.CONVENTIONAL,
            'description': 'High gluten rich golden wheat.',
            'quantity_available': '300.00',
            'unit': CropListing.Unit.QUINTAL,
            'price_per_unit': '2800.00',
            'minimum_order_quantity': '10.00',
            'district': 'Ludhiana',
            'state': 'Punjab',
            'status': CropListing.Status.ACTIVE
        })
        self.assertEqual(response.status_code, 302)
        created_crop = CropListing.objects.get(title='Sharbati Premium Wheat')
        self.assertEqual(created_crop.farmer, self.farmer1)
        self.assertEqual(created_crop.quantity_remaining, Decimal('300.00'))

    def test_prevent_editing_other_farmers_crop(self):
        """Security: Farmer 2 cannot edit Farmer 1's crop (must return 404)."""
        self.client.login(email='farmer2@agrisure.in', password='Password123!')
        response = self.client.get(reverse('crops:edit', kwargs={'pk': self.crop1.pk}))
        self.assertEqual(response.status_code, 404)

    def test_crop_update_quantity(self):
        """Test updating remaining quantity and preventing negative quantity."""
        self.client.login(email='farmer1@agrisure.in', password='Password123!')
        
        # Update valid quantity
        response = self.client.post(
            reverse('crops:update_quantity', kwargs={'pk': self.crop1.pk}),
            {'quantity_remaining': '250.00'}
        )
        self.assertEqual(response.status_code, 302)
        self.crop1.refresh_from_db()
        self.assertEqual(self.crop1.quantity_remaining, Decimal('250.00'))

        # Negative quantity must be rejected
        response = self.client.post(
            reverse('crops:update_quantity', kwargs={'pk': self.crop1.pk}),
            {'quantity_remaining': '-50.00'}
        )
        self.crop1.refresh_from_db()
        self.assertEqual(self.crop1.quantity_remaining, Decimal('250.00'))  # Remains unchanged

    def test_crop_status_toggle(self):
        """Test toggling status between ACTIVE and UNAVAILABLE."""
        self.client.login(email='farmer1@agrisure.in', password='Password123!')
        response = self.client.post(reverse('crops:toggle_status', kwargs={'pk': self.crop1.pk}))
        self.crop1.refresh_from_db()
        self.assertEqual(self.crop1.status, CropListing.Status.UNAVAILABLE)

        # Toggle back to ACTIVE
        response = self.client.post(reverse('crops:toggle_status', kwargs={'pk': self.crop1.pk}))
        self.crop1.refresh_from_db()
        self.assertEqual(self.crop1.status, CropListing.Status.ACTIVE)

    # 5. Farmer & Buyer Dashboard Statistics Calculation
    def test_farmer_dashboard_metrics_calculation(self):
        """Test all 8 farmer dashboard statistics calculate accurately from DB."""
        # Create a contract and payment
        contract = Contract.objects.create(
            contract_number='AGR-TEST-001',
            buyer=self.buyer,
            farmer=self.farmer1,
            crop_listing=self.crop1,
            quantity=Decimal('50.00'),
            unit=CropListing.Unit.QUINTAL,
            price_per_unit=Decimal('4200.00'),
            total_amount=Decimal('210000.00'),
            status=Contract.Status.ACTIVE,
            delivery_date=date.today() + timedelta(days=10)
        )
        Payment.objects.create(
            contract=contract,
            payer=self.buyer,
            payee=self.farmer1,
            amount=Decimal('50000.00'),
            status=Payment.Status.COMPLETED
        )

        metrics = FarmerDashboardService.get_dashboard_metrics(self.farmer1)
        self.assertEqual(metrics['total_listings'], 1)
        self.assertEqual(metrics['active_listings'], 1)
        self.assertEqual(metrics['active_contracts'], 1)
        self.assertEqual(metrics['total_earnings'], Decimal('50000.00'))

    def test_buyer_recommendations_matching(self):
        """Test buyer receives recommendations matching preferred crops (Basmati Rice)."""
        metrics = BuyerDashboardService.get_dashboard_metrics(self.buyer)
        recommended_ids = [c.id for c in metrics['recommended_crops']]
        self.assertIn(self.crop1.id, recommended_ids)
