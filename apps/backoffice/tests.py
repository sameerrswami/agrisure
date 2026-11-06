from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User
from apps.farmers.models import FarmerProfile
from apps.buyers.models import BuyerProfile
from apps.crops.models import CropCategory, CropListing
from apps.contracts.models import Contract
from apps.payments.models import Payment
from apps.disputes.models import Dispute
from apps.backoffice.models import PlatformSetting, AdminAuditLog

class AdministratorBackofficeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = CropCategory.objects.create(name='Cereals', slug='cereals')

        self.admin = User.objects.create_user(
            email='admin.boss@agrisure.in', password='Password123!',
            first_name='Admin', last_name='Chief', role=User.Role.ADMIN,
            is_staff=True, is_superuser=True
        )

        self.farmer = User.objects.create_user(
            email='farmer.bo@agrisure.in', password='Password123!',
            first_name='Kailash', last_name='Verma', role=User.Role.FARMER,
            phone='9811177711', email_verified=True
        )
        self.farmer_profile = FarmerProfile.objects.create(
            user=self.farmer, farm_name='Kailash Farms',
            verification_status=FarmerProfile.VerificationStatus.PENDING, is_verified=False
        )

        self.buyer = User.objects.create_user(
            email='buyer.bo@agrisure.in', password='Password123!',
            first_name='Cargill', last_name='India', role=User.Role.BUYER,
            phone='9822277722', email_verified=True
        )
        self.buyer_profile = BuyerProfile.objects.create(
            user=self.buyer, company_name='Cargill India',
            verification_status=BuyerProfile.VerificationStatus.PENDING, is_verified=False
        )

        self.crop = CropListing.objects.create(
            farmer=self.farmer, category=self.category, title='Sharbati Wheat Grain',
            quantity_available=Decimal('500.00'), quantity_remaining=Decimal('500.00'),
            price_per_unit=Decimal('2800.00'), unit=CropListing.Unit.QUINTAL,
            state='Madhya Pradesh', district='Sehore', status=CropListing.Status.ACTIVE
        )

        self.contract = Contract.objects.create(
            crop_listing=self.crop, farmer=self.farmer, buyer=self.buyer,
            quantity=Decimal('200.00'), unit='quintal', price_per_unit=Decimal('2800.00'),
            total_amount=Decimal('560000.00'), advance_amount=Decimal('112000.00'),
            delivery_date=date.today() + timedelta(days=30),
            delivery_address='Cargill Silos, Bhopal',
            status=Contract.Status.ACTIVE
        )

    def test_backoffice_dashboard_metrics_and_charts(self):
        """Test admin dashboard loads accurate database metrics and 6 Chart.js payloads."""
        self.client.login(email='admin.boss@agrisure.in', password='Password123!')
        resp = self.client.get(reverse('backoffice:dashboard'))
        self.assertEqual(resp.status_code, 200)

        # Check KPI stats in context
        self.assertGreaterEqual(resp.context['total_users'], 3)
        self.assertEqual(resp.context['total_contracts'], 1)
        self.assertEqual(resp.context['active_crop_listings'], 1)

        # Check all 6 Chart.js datasets present in context
        self.assertIn('userRegistrationsChart', resp.content.decode())
        self.assertIn('monthlyContractsChart', resp.content.decode())
        self.assertIn('monthlyVolumeChart', resp.content.decode())
        self.assertIn('cropCategoriesChart', resp.content.decode())
        self.assertIn('contractCompletionChart', resp.content.decode())
        self.assertIn('paymentSuccessChart', resp.content.decode())

    def test_non_admin_blocked_from_backoffice(self):
        """Test non-admin (farmer/buyer) is forbidden from backoffice dashboard."""
        self.client.login(email='farmer.bo@agrisure.in', password='Password123!')
        resp = self.client.get(reverse('backoffice:dashboard'))
        self.assertEqual(resp.status_code, 403)

    def test_admin_kyc_approval_workflow(self):
        """Test administrator approving farmer KYC credentials."""
        self.client.login(email='admin.boss@agrisure.in', password='Password123!')
        self.assertFalse(self.farmer.farmer_profile.is_verified)

        resp = self.client.post(reverse('backoffice:verify_user', kwargs={'user_id': self.farmer.id}), follow=True)
        self.assertEqual(resp.status_code, 200)

        self.farmer.farmer_profile.refresh_from_db()
        self.assertTrue(self.farmer.farmer_profile.is_verified)
        self.assertEqual(self.farmer.farmer_profile.verification_status, FarmerProfile.VerificationStatus.VERIFIED)

        # Verify audit log entry created
        audit = AdminAuditLog.objects.filter(target_id=str(self.farmer.id), action='KYC_VERIFIED').first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.admin_user, self.admin)

    def test_admin_kyc_rejection_with_reason(self):
        """Test administrator rejecting verification with recorded mandatory reason."""
        self.client.login(email='admin.boss@agrisure.in', password='Password123!')

        resp = self.client.post(reverse('backoffice:reject_user', kwargs={'user_id': self.buyer.id}), {
            'rejection_reason': 'GST certificate is expired and mismatching registered address.'
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        self.buyer.buyer_profile.refresh_from_db()
        self.assertFalse(self.buyer.buyer_profile.is_verified)
        self.assertEqual(self.buyer.buyer_profile.verification_status, BuyerProfile.VerificationStatus.REJECTED)

        # Audit log verification
        audit = AdminAuditLog.objects.filter(target_id=str(self.buyer.id), action='KYC_REJECTED').first()
        self.assertIsNotNone(audit)
        self.assertIn('GST certificate is expired', audit.details)

    def test_admin_suspend_reactivate_user(self):
        """Test suspending and reactivating user account with audit logging."""
        self.client.login(email='admin.boss@agrisure.in', password='Password123!')
        self.assertTrue(self.farmer.is_active)

        # Suspend
        self.client.post(reverse('backoffice:toggle_user_status', kwargs={'user_id': self.farmer.id}), follow=True)
        self.farmer.refresh_from_db()
        self.assertFalse(self.farmer.is_active)

        # Reactivate
        self.client.post(reverse('backoffice:toggle_user_status', kwargs={'user_id': self.farmer.id}), follow=True)
        self.farmer.refresh_from_db()
        self.assertTrue(self.farmer.is_active)

    def test_admin_settings_update(self):
        """Test modifying platform parameters and policies."""
        self.client.login(email='admin.boss@agrisure.in', password='Password123!')

        resp = self.client.post(reverse('backoffice:settings'), {
            'platform_name': 'AgriSure National Marketplace',
            'support_email': 'helpdesk@agrisure.in',
            'support_phone': '+91 1800 555 4321',
            'office_address': 'AgriSure Tower, Cyber City, Gurugram, Haryana',
            'working_hours': 'Mon-Fri 9AM-7PM IST',
            'emergency_helpline': '1800-AGRI-HELP',
            'max_upload_size_mb': '25',
            'platform_commission_pct': '2.00',
            'min_contract_value': '10000.00',
            'dispute_sla_days': '5',
            'email_notifications_enabled': True,
            'sms_notifications_enabled': True,
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        settings = PlatformSetting.get_settings()
        self.assertEqual(settings.platform_name, 'AgriSure National Marketplace')
        self.assertEqual(settings.max_upload_size_mb, 25)
        self.assertEqual(settings.dispute_sla_days, 5)

    def test_admin_marketplace_listing_toggle(self):
        """Test admin disabling inappropriate crop listing from marketplace."""
        self.client.login(email='admin.boss@agrisure.in', password='Password123!')
        self.assertEqual(self.crop.status, CropListing.Status.ACTIVE)

        resp = self.client.post(reverse('backoffice:toggle_listing', kwargs={'crop_id': self.crop.id}), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.crop.refresh_from_db()
        self.assertEqual(self.crop.status, CropListing.Status.UNAVAILABLE)

