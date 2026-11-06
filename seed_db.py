#!/usr/bin/env python3
"""
AgriSure Database Seeder
Populates realistic development seed data for local testing and demonstration.
"""
import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agrisure.settings')
django.setup()

from apps.accounts.models import User
from apps.farmers.models import FarmerProfile
from apps.buyers.models import BuyerProfile, SavedCrop
from apps.crops.models import CropCategory, CropListing
from apps.contracts.models import Contract, ContractHistory
from apps.contracts.services import ContractService
from apps.negotiations.models import Negotiation, Offer
from apps.payments.models import Payment
from apps.deliveries.models import Delivery
from apps.notifications.models import Notification
from apps.reviews.models import Review
from apps.payments.models import PayoutRecord, PaymentRefund
from apps.disputes.models import Dispute, DisputeMessage
from apps.deliveries.models import DeliveryUpdate
from apps.backoffice.models import AdminAuditLog, ReportedListing, PlatformSetting

print("Clearing previous seed data...")
AdminAuditLog.objects.all().delete()
ReportedListing.objects.all().delete()
DisputeMessage.objects.all().delete()
Dispute.objects.all().delete()
PayoutRecord.objects.all().delete()
PaymentRefund.objects.all().delete()
Review.objects.all().delete()
DeliveryUpdate.objects.all().delete()
Delivery.objects.all().delete()
Payment.objects.all().delete()
Offer.objects.all().delete()
Negotiation.objects.all().delete()
ContractHistory.objects.all().delete()
Contract.objects.all().delete()
SavedCrop.objects.all().delete()
CropListing.objects.all().delete()
CropCategory.objects.all().delete()
FarmerProfile.objects.all().delete()
BuyerProfile.objects.all().delete()
Notification.objects.all().delete()
User.objects.all().delete()

print("Creating Administrative User...")
admin_user = User.objects.create_superuser(
    email='admin@agrisure.in',
    password='AdminPassword123!',
    first_name='AgriSure',
    last_name='Admin',
    phone='+919876500000'
)

print("Creating Crop Categories...")
cat_grains = CropCategory.objects.create(name='Grains & Cereals', slug='grains-cereals', icon='wheat', description='Paddy, Wheat, Maize, Barley, Millets')
cat_pulses = CropCategory.objects.create(name='Pulses & Lentils', slug='pulses-lentils', icon='sprout', description='Chickpeas, Pigeon Pea, Black Gram, Green Gram')
cat_spices = CropCategory.objects.create(name='Spices & Condiments', slug='spices', icon='flame', description='Red Chilli, Turmeric, Coriander, Cumin, Cardamom')
cat_oilseeds = CropCategory.objects.create(name='Oilseeds', slug='oilseeds', icon='droplet', description='Soybean, Mustard, Groundnut, Sunflower')
cat_fibers = CropCategory.objects.create(name='Cotton & Fibers', slug='cotton-fibers', icon='feather', description='Medium & Long Staple Raw Cotton')
cat_horticulture = CropCategory.objects.create(name='Horticulture', slug='horticulture', icon='apple', description='Fresh Fruits and Export Quality Vegetables')

print("Creating Farmers...")
# Farmer 1: Ramesh Kumar (Punjab)
farmer1 = User.objects.create_user(
    email='ramesh.farmer@agrisure.in',
    password='FarmerPassword123!',
    first_name='Ramesh',
    last_name='Kumar',
    role=User.Role.FARMER,
    phone='+919812345678',
    email_verified=True,
    profile_completed=True
)
FarmerProfile.objects.create(
    user=farmer1,
    farm_name='Kisan Green Acres Farm',
    farm_size=Decimal('25.5'),
    village='Tarn Taran',
    district='Amritsar',
    state='Punjab',
    pincode='143001',
    latitude=Decimal('31.634000'),
    longitude=Decimal('74.872300'),
    farming_experience_years=18,
    farming_methods='Organic Certified, Precision Drip Irrigation',
    irrigation_facilities='Deep Tube Well & Solar Powered Drip',
    organic_certified=True,
    bio='Third-generation paddy and durum wheat cultivators specializing in pesticide-free export-grade Basmati crops.',
    bank_account_number='384729104859',
    bank_name='State Bank of India',
    ifsc_code='SBIN0001234',
    verification_status=FarmerProfile.VerificationStatus.VERIFIED,
    is_verified=True
)

