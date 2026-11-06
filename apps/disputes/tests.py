from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import User
from apps.farmers.models import FarmerProfile
from apps.buyers.models import BuyerProfile
from apps.crops.models import CropCategory, CropListing
from apps.contracts.models import Contract
from apps.disputes.models import Dispute, DisputeMessage

class DisputeManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = CropCategory.objects.create(name='Fiber', slug='fiber')

        self.farmer = User.objects.create_user(
            email='farmer.disp@agrisure.in', password='Password123!',
            first_name='Baldev', last_name='Singh', role=User.Role.FARMER,
            phone='9811199911', email_verified=True
        )
        FarmerProfile.objects.create(user=self.farmer, farm_name='Baldev Cotton', is_verified=True)

        self.buyer = User.objects.create_user(
            email='buyer.disp@agrisure.in', password='Password123!',
            first_name='Vardhman', last_name='Textiles', role=User.Role.BUYER,
            phone='9822299922', email_verified=True
        )
        BuyerProfile.objects.create(user=self.buyer, company_name='Vardhman Textiles', is_verified=True)

        self.stranger = User.objects.create_user(
            email='stranger@agrisure.in', password='Password123!',
            first_name='Stranger', last_name='User', role=User.Role.BUYER
        )

        self.admin = User.objects.create_user(
            email='admin.disp@agrisure.in', password='Password123!',
            first_name='Platform', last_name='Mediator', role=User.Role.ADMIN,
            is_staff=True, is_superuser=True
        )

        self.crop = CropListing.objects.create(
            farmer=self.farmer, category=self.category, title='Kapas Organic Cotton',
            quantity_available=Decimal('500.00'), quantity_remaining=Decimal('500.00'),
            price_per_unit=Decimal('7500.00'), unit=CropListing.Unit.QUINTAL,
            state='Gujarat', district='Rajkot', status=CropListing.Status.ACTIVE
        )

        self.contract = Contract.objects.create(
            crop_listing=self.crop, farmer=self.farmer, buyer=self.buyer,
            quantity=Decimal('200.00'), unit='quintal', price_per_unit=Decimal('7500.00'),
            total_amount=Decimal('1500000.00'), advance_amount=Decimal('300000.00'),
            delivery_date=date.today() + timedelta(days=25),
            delivery_address='Vardhman Spinning Mill, Ludhiana',
            status=Contract.Status.ACTIVE
        )

    def test_dispute_submission_by_buyer(self):
        """Test buyer submitting a formal dispute moves contract to DISPUTED status."""
        self.client.login(email='buyer.disp@agrisure.in', password='Password123!')
        evidence = SimpleUploadedFile("lab_report.pdf", b"%PDF-1.4 sample lab report", content_type="application/pdf")

        resp = self.client.post(reverse('disputes:file', kwargs={'contract_id': self.contract.id}), {
            'category': Dispute.Category.QUALITY,
            'title': 'Staple Length Below Agreed 29mm Specification',
            'description': 'Laboratory testing showed 26mm average staple length. Requested discount or replacement batch.',
            'evidence_file': evidence
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        disp = Dispute.objects.filter(contract=self.contract).first()
        self.assertIsNotNone(disp)
        self.assertEqual(disp.category, Dispute.Category.QUALITY)
        self.assertEqual(disp.raised_by, self.buyer)
        self.assertEqual(disp.against_party, self.farmer)
        self.assertEqual(disp.status, Dispute.Status.OPEN)
        self.assertTrue(disp.dispute_number.startswith('DSP-'))

        # Contract moved to DISPUTED status
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, Contract.Status.DISPUTED)

    def test_unauthorized_dispute_submission_blocked(self):
        """Test non-participant cannot file dispute on third-party contract."""
        self.client.login(email='stranger@agrisure.in', password='Password123!')
        resp = self.client.post(reverse('disputes:file', kwargs={'contract_id': self.contract.id}), {
            'category': Dispute.Category.PAYMENT,
            'title': 'Intruder dispute',
            'description': 'Should fail'
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Dispute.objects.filter(contract=self.contract).count(), 0)

    def test_dispute_resolution_by_admin(self):
        """Test admin reviewing evidence and recording arbitration resolution."""
        disp = Dispute.objects.create(
            contract=self.contract,
            raised_by=self.farmer,
            against_party=self.buyer,
            category=Dispute.Category.PAYMENT,
            title='Withheld Advance Settlement',
            description='Advance deposit was not credited within contractual timeline.'
        )
        self.contract.status = Contract.Status.DISPUTED
        self.contract.save()

        self.client.login(email='admin.disp@agrisure.in', password='Password123!')
        resp = self.client.post(reverse('disputes:resolve', kwargs={'pk': disp.pk}), {
            'status': Dispute.Status.RESOLVED,
            'contract_action': 'RESET_ACTIVE',
            'admin_response': 'Mediation complete. Buyer instructed to release advance within 48 hours.',
            'resolution_details': 'Extension granted of 3 calendar days for dispatch.'
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        disp.refresh_from_db()
        self.assertEqual(disp.status, Dispute.Status.RESOLVED)
        self.assertEqual(disp.resolved_by, self.admin)
        self.assertIsNotNone(disp.resolved_at)

        # Contract reset to ACTIVE as directed by mediation
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, Contract.Status.ACTIVE)

    def test_dispute_messages_timeline(self):
        """Test communication thread inside dispute case file."""
        disp = Dispute.objects.create(
            contract=self.contract,
            raised_by=self.buyer,
            against_party=self.farmer,
            category=Dispute.Category.DAMAGE,
            title='Transit Water Ingress',
            description='10 bags damaged during road transit.'
        )

        self.client.login(email='farmer.disp@agrisure.in', password='Password123!')
        resp = self.client.post(reverse('disputes:detail', kwargs={'pk': disp.pk}), {
            'post_message': '1',
            'message': 'We have contacted the transporter insurance team to replace the 10 bags immediately.'
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(disp.messages.count(), 1)
        msg = disp.messages.first()
        self.assertEqual(msg.sender, self.farmer)
        self.assertIn('transporter insurance', msg.message)

