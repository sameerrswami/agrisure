from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User
from apps.farmers.models import FarmerProfile
from apps.buyers.models import BuyerProfile
from apps.crops.models import CropCategory, CropListing
from apps.contracts.models import Contract
from decimal import Decimal

class AgriSureWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create Category
        self.category = CropCategory.objects.create(name='Cereals', slug='cereals')
        
        # Create Farmer
        self.farmer = User.objects.create_user(
            email='test.farmer@agrisure.in',
            password='Password123!',
            first_name='Test',
            last_name='Farmer',
            role=User.Role.FARMER,
            email_verified=True
        )
        self.farmer_profile = FarmerProfile.objects.create(
            user=self.farmer,
            farm_name='Test Agro',
            farm_size=Decimal('10.0'),
            state='Punjab',
            district='Ludhiana'
        )

        # Create Buyer
        self.buyer = User.objects.create_user(
            email='test.buyer@agrisure.in',
            password='Password123!',
            first_name='Test',
            last_name='Buyer',
            role=User.Role.BUYER,
            email_verified=True
        )
        self.buyer_profile = BuyerProfile.objects.create(
            user=self.buyer,
            company_name='Test Buyer Corp',
            city='Delhi',
            state='Delhi'
        )

        # Create Crop Listing
        self.crop = CropListing.objects.create(
            farmer=self.farmer,
            category=self.category,
            title='Test Basmati Rice',
            description='Export grade basmati rice.',
            quantity_available=Decimal('100.00'),
            quantity_remaining=Decimal('100.00'),
            unit=CropListing.Unit.QUINTAL,
            price_per_unit=Decimal('3500.00'),
            status=CropListing.Status.ACTIVE,
            district='Ludhiana',
            state='Punjab'
        )

    def test_farmer_registration(self):
        """Test farmer registration creates a user with FARMER role."""
        response = self.client.post(reverse('accounts:register_farmer'), {
            'first_name': 'New',
            'last_name': 'Kisan',
            'email': 'new.kisan@agrisure.in',
            'phone': '9876543210',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email='new.kisan@agrisure.in')
        self.assertTrue(user.is_farmer)
        self.assertEqual(user.role, User.Role.FARMER)

    def test_buyer_registration(self):
        """Test buyer registration creates a user with BUYER role."""
        response = self.client.post(reverse('accounts:register_buyer'), {
            'first_name': 'Corporate',
            'last_name': 'Procurement',
            'company_name': 'Global Agri Foods',
            'email': 'new.buyer@agrisure.in',
            'phone': '9876543211',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email='new.buyer@agrisure.in')
        self.assertTrue(user.is_buyer)
        self.assertEqual(user.role, User.Role.BUYER)

    def test_role_based_redirects(self):
        """Test logged-in users redirect to their respective dashboard."""
        self.client.login(email='test.farmer@agrisure.in', password='Password123!')
        response = self.client.get(reverse('accounts:role_redirect'))
        self.assertRedirects(response, reverse('farmers:dashboard'))
        self.client.logout()

        self.client.login(email='test.buyer@agrisure.in', password='Password123!')
        response = self.client.get(reverse('accounts:role_redirect'))
        self.assertRedirects(response, reverse('buyers:dashboard'))
        self.client.logout()

    def test_unauthorized_access_prevented(self):
        """Test a buyer cannot access farmer-only dashboard and vice versa."""
        # Buyer accessing farmer dashboard -> 403 Forbidden
        self.client.login(email='test.buyer@agrisure.in', password='Password123!')
        response = self.client.get(reverse('farmers:dashboard'))
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        # Farmer accessing buyer dashboard -> 403 Forbidden
        self.client.login(email='test.farmer@agrisure.in', password='Password123!')
        response = self.client.get(reverse('buyers:dashboard'))
        self.assertEqual(response.status_code, 403)
        self.client.logout()

    def test_marketplace_filtering_and_discovery(self):
        """Test public marketplace search and category filtering."""
        response = self.client.get(reverse('marketplace:index'), {'category': 'cereals'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Basmati Rice')

    def test_crop_quantity_validation(self):
        """Test negative price and invalid quantities are blocked."""
        self.client.login(email='test.farmer@agrisure.in', password='Password123!')
        response = self.client.post(reverse('crops:create'), {
            'category': self.category.id,
            'title': 'Invalid Negative Price Crop',
            'description': 'Test invalid.',
            'quantity_available': -50,
            'unit': 'quintal',
            'price_per_unit': -200,
            'state': 'Punjab',
            'district': 'Ludhiana',
            'status': 'ACTIVE'
        })
        self.assertEqual(response.status_code, 200) # Re-rendered form with errors
        self.assertFalse(CropListing.objects.filter(title='Invalid Negative Price Crop').exists())

    def test_wishlist_functionality(self):
        """Test buyer can add and remove items from wishlist."""
        self.client.login(email='test.buyer@agrisure.in', password='Password123!')
        # Toggle add
        response = self.client.get(reverse('buyers:toggle_wishlist', kwargs={'crop_id': self.crop.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.buyer.saved_crops.filter(crop_listing=self.crop).exists())
        
        # Toggle remove
        response = self.client.get(reverse('buyers:toggle_wishlist', kwargs={'crop_id': self.crop.id}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.buyer.saved_crops.filter(crop_listing=self.crop).exists())

    def test_contract_request_and_acceptance(self):
        """Test contract request, calculation, and digital acceptance."""
        self.client.login(email='test.buyer@agrisure.in', password='Password123!')
        response = self.client.post(reverse('contracts:request', kwargs={'crop_id': self.crop.id}), {
            'quantity': 50,
            'price_per_unit': 3500,
            'advance_payment_percentage': 20,
            'delivery_date': '2026-12-01',
            'delivery_address': 'Delhi Hub',
            'buyer_message': 'Looking forward to contract.'
        })
        self.assertEqual(response.status_code, 302)
        contract = Contract.objects.filter(farmer=self.farmer, buyer=self.buyer).first()
        self.assertIsNotNone(contract)
        self.assertEqual(contract.total_amount, Decimal('175000.00'))
        self.assertEqual(contract.advance_amount, Decimal('35000.00'))
        self.client.logout()

        # Farmer accepts
        self.client.login(email='test.farmer@agrisure.in', password='Password123!')
        accept_resp = self.client.get(reverse('contracts:accept', kwargs={'pk': contract.id}))
        self.assertEqual(accept_resp.status_code, 302)
        contract.refresh_from_db()
        self.assertEqual(contract.status, Contract.Status.ACTIVE)
        self.assertTrue(contract.farmer_accepted)
        self.assertTrue(contract.buyer_accepted)
        # Quantity remaining on crop deducted from 100 to 50
        self.crop.refresh_from_db()
        self.assertEqual(self.crop.quantity_remaining, Decimal('50.00'))