# Farmer 2: Suresh Patel (Gujarat)
farmer2 = User.objects.create_user(
    email='suresh.patel@agrisure.in',
    password='FarmerPassword123!',
    first_name='Suresh',
    last_name='Patel',
    role=User.Role.FARMER,
    phone='+919823456789',
    email_verified=True,
    profile_completed=True
)
FarmerProfile.objects.create(
    user=farmer2,
    farm_name='Patel Agritech Estates',
    farm_size=Decimal('42.0'),
    village='Gondal',
    district='Rajkot',
    state='Gujarat',
    pincode='360311',
    latitude=Decimal('21.961900'),
    longitude=Decimal('70.793700'),
    farming_experience_years=22,
    farming_methods='Natural Zero-Budget Farming (ZBNF)',
    irrigation_facilities='Narmada Canal Irrigation & Sprinklers',
    organic_certified=False,
    bio='Large-scale producer of high-oil groundnut and long-staple Shankar-6 raw cotton.',
    bank_account_number='982347109283',
    bank_name='Bank of Baroda',
    ifsc_code='BARB0GONDAL',
    verification_status=FarmerProfile.VerificationStatus.VERIFIED,
    is_verified=True
)

print("Creating Institutional Buyers...")
# Buyer 1: ITC Agri Business
buyer1 = User.objects.create_user(
    email='procurement@itc-agri.in',
    password='BuyerPassword123!',
    first_name='Anand',
    last_name='Verma',
    role=User.Role.BUYER,
    phone='+919876543210',
    email_verified=True,
    profile_completed=True
)
BuyerProfile.objects.create(
    user=buyer1,
    company_name='ITC Agri Business Division',
    contact_person='Anand Verma (VP Procurement)',
    business_type=BuyerProfile.BusinessType.PROCESSOR,
    gstin='07AAACI1681G1Z0',
    pan_number='AAACI1681G',
    business_address='ITC Centre, 37 J.L. Nehru Road',
    city='New Delhi',
    district='Central Delhi',
    state='Delhi',
    pincode='110001',
    delivery_address='ITC Agri Mega Warehouse, Kundli Logistics Hub, Sonepat, Haryana 131028',
    annual_procurement_budget=Decimal('250000000.00'),
    preferred_crops='Basmati Paddy, Sharbati Wheat, Mustard, Soybean',
    verification_status=BuyerProfile.VerificationStatus.VERIFIED,
    is_verified=True
)

# Buyer 2: Nature Bio-Foods Ltd (Organic Exporter)
buyer2 = User.objects.create_user(
    email='sourcing@naturebiofoods.in',
    password='BuyerPassword123!',
    first_name='Priya',
    last_name='Nair',
    role=User.Role.BUYER,
    phone='+919834567890',
    email_verified=True,
    profile_completed=True
)
BuyerProfile.objects.create(
    user=buyer2,
    company_name='Nature Bio-Foods Limited',
    contact_person='Priya Nair (Senior Sourcing Manager)',
    business_type=BuyerProfile.BusinessType.EXPORTER,
    gstin='06AABCN4421H1ZM',
    pan_number='AABCN4421H',
    city='Gurugram',
    state='Haryana',
    delivery_address='Nature Bio Cold Storage & Export Warehouse, Sonipat, Haryana',
    annual_procurement_budget=Decimal('120000000.00'),
    preferred_crops='Organic Basmati, Organic Soybean, Organic Pulses',
    verification_status=BuyerProfile.VerificationStatus.VERIFIED,
    is_verified=True
)

print("Creating Crop Listings...")
crop1 = CropListing.objects.create(
    farmer=farmer1,
    category=cat_grains,
    title='Organic Basmati Paddy (Pusa 1121 Extra Long)',
    variety='Pusa 1121',
    description='Single-origin premium long-grain Basmati paddy grown using Jaivik organic standards in the fertile Amritsar belt. Moisture content under 12%, grain elongation ratio 2.5x upon cooking.',
    quantity_available=Decimal('250.00'),
    quantity_remaining=Decimal('150.00'),
    unit=CropListing.Unit.QUINTAL,
    price_per_unit=Decimal('3850.00'),
    minimum_acceptable_price=Decimal('3600.00'),
    minimum_order_quantity=Decimal('20.00'),
    quality_grade=CropListing.QualityGrade.PREMIUM,
    farming_type=CropListing.FarmingType.ORGANIC,
    expected_harvest_date=date.today() + timedelta(days=25),
    available_from=date.today() + timedelta(days=20),
    available_until=date.today() + timedelta(days=90),
    village='Tarn Taran',
    district='Amritsar',
    state='Punjab',
    pincode='143001',
    latitude=Decimal('31.634000'),
    longitude=Decimal('74.872300'),
    delivery_location_availability='Farm Gate pickup or dispatched to NCR Warehouses',
    delivery_conditions='Jute gunny bags of 50kg each. Moisture testing certified prior to loading.',
    status=CropListing.Status.ACTIVE
)

