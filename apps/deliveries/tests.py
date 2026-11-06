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
from apps.deliveries.models import Delivery, DeliveryUpdate
from apps.deliveries.services import DeliveryService

class DeliveryManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = CropCategory.objects.create(name='Pulses', slug='pulses')

        self.farmer = User.objects.create_user(
            email='farmer.delv@agrisure.in', password='Password123!',
            first_name='Harpreet', last_name='Singh', role=User.Role.FARMER,
            phone='9811122299', email_verified=True
        )
        FarmerProfile.objects.create(user=self.farmer, farm_name='Harpreet Pulses', is_verified=True)

        self.buyer = User.objects.create_user(
            email='buyer.delv@agrisure.in', password='Password123!',
            first_name='Tata', last_name='Sampann', role=User.Role.BUYER,
            phone='9822233399', email_verified=True
        )
        BuyerProfile.objects.create(user=self.buyer, company_name='Tata Sampann', is_verified=True)

        self.crop = CropListing.objects.create(
            farmer=self.farmer, category=self.category, title='Organic Chana Dal',
            quantity_available=Decimal('300.00'), quantity_remaining=Decimal('300.00'),
            price_per_unit=Decimal('6200.00'), unit=CropListing.Unit.QUINTAL,
            state='Madhya Pradesh', district='Indore', status=CropListing.Status.ACTIVE
        )

        self.contract = Contract.objects.create(
            crop_listing=self.crop, farmer=self.farmer, buyer=self.buyer,
            quantity=Decimal('100.00'), unit='quintal', price_per_unit=Decimal('6200.00'),
            total_amount=Decimal('620000.00'), advance_amount=Decimal('124000.00'),
            delivery_date=date.today() + timedelta(days=20),
            delivery_address='Tata Central Silo, Indore',
            status=Contract.Status.ACTIVE
        )

    def test_delivery_creation_by_farmer(self):
        """Test scheduling a shipment from an active contract."""
        self.client.login(email='farmer.delv@agrisure.in', password='Password123!')
        resp = self.client.post(reverse('deliveries:create', kwargs={'contract_id': self.contract.id}), {
            'quantity_scheduled': '50.00',
            'unit': 'quintal',
            'pickup_location': 'Indore Farm Gate #2',
            'destination_address': 'Tata Central Silo, Indore',
            'estimated_delivery_date': (date.today() + timedelta(days=5)).isoformat(),
            'delivery_notes': 'Moisture verified under 10%.'
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        delv = Delivery.objects.filter(contract=self.contract).first()
        self.assertIsNotNone(delv)
        self.assertEqual(delv.quantity_scheduled, Decimal('50.00'))
        self.assertEqual(delv.status, Delivery.Status.SCHEDULED)
        self.assertTrue(delv.tracking_number.startswith('DEL-'))

    def test_farmer_dispatch_confirmation(self):
        """Test farmer confirming dispatch with transport & vehicle details."""
        self.client.login(email='farmer.delv@agrisure.in', password='Password123!')
        delv = DeliveryService.create_shipment(
            contract=self.contract,
            scheduled_quantity=Decimal('60.00'),
            pickup_location='Farm Silo',
            destination_address=self.contract.delivery_address,
            estimated_delivery_date=self.contract.delivery_date
        )
        self.assertEqual(delv.status, Delivery.Status.SCHEDULED)

        resp = self.client.post(reverse('deliveries:dispatch', kwargs={'pk': delv.pk}), {
            'transporter_name': 'Indore Roadways Corp',
            'vehicle_number': 'MP-09-CD-5678',
            'driver_name': 'Sukhbir Singh',
            'driver_phone': '9876543210',
            'delivery_notes': 'Dispatched 120 bags.'
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        delv.refresh_from_db()
        self.assertEqual(delv.status, Delivery.Status.DISPATCHED)
        self.assertEqual(delv.vehicle_number, 'MP-09-CD-5678')
        self.assertIsNotNone(delv.dispatched_at)

        # Contract moved to READY_FOR_DELIVERY
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, Contract.Status.READY_FOR_DELIVERY)

    def test_buyer_delivery_confirmation_and_proof_upload(self):
        """Test buyer verifying arrival, recording delivered quantity, and attaching proof."""
        self.client.login(email='buyer.delv@agrisure.in', password='Password123!')
        delv = DeliveryService.create_shipment(
            contract=self.contract,
            scheduled_quantity=Decimal('100.00'),
            pickup_location='Farm Silo',
            destination_address=self.contract.delivery_address,
            estimated_delivery_date=self.contract.delivery_date,
            transporter_name='Express Ag',
            vehicle_number='MP-09-AB-1234'
        )

        test_file = SimpleUploadedFile("proof_slip.pdf", b"%PDF-1.4 test weighbridge slip", content_type="application/pdf")

        resp = self.client.post(reverse('deliveries:confirm', kwargs={'pk': delv.pk}), {
            'quantity_delivered': '100.00',
            'inspection_status': 'VERIFIED',
            'proof_of_delivery': test_file,
            'inspection_notes': 'All 100 quintals inspected and accepted into warehouse Silo A.'
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        delv.refresh_from_db()
        self.assertEqual(delv.status, Delivery.Status.DELIVERED)
        self.assertEqual(delv.quantity_delivered, Decimal('100.00'))
        self.assertEqual(delv.inspection_status, Delivery.InspectionStatus.VERIFIED)
        self.assertIsNotNone(delv.delivered_at)

        # Total contract quantity fulfilled -> Contract moves to DELIVERED (NOT immediately COMPLETED)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, Contract.Status.DELIVERED)
        self.assertEqual(self.contract.delivery_progress_pct, 100)

    def test_partial_delivery_progress_calculation(self):
        """Test multi-shipment and partial delivery progress calculation."""
        delv1 = DeliveryService.create_shipment(
            contract=self.contract,
            scheduled_quantity=Decimal('40.00'),
            pickup_location='Farm Gate',
            destination_address=self.contract.delivery_address,
            estimated_delivery_date=self.contract.delivery_date
        )

        # Buyer verifies 35 quintals received (5 quintals shortage)
        DeliveryService.confirm_receipt(
            delivery=delv1,
            quantity_delivered=Decimal('35.00'),
            inspection_status=Delivery.InspectionStatus.SHORTAGE,
            inspection_notes='Weighbridge recorded 35 quintals.'
        )

        delv1.refresh_from_db()
        self.assertEqual(delv1.status, Delivery.Status.PARTIALLY_DELIVERED)

        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, Contract.Status.PARTIALLY_DELIVERED)
        self.assertEqual(self.contract.total_delivered_quantity, Decimal('35.00'))
        self.assertEqual(self.contract.delivery_progress_pct, 35)
        # Contract MUST NOT be completed merely upon dispatch or partial receipt
        self.assertNotEqual(self.contract.status, Contract.Status.COMPLETED)

