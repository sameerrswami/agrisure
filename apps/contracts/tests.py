from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import PermissionDenied
from apps.accounts.models import User
from apps.farmers.models import FarmerProfile
from apps.buyers.models import BuyerProfile
from apps.crops.models import CropCategory, CropListing
from apps.contracts.models import Contract, ContractAcceptance, ContractHistory
from apps.contracts.services import ContractService
from apps.negotiations.models import Negotiation, Offer
from apps.negotiations.services import NegotiationService
from apps.messaging.models import Conversation, Message
from apps.messaging.services import MessagingService
from apps.notifications.models import Notification

class CompleteContractFarmingWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Category
        self.category = CropCategory.objects.create(name='Cereals', slug='cereals')
        
        # Farmer
        self.farmer = User.objects.create_user(
            email='ramesh.farmer@agrisure.in',
            password='Password123!',
            first_name='Ramesh',
            last_name='Kumar',
            role=User.Role.FARMER,
            phone='9876543210',
            email_verified=True
        )
        self.farmer_profile = FarmerProfile.objects.create(
            user=self.farmer,
            farm_name='Shri Ram Organic Farm',
            farm_size=Decimal('25.0'),
            state='Punjab',
            district='Ludhiana',
            is_verified=True,
            verification_status=FarmerProfile.VerificationStatus.VERIFIED
        )

        # Buyer
        self.buyer = User.objects.create_user(
            email='procurement@itc-agri.in',
            password='Password123!',
            first_name='Anil',
            last_name='Sharma',
            role=User.Role.BUYER,
            phone='9876543211',
            email_verified=True
        )
        self.buyer_profile = BuyerProfile.objects.create(
            user=self.buyer,
            company_name='ITC Agri Procurement Ltd',
            gstin='03AAAAA1234A1Z5',
            pan_number='AAAAA1234A',
            delivery_address='Central Silo Facility, Ludhiana'
        )

        # Third party stranger (unauthorized)
        self.stranger = User.objects.create_user(
            email='stranger@agrisure.in',
            password='Password123!',
            first_name='Unauthorized',
            last_name='User',
            role=User.Role.BUYER,
            email_verified=True
        )

        # Crop Listing
        self.crop = CropListing.objects.create(
            farmer=self.farmer,
            category=self.category,
            title='Basmati Paddy 1121 Export Grade',
            variety='1121',
            description='Export grade basmati paddy.',
            quantity_available=Decimal('500.00'),
            quantity_remaining=Decimal('500.00'),
            unit=CropListing.Unit.QUINTAL,
            price_per_unit=Decimal('3800.00'),
            minimum_acceptable_price=Decimal('3500.00'),
            status=CropListing.Status.ACTIVE,
            state='Punjab',
            district='Ludhiana',
            expected_harvest_date=date.today() + timedelta(days=30)
        )

    # -------------------------------------------------------------------------
    # 1. Contract Request System (Prompt 3 Section 1)
    # -------------------------------------------------------------------------
    def test_buyer_contract_request_creation_and_auto_calculation(self):
        """Test buyer submits contract request; calculations and notifications are generated."""
        self.client.login(email='procurement@itc-agri.in', password='Password123!')
        
        response = self.client.post(reverse('contracts:request', kwargs={'crop_id': self.crop.id}), {
            'quantity': '100.00',
            'price_per_unit': '3700.00',
            'advance_payment_percentage': '20',
            'delivery_date': (date.today() + timedelta(days=25)).strftime('%Y-%m-%d'),
            'delivery_address': 'ITC Central Hub, Sector 4, Ludhiana',
            'required_quality_grade': CropListing.QualityGrade.GRADE_A,
            'quality_specifications': 'Moisture < 12%, purity > 98%',
            'payment_terms': '20% escrow advance, 80% post weighment',
            'buyer_message': 'Looking forward to sourcing your premium harvest.'
        })
        self.assertEqual(response.status_code, 302)
        
        contract = Contract.objects.get(crop_listing=self.crop)
        # Check calculations
        self.assertEqual(contract.total_amount, Decimal('370000.00'))  # 100 * 3700
        self.assertEqual(contract.advance_amount, Decimal('74000.00'))  # 20% of 370,000
        self.assertEqual(contract.status, Contract.Status.PENDING_FARMER)
        self.assertTrue(contract.buyer_accepted)
        self.assertEqual(contract.buyer_accepted_version, 1)
        self.assertFalse(contract.farmer_accepted)

        # Check PDF generated
        self.assertTrue(bool(contract.contract_pdf))
        
        # Check Notification sent to farmer
        self.assertTrue(Notification.objects.filter(recipient=self.farmer, notification_type=Notification.Type.CONTRACT).exists())

    # -------------------------------------------------------------------------
    # 2. Price Negotiation System (Prompt 3 Section 2)
    # -------------------------------------------------------------------------
    def test_two_way_negotiation_counter_offer_and_concurrency(self):
        """Test full negotiation: offer, counteroffer, withdraw, and atomic acceptance."""
        # Step 1: Buyer initiates negotiation
        self.client.login(email='procurement@itc-agri.in', password='Password123!')
        self.client.post(reverse('negotiations:start', kwargs={'crop_id': self.crop.id}), {
            'price_per_unit': '3400.00',
            'quantity': '150.00',
            'proposed_delivery_date': (date.today() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'message': 'Initial offer for large volume.'
        })
        negotiation = Negotiation.objects.get(crop_listing=self.crop, buyer=self.buyer)
        self.assertEqual(negotiation.offers.count(), 1)
        first_offer = negotiation.latest_offer
        self.assertEqual(first_offer.price_per_unit, Decimal('3400.00'))
        self.assertEqual(first_offer.status, Offer.Status.PENDING)

        # Step 2: Farmer logs in and submits counter-offer
        self.client.login(email='ramesh.farmer@agrisure.in', password='Password123!')
        self.client.post(reverse('negotiations:counter', kwargs={'pk': negotiation.pk}), {
            'price_per_unit': '3650.00',
            'quantity': '150.00',
            'proposed_delivery_date': (date.today() + timedelta(days=28)).strftime('%Y-%m-%d'),
            'message': 'Best counter price for premium grade 1121.'
        })
        negotiation.refresh_from_db()
        first_offer.refresh_from_db()
        self.assertEqual(first_offer.status, Offer.Status.COUNTERED)  # Old offer marked COUNTERED
        self.assertEqual(negotiation.offers.count(), 2)
        counter_offer = negotiation.latest_offer
        self.assertEqual(counter_offer.price_per_unit, Decimal('3650.00'))
        self.assertEqual(counter_offer.status, Offer.Status.PENDING)

        # Step 3: Farmer cannot accept their own counter-offer
        with self.assertRaises(ValueError):
            NegotiationService.accept_offer(negotiation.id, counter_offer.id, self.farmer)

        # Step 4: Buyer accepts the counter-offer
        self.client.login(email='procurement@itc-agri.in', password='Password123!')
        response = self.client.get(reverse('negotiations:accept_offer', kwargs={'offer_id': counter_offer.id}))
        self.assertEqual(response.status_code, 302)

        counter_offer.refresh_from_db()
        negotiation.refresh_from_db()
        self.assertEqual(counter_offer.status, Offer.Status.ACCEPTED)
        self.assertEqual(negotiation.status, Negotiation.Status.ACCEPTED)
        self.assertEqual(negotiation.final_price_per_unit, Decimal('3650.00'))

        # A formal contract must be generated from agreed terms
        created_contract = Contract.objects.get(crop_listing=self.crop, buyer=self.buyer)
        self.assertEqual(created_contract.price_per_unit, Decimal('3650.00'))
        self.assertEqual(created_contract.quantity, Decimal('150.00'))

    def test_offer_rejection_and_withdrawal(self):
        """Test rejecting an offer and withdrawing an offer."""
        negotiation = Negotiation.objects.create(
            crop_listing=self.crop,
            farmer=self.farmer,
            buyer=self.buyer,
            status=Negotiation.Status.OPEN
        )
        offer = Offer.objects.create(
            negotiation=negotiation,
            submitted_by=self.buyer,
            price_per_unit=Decimal('3300.00'),
            quantity=Decimal('80.00'),
            status=Offer.Status.PENDING
        )

        # Farmer rejects buyer offer
        self.client.login(email='ramesh.farmer@agrisure.in', password='Password123!')
        self.client.get(reverse('negotiations:reject_offer', kwargs={'offer_id': offer.id}))
        offer.refresh_from_db()
        self.assertEqual(offer.status, Offer.Status.REJECTED)

        # Farmer makes a counter offer, then decides to withdraw it
        counter = Offer.objects.create(
            negotiation=negotiation,
            submitted_by=self.farmer,
            price_per_unit=Decimal('3900.00'),
            quantity=Decimal('80.00'),
            status=Offer.Status.PENDING
        )
        self.client.get(reverse('negotiations:withdraw_offer', kwargs={'offer_id': counter.id}))
        counter.refresh_from_db()
        self.assertEqual(counter.status, Offer.Status.WITHDRAWN)

    # -------------------------------------------------------------------------
    # 3. Contract Dual Acceptance & Activation Workflow (Prompt 3 Section 4)
    # -------------------------------------------------------------------------
    def test_two_party_acceptance_and_activation(self):
        """Test contract activation only occurs when BOTH parties accept the current version."""
        contract = Contract.objects.create(
            crop_listing=self.crop,
            farmer=self.farmer,
            buyer=self.buyer,
            title='Contract for Basmati Paddy',
            quantity=Decimal('100.00'),
            unit=CropListing.Unit.QUINTAL,
            price_per_unit=Decimal('3800.00'),
            delivery_date=date.today() + timedelta(days=20),
            delivery_address='Ludhiana Hub',
            status=Contract.Status.PENDING_FARMER,
            version=1,
            buyer_accepted=True,
            buyer_accepted_version=1,
            buyer_accepted_at=timezone.now()
        )
        self.assertFalse(contract.is_fully_accepted)
        self.assertEqual(contract.status, Contract.Status.PENDING_FARMER)

        # Farmer accepts Version 1
        self.client.login(email='ramesh.farmer@agrisure.in', password='Password123!')
        response = self.client.post(reverse('contracts:accept', kwargs={'pk': contract.pk}), {
            'disclaimer_acknowledged': 'on'
        })
        self.assertEqual(response.status_code, 302)

        contract.refresh_from_db()
        self.assertTrue(contract.farmer_accepted)
        self.assertEqual(contract.farmer_accepted_version, 1)
        self.assertTrue(contract.is_fully_accepted)
        self.assertEqual(contract.status, Contract.Status.ACTIVE)

        # Remaining stock deducted from crop listing
        self.crop.refresh_from_db()
        self.assertEqual(self.crop.quantity_remaining, Decimal('400.00'))  # 500 - 100

        # ContractAcceptance records created
        self.assertTrue(ContractAcceptance.objects.filter(contract=contract, user=self.farmer, version=1).exists())

    # -------------------------------------------------------------------------
    # 4. Contract Amendments (Prompt 3 Section 4)
    # -------------------------------------------------------------------------
    def test_contract_amendment_increments_version_and_resets_acceptance(self):
        """Test proposing an amendment creates v2, resets dual acceptance, and requires re-approval."""
        contract = Contract.objects.create(
            crop_listing=self.crop,
            farmer=self.farmer,
            buyer=self.buyer,
            title='Contract for Basmati Paddy',
            quantity=Decimal('100.00'),
            unit=CropListing.Unit.QUINTAL,
            price_per_unit=Decimal('3800.00'),
            delivery_date=date.today() + timedelta(days=20),
            delivery_address='Ludhiana Hub',
            status=Contract.Status.ACTIVE,
            version=1,
            farmer_accepted=True,
            farmer_accepted_version=1,
            buyer_accepted=True,
            buyer_accepted_version=1
        )

        # Buyer proposes amendment (adjusting quantity to 120 and price to 3750)
        self.client.login(email='procurement@itc-agri.in', password='Password123!')
        response = self.client.post(reverse('contracts:amend', kwargs={'pk': contract.pk}), {
            'amendment_reason': 'Expanding procurement quota due to retail surge.',
            'quantity': '120.00',
            'price_per_unit': '3750.00',
            'delivery_date': (date.today() + timedelta(days=22)).strftime('%Y-%m-%d'),
            'delivery_address': 'ITC Central Silo, Ludhiana',
            'required_quality_grade': CropListing.QualityGrade.GRADE_A,
            'quality_specifications': 'Export FAQ',
            'payment_terms': '20% advance, 80% final'
        })
        self.assertEqual(response.status_code, 302)

        contract.refresh_from_db()
        self.assertEqual(contract.version, 2)
        self.assertEqual(contract.quantity, Decimal('120.00'))
        self.assertEqual(contract.total_amount, Decimal('450000.00'))  # 120 * 3750
        # Version 2 is NOT active yet because farmer hasn't approved the amended version
        self.assertFalse(contract.is_fully_accepted)
        self.assertEqual(contract.status, Contract.Status.PENDING_FARMER)
        self.assertFalse(contract.farmer_accepted)
        self.assertTrue(contract.buyer_accepted)
        self.assertEqual(contract.buyer_accepted_version, 2)

    # -------------------------------------------------------------------------
    # 5. Contract Lifecycle State Machine & Security (Prompt 3 Section 5)
    # -------------------------------------------------------------------------
    def test_contract_lifecycle_valid_transitions(self):
        """Test valid state transitions: ACTIVE -> PRODUCTION_IN_PROGRESS -> READY_FOR_DELIVERY -> COMPLETED."""
        contract = Contract.objects.create(
            crop_listing=self.crop,
            farmer=self.farmer,
            buyer=self.buyer,
            title='Contract for Basmati Paddy',
            quantity=Decimal('50.00'),
            unit=CropListing.Unit.QUINTAL,
            price_per_unit=Decimal('3800.00'),
            delivery_date=date.today() + timedelta(days=15),
            delivery_address='Ludhiana Hub',
            status=Contract.Status.ACTIVE
        )

        # Farmer updates to PRODUCTION_IN_PROGRESS
        self.client.login(email='ramesh.farmer@agrisure.in', password='Password123!')
        self.client.post(reverse('contracts:update_status', kwargs={'pk': contract.pk}), {
            'status': Contract.Status.PRODUCTION_IN_PROGRESS,
            'reason': 'Paddy transplanting completed successfully.'
        })
        contract.refresh_from_db()
        self.assertEqual(contract.status, Contract.Status.PRODUCTION_IN_PROGRESS)

        # Farmer updates to READY_FOR_DELIVERY
        self.client.post(reverse('contracts:update_status', kwargs={'pk': contract.pk}), {
            'status': Contract.Status.READY_FOR_DELIVERY,
            'reason': 'Harvested and bagged in 50kg standard jute bags.'
        })
        contract.refresh_from_db()
        self.assertEqual(contract.status, Contract.Status.READY_FOR_DELIVERY)

        # Buyer marks COMPLETED upon delivery receipt
        self.client.login(email='procurement@itc-agri.in', password='Password123!')
        self.client.post(reverse('contracts:update_status', kwargs={'pk': contract.pk}), {
            'status': Contract.Status.COMPLETED,
            'reason': 'Delivered and passed quality moisture testing.'
        })
        contract.refresh_from_db()
        self.assertEqual(contract.status, Contract.Status.COMPLETED)

    def test_unauthorized_access_and_illegal_status_jump(self):
        """Security: Strangers cannot view contract, and illegal status transitions are rejected."""
        contract = Contract.objects.create(
            crop_listing=self.crop,
            farmer=self.farmer,
            buyer=self.buyer,
            title='Private Agreement',
            quantity=Decimal('50.00'),
            unit=CropListing.Unit.QUINTAL,
            price_per_unit=Decimal('3800.00'),
            delivery_date=date.today() + timedelta(days=15),
            delivery_address='Ludhiana Hub',
            status=Contract.Status.PENDING_FARMER
        )

        # Stranger attempts to view contract -> redirected with error
        self.client.login(email='stranger@agrisure.in', password='Password123!')
        response = self.client.get(reverse('contracts:detail', kwargs={'pk': contract.pk}))
        self.assertEqual(response.status_code, 302)

        # Illegal status transition: jump directly from PENDING_FARMER to COMPLETED
        with self.assertRaises(ValueError):
            ContractService.transition_status(contract.id, self.buyer, Contract.Status.COMPLETED)

    # -------------------------------------------------------------------------
    # 6. Farmer-Buyer Messaging System (Prompt 3 Section 7)
    # -------------------------------------------------------------------------
    def test_messaging_participant_isolation_and_attachment_validation(self):
        """Test messaging: communication between contract participants, attachment size & type validation, and stranger blocking."""
        contract = Contract.objects.create(
            crop_listing=self.crop,
            farmer=self.farmer,
            buyer=self.buyer,
            title='Contract for Basmati',
            quantity=Decimal('50.00'),
            unit=CropListing.Unit.QUINTAL,
            price_per_unit=Decimal('3800.00'),
            delivery_date=date.today() + timedelta(days=15),
            delivery_address='Ludhiana Hub'
        )

        # Buyer starts conversation
        conv = MessagingService.get_or_create_conversation(self.buyer, self.farmer, contract=contract)
        
        # Buyer sends valid message with PDF attachment
        self.client.login(email='procurement@itc-agri.in', password='Password123!')
        valid_pdf = SimpleUploadedFile("spec_sheet.pdf", b"%PDF-1.4 test content", content_type="application/pdf")
        
        response = self.client.post(reverse('messaging:conversation', kwargs={'pk': conv.pk}), {
            'content': 'Please review the quality specifications document attached.',
            'attachment': valid_pdf
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(conv.messages.count(), 1)
        msg = conv.messages.first()
        self.assertTrue(bool(msg.attachment))
        self.assertFalse(msg.is_read)

        # Stranger attempts to access conversation -> must raise 403 Forbidden
        self.client.login(email='stranger@agrisure.in', password='Password123!')
        response = self.client.get(reverse('messaging:conversation', kwargs={'pk': conv.pk}))
        self.assertEqual(response.status_code, 403)

        # Farmer logs in and reads message -> marks as read
        self.client.login(email='ramesh.farmer@agrisure.in', password='Password123!')
        self.client.get(reverse('messaging:conversation', kwargs={'pk': conv.pk}))
        msg.refresh_from_db()
        self.assertTrue(msg.is_read)