crop2 = CropListing.objects.create(
    farmer=farmer1,
    category=cat_grains,
    title='Golden Sharbati Wheat (Sehore Variety)',
    variety='Sharbati C-306',
    description='Heirloom golden-grain Sharbati wheat with high gluten strength and natural sweetness. Renowned for soft chapatis with zero chemical pesticide residues.',
    quantity_available=Decimal('400.00'),
    quantity_remaining=Decimal('400.00'),
    unit=CropListing.Unit.QUINTAL,
    price_per_unit=Decimal('2950.00'),
    minimum_acceptable_price=Decimal('2800.00'),
    minimum_order_quantity=Decimal('50.00'),
    quality_grade=CropListing.QualityGrade.GRADE_A,
    farming_type=CropListing.FarmingType.CONVENTIONAL,
    expected_harvest_date=date.today() + timedelta(days=45),
    district='Amritsar',
    state='Punjab',
    status=CropListing.Status.ACTIVE
)

crop3 = CropListing.objects.create(
    farmer=farmer2,
    category=cat_oilseeds,
    title='High-Oil Saurashtra Groundnut (GG-20 Variety)',
    variety='GG-20 Bold Pods',
    description='Saurashtra bold pod groundnuts with 48%+ oil extraction ratio. Pods sun-dried to optimal 7% moisture, perfect for cold-pressed oil extraction and peanut butter processing.',
    quantity_available=Decimal('300.00'),
    quantity_remaining=Decimal('300.00'),
    unit=CropListing.Unit.QUINTAL,
    price_per_unit=Decimal('6200.00'),
    minimum_acceptable_price=Decimal('5900.00'),
    minimum_order_quantity=Decimal('25.00'),
    quality_grade=CropListing.QualityGrade.PREMIUM,
    farming_type=CropListing.FarmingType.NATURAL,
    expected_harvest_date=date.today() + timedelta(days=15),
    district='Rajkot',
    state='Gujarat',
    status=CropListing.Status.ACTIVE
)

crop4 = CropListing.objects.create(
    farmer=farmer2,
    category=cat_fibers,
    title='Shankar-6 Raw Cotton Bales (29mm+ Staple)',
    variety='Shankar-6',
    description='Premium Shankar-6 raw seed cotton with 29mm+ staple length, 3.8 to 4.2 micronaire value, and low trash content below 3%. Direct from Gujarat ginning facilities.',
    quantity_available=Decimal('150.00'),
    quantity_remaining=Decimal('150.00'),
    unit=CropListing.Unit.QUINTAL,
    price_per_unit=Decimal('7400.00'),
    minimum_acceptable_price=Decimal('7100.00'),
    minimum_order_quantity=Decimal('10.00'),
    quality_grade=CropListing.QualityGrade.GRADE_A,
    farming_type=CropListing.FarmingType.CONVENTIONAL,
    expected_harvest_date=date.today() + timedelta(days=35),
    district='Rajkot',
    state='Gujarat',
    status=CropListing.Status.ACTIVE
)

print("Creating Active Binding Contract...")
contract1 = Contract.objects.create(
    crop_listing=crop1,
    farmer=farmer1,
    buyer=buyer1,
    title='Supply Agreement for 100 Quintals Pusa 1121 Basmati',
    quantity=Decimal('100.00'),
    unit='quintal',
    price_per_unit=Decimal('3850.00'),
    total_amount=Decimal('385000.00'),
    advance_payment_percentage=Decimal('20.00'),
    advance_amount=Decimal('77000.00'),
    delivery_date=date.today() + timedelta(days=30),
    delivery_address=buyer1.buyer_profile.delivery_address,
    quality_specifications='Moisture <= 12%, Foreign Matter < 1%, Broken grains < 2%',
    terms_and_conditions='Quality inspection at buyer hub within 24 hours of unloading. 80% balance payment released immediately after QA clearance.',
    status=Contract.Status.ACTIVE,
    farmer_accepted=True,
    farmer_accepted_at=timezone.now() - timedelta(days=3),
    buyer_accepted=True,
    buyer_accepted_at=timezone.now() - timedelta(days=3)
)
ContractHistory.objects.create(
    contract=contract1,
    performed_by=buyer1,
    from_status='DRAFT',
    to_status=Contract.Status.ACTIVE,
    comment='Contract accepted and signed by both parties. Legally binding agreement active.'
)
# Generate PDF for this contract
ContractService.generate_pdf(contract1)

print("Creating Advance Escrow Payment for Contract...")
payment1 = Payment.objects.create(
    contract=contract1,
    payer=buyer1,
    payee=farmer1,
    amount=Decimal('77000.00'),
    payment_type=Payment.PaymentType.ADVANCE,
    status=Payment.Status.COMPLETED,
    razorpay_order_id='order_AGR_seed_001',
    razorpay_payment_id='pay_AGR_seed_9871',
    notes='20% advance security deposit held in AgriSure Escrow.',
    paid_at=timezone.now() - timedelta(days=2)
)

