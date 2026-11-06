from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User
from apps.farmers.models import FarmerProfile
from apps.buyers.models import BuyerProfile
from apps.crops.models import CropCategory, CropListing
from apps.contracts.models import Contract
from apps.reviews.models import Review

class ReviewSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = CropCategory.objects.create(name='Spices', slug='spices')

        self.farmer = User.objects.create_user(
            email='farmer.rev@agrisure.in', password='Password123!',
            first_name='Anand', last_name='Patel', role=User.Role.FARMER,
            phone='9811188811', email_verified=True
        )
        FarmerProfile.objects.create(user=self.farmer, farm_name='Patel Spices', is_verified=True)

        self.buyer = User.objects.create_user(
            email='buyer.rev@agrisure.in', password='Password123!',
            first_name='MDH', last_name='Spices', role=User.Role.BUYER,
            phone='9822288822', email_verified=True
        )
        BuyerProfile.objects.create(user=self.buyer, company_name='MDH Spices', is_verified=True)

        self.crop = CropListing.objects.create(
            farmer=self.farmer, category=self.category, title='Salem Turmeric Curcumin 4.5%',
            quantity_available=Decimal('100.00'), quantity_remaining=Decimal('100.00'),
            price_per_unit=Decimal('9000.00'), unit=CropListing.Unit.QUINTAL,
            state='Tamil Nadu', district='Salem', status=CropListing.Status.ACTIVE
        )

        self.completed_contract = Contract.objects.create(
            crop_listing=self.crop, farmer=self.farmer, buyer=self.buyer,
            quantity=Decimal('50.00'), unit='quintal', price_per_unit=Decimal('9000.00'),
            total_amount=Decimal('450000.00'), advance_amount=Decimal('90000.00'),
            delivery_date=date.today() - timedelta(days=10),
            delivery_address='MDH Spice Processing Hub, Chennai',
            status=Contract.Status.COMPLETED
        )

        self.active_contract = Contract.objects.create(
            crop_listing=self.crop, farmer=self.farmer, buyer=self.buyer,
            quantity=Decimal('20.00'), unit='quintal', price_per_unit=Decimal('9000.00'),
            total_amount=Decimal('180000.00'), advance_amount=Decimal('36000.00'),
            delivery_date=date.today() + timedelta(days=15),
            delivery_address='MDH Spice Processing Hub, Chennai',
            status=Contract.Status.ACTIVE
        )

    def test_review_submission_for_completed_contract(self):
        """Test buyer submitting 5-star review for a completed contract."""
        self.client.login(email='buyer.rev@agrisure.in', password='Password123!')
        resp = self.client.post(reverse('reviews:create', kwargs={'contract_id': self.completed_contract.id}), {
            'rating': '5',
            'quality_rating': '5',
            'timeliness_rating': '5',
            'communication_rating': '5',
            'title': 'Highest Grade Turmeric with 4.8% Curcumin',
            'comment': 'Exceptional purity and lab verified curcumin levels. Excellent farmer partnership.'
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        review = Review.objects.filter(contract=self.completed_contract, reviewer=self.buyer).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.rating, 5)
        self.assertTrue(review.is_verified_transaction)
        self.assertEqual(review.reviewee, self.farmer)

        # Farmer average rating updated in profile
        self.farmer.farmer_profile.refresh_from_db()
        self.assertEqual(float(self.farmer.farmer_profile.average_rating), 5.0)

    def test_review_rejected_for_non_completed_contract(self):
        """Test reviews cannot be submitted for ongoing or uncompleted contracts."""
        self.client.login(email='buyer.rev@agrisure.in', password='Password123!')
        resp = self.client.post(reverse('reviews:create', kwargs={'contract_id': self.active_contract.id}), {
            'rating': '4',
            'comment': 'Should be rejected because contract is active'
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Review.objects.filter(contract=self.active_contract).count(), 0)

    def test_duplicate_review_prevented(self):
        """Test user cannot review the same completed contract more than once."""
        Review.objects.create(
            contract=self.completed_contract,
            reviewer=self.buyer,
            reviewee=self.farmer,
            rating=5,
            comment='First verified review'
        )

        self.client.login(email='buyer.rev@agrisure.in', password='Password123!')
        resp = self.client.post(reverse('reviews:create', kwargs={'contract_id': self.completed_contract.id}), {
            'rating': '1',
            'comment': 'Second duplicate attempt'
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        # Still only 1 review
        self.assertEqual(Review.objects.filter(contract=self.completed_contract, reviewer=self.buyer).count(), 1)