print("Creating Delivery Tracking...")
delivery1 = Delivery.objects.create(
    contract=contract1,
    quantity_shipped=Decimal('100.00'),
    carrier_name='Punjab Roadlines (Truck PB-02-CX-4421)',
    driver_phone='+919877123456',
    shipping_address=contract1.delivery_address,
    status=Delivery.Status.SHIPPED,
    estimated_delivery_date=date.today() + timedelta(days=2),
    delivery_notes='Dispatched in 200 sealed 50kg polypropylene bags.'
)

print("Creating Negotiation Thread...")
neg1 = Negotiation.objects.create(
    crop_listing=crop3,
    farmer=farmer2,
    buyer=buyer2,
    status=Negotiation.Status.OPEN
)
Offer.objects.create(
    negotiation=neg1,
    submitted_by=buyer2,
    offer_type=Offer.OfferType.INITIAL,
    price_per_unit=Decimal('5950.00'),
    quantity=Decimal('150.00'),
    proposed_delivery_date=date.today() + timedelta(days=20),
    conditions='Pre-shipment aflatoxin testing report required.',
    message='We can lift 150 quintals in a single batch if price is ₹5,950/quintal.',
    status=Offer.Status.COUNTERED
)
Offer.objects.create(
    negotiation=neg1,
    submitted_by=farmer2,
    offer_type=Offer.OfferType.COUNTER,
    price_per_unit=Decimal('6050.00'),
    quantity=Decimal('150.00'),
    proposed_delivery_date=date.today() + timedelta(days=20),
    conditions='Pre-shipment aflatoxin testing included.',
    message='Can accommodate at ₹6,050/quintal including direct gate loading.',
    status=Offer.Status.PENDING
)

print("Creating Wishlist Items & Notifications...")
SavedCrop.objects.create(buyer=buyer1, crop_listing=crop3)
SavedCrop.objects.create(buyer=buyer2, crop_listing=crop1)

Notification.objects.create(
    recipient=farmer1,
    notification_type='PAYMENT',
    title='Advance Payment Received!',
    message='₹77,000.00 has been credited to your AgriSure escrow ledger for Contract #' + contract1.contract_number,
    link=f'/contracts/{contract1.id}/'
)
Notification.objects.create(
    recipient=buyer1,
    notification_type='DELIVERY',
    title='Shipment Dispatched',
    message='Farmer Ramesh Kumar has dispatched 100 quintals via Punjab Roadlines.',
    link=f'/deliveries/{delivery1.id}/'
)

print("Creating Reputation Review & Platform Settings...")
from apps.backoffice.models import PlatformSetting, ReportedListing
from apps.disputes.models import Dispute, DisputeMessage
from apps.payments.models import PayoutRecord

PlatformSetting.get_settings()

PayoutRecord.objects.create(
    contract=contract1,
    farmer=farmer1,
    amount=Decimal('77000.00'),
    status=PayoutRecord.Status.PENDING,
    provider='Razorpay Route / Bank Direct Settlement',
    notes=f'Pending bank clearance for {payment1.transaction_id}'
)

# Seed an active dispute for testing
dispute1 = Dispute.objects.create(
    contract=contract1,
    raised_by=buyer1,
    against_party=farmer1,
    category=Dispute.Category.QUALITY,
    title='Moisture Variance in Pre-Dispatch Sample',
    description='Pre-shipment moisture reading was measured at 14.8%, which slightly exceeds the contractual 12% target limit.',
    status=Dispute.Status.OPEN
)

DisputeMessage.objects.create(
    dispute=dispute1,
    sender=buyer1,
    message='We request an independent testing laboratory certificate prior to unsealing the transit bags.'
)

Review.objects.create(
    contract=contract1,
    reviewer=buyer1,
    reviewee=farmer1,
    rating=5,
    quality_rating=5,
    timeliness_rating=5,
    communication_rating=5,
    title='Superb Basmati Crop Quality & Timely Delivery',
    comment='Ramesh Kumar provided outstanding organic paddy with zero foreign matter. Accurate weighing and seamless documentation.'
)

print("\n" + "="*60)
print("AGRISURE DATABASE SEEDING COMPLETED SUCCESSFULLY!")
print("="*60)
print("Demo Credentials:")
print("1. Admin:   admin@agrisure.in        / AdminPassword123!")
print("2. Farmer:  ramesh.farmer@agrisure.in / FarmerPassword123!")
print("3. Buyer:   procurement@itc-agri.in   / BuyerPassword123!")
print("="*60)
