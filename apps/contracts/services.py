import io
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from .models import Contract, ContractAcceptance, ContractHistory
from apps.crops.models import CropListing
from apps.notifications.services import NotificationService

class NumberedCanvas:
    """Helper to draw header, footer, and page numbers on ReportLab PDFs."""
    def __init__(self, *args, **kwargs):
        pass

class ContractService:
    # Valid status transitions map
    VALID_TRANSITIONS = {
        Contract.Status.DRAFT: [
            Contract.Status.PENDING_FARMER,
            Contract.Status.PENDING_BUYER,
            Contract.Status.CANCELLED
        ],
        Contract.Status.PENDING_FARMER: [
            Contract.Status.ACTIVE,
            Contract.Status.PENDING_BUYER,
            Contract.Status.CANCELLED,
            Contract.Status.DISPUTED
        ],
        Contract.Status.PENDING_BUYER: [
            Contract.Status.ACTIVE,
            Contract.Status.PENDING_FARMER,
            Contract.Status.CANCELLED,
            Contract.Status.DISPUTED
        ],
        Contract.Status.ACTIVE: [
            Contract.Status.PRODUCTION_IN_PROGRESS,
            Contract.Status.READY_FOR_DELIVERY,
            Contract.Status.CANCELLED,
            Contract.Status.DISPUTED
        ],
        Contract.Status.PRODUCTION_IN_PROGRESS: [
            Contract.Status.READY_FOR_DELIVERY,
            Contract.Status.PARTIALLY_DELIVERED,
            Contract.Status.DISPUTED,
            Contract.Status.CANCELLED
        ],
        Contract.Status.READY_FOR_DELIVERY: [
            Contract.Status.PARTIALLY_DELIVERED,
            Contract.Status.DELIVERED,
            Contract.Status.COMPLETED,
            Contract.Status.DISPUTED
        ],
        Contract.Status.PARTIALLY_DELIVERED: [
            Contract.Status.DELIVERED,
            Contract.Status.DISPUTED
        ],
        Contract.Status.DELIVERED: [
            Contract.Status.COMPLETED,
            Contract.Status.DISPUTED
        ],
        Contract.Status.DISPUTED: [
            Contract.Status.ACTIVE,
            Contract.Status.PRODUCTION_IN_PROGRESS,
            Contract.Status.COMPLETED,
            Contract.Status.CANCELLED
        ],
        Contract.Status.COMPLETED: [],
        Contract.Status.CANCELLED: []
    }

    @staticmethod
    def generate_pdf(contract):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36, leftMargin=36,
            topMargin=36, bottomMargin=40
        )
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ContractTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=colors.HexColor('#064e3b'),
            alignment=1,
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            'ContractSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor('#4b5563'),
            alignment=1,
            spaceAfter=14,
        )
        h2_style = ParagraphStyle(
            'H2',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=colors.HexColor('#065f46'),
            spaceBefore=10,
            spaceAfter=4,
        )
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor('#1f2937'),
        )
        body_bold = ParagraphStyle(
            'BodyBold',
            parent=body_style,
            fontName='Helvetica-Bold',
        )
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor('#6b7280'),
            alignment=1,
        )

        elements = []
        elements.append(Paragraph("AGRISURE DIRECT CONTRACT FARMING AGREEMENT", title_style))
        elements.append(Paragraph(
            f"Agreement Ref: <b>{contract.contract_number}</b> &nbsp;|&nbsp; Version: <b>v{contract.version}</b> &nbsp;|&nbsp; Date: <b>{contract.created_at.strftime('%d %B %Y')}</b>",
            subtitle_style
        ))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#059669'), spaceBefore=0, spaceAfter=10))

        # Parties Table
        farmer_profile = getattr(contract.farmer, 'farmer_profile', None)
        buyer_profile = getattr(contract.buyer, 'buyer_profile', None)

        parties_data = [
            [
                Paragraph("<b>PRODUCER (FARMER) DETAILS:</b>", body_bold),
                Paragraph("<b>PURCHASER (BUYER) DETAILS:</b>", body_bold)
            ],
            [
                Paragraph(
                    f"<b>Legal Name:</b> {contract.farmer.get_full_name()}<br/>"
                    f"<b>Farm Entity:</b> {farmer_profile.farm_name if farmer_profile and farmer_profile.farm_name else 'Agricultural Producer'}<br/>"
                    f"<b>Location:</b> {contract.crop_listing.district}, {contract.crop_listing.state}<br/>"
                    f"<b>Contact:</b> {contract.farmer.phone or 'Not provided'} | {contract.farmer.email}<br/>"
                    f"<b>KYC Status:</b> {'Verified Producer' if farmer_profile and farmer_profile.is_verified else 'Registered Farmer'}",
                    body_style
                ),
                Paragraph(
                    f"<b>Company Name:</b> {buyer_profile.company_name if buyer_profile and buyer_profile.company_name else contract.buyer.get_full_name()}<br/>"
                    f"<b>Business Type:</b> {buyer_profile.get_business_type_display() if buyer_profile else 'Corporate Procurement'}<br/>"
                    f"<b>GSTIN:</b> {buyer_profile.gstin if buyer_profile and buyer_profile.gstin else 'N/A'} | PAN: {buyer_profile.pan_number if buyer_profile and buyer_profile.pan_number else 'N/A'}<br/>"
                    f"<b>Representative:</b> {contract.buyer.get_full_name()} ({contract.buyer.email})<br/>"
                    f"<b>Warehouse:</b> {contract.delivery_address[:60] if contract.delivery_address else 'Primary Facility'}",
                    body_style
                )
            ]
        ]
        t_parties = Table(parties_data, colWidths=[270, 270])
        t_parties.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(t_parties)
        elements.append(Spacer(1, 10))

        # 1. Produce & Commercial Specifications
        elements.append(Paragraph("1. PRODUCE & COMMERCIAL SPECIFICATIONS", h2_style))
        comm_data = [
            [Paragraph("<b>Crop & Variety</b>", body_style), Paragraph(f"{contract.crop_listing.title} ({contract.crop_listing.variety or 'Standard'})", body_style)],
            [Paragraph("<b>Farming Practice</b>", body_style), Paragraph(contract.crop_listing.get_farming_type_display(), body_style)],
            [Paragraph("<b>Contracted Quantity</b>", body_style), Paragraph(f"<b>{contract.quantity:,.2f} {contract.unit}</b>", body_style)],
            [Paragraph("<b>Price Per Unit</b>", body_style), Paragraph(f"₹ {contract.price_per_unit:,.2f} per {contract.unit}", body_style)],
            [Paragraph("<b>Total Contract Value</b>", body_style), Paragraph(f"<b>₹ {contract.total_amount:,.2f}</b> (INR)", body_style)],
            [Paragraph("<b>Advance Escrow Deposit</b>", body_style), Paragraph(f"{contract.advance_payment_percentage}% (₹ {contract.advance_amount:,.2f})", body_style)],
            [Paragraph("<b>Target Delivery Date</b>", body_style), Paragraph(contract.delivery_date.strftime('%d %B %Y'), body_style)],
            [Paragraph("<b>Delivery Location</b>", body_style), Paragraph(contract.delivery_address, body_style)],
            [Paragraph("<b>Required Quality Grade</b>", body_style), Paragraph(contract.get_required_quality_grade_display(), body_style)],
        ]
        t_comm = Table(comm_data, colWidths=[170, 370])
        t_comm.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0,0), (-1,-1), 4.5),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f1f5f9')),
        ]))
        elements.append(t_comm)
        elements.append(Spacer(1, 10))

        # 2. Quality & Payment Terms
        elements.append(Paragraph("2. QUALITY SPECIFICATIONS & PAYMENT CONDITIONS", h2_style))
        terms_text = (
            f"<b>Quality Parameters:</b> {contract.quality_specifications or 'Produce must meet Fair Average Quality (FAQ) standards with prescribed moisture thresholds.'}<br/>"
            f"<b>Payment Terms:</b> {contract.payment_terms or 'Advance deposit placed into secured escrow upon contract execution; remaining balance disbursed within 48 hours of joint quality weighment.'}<br/>"
            f"<b>Harvest & Delivery Logistics:</b> {contract.harvest_schedule or 'Harvest window aligned with natural crop maturity; transport coordinated per agreed dispatch condition.'}"
        )
        if contract.additional_conditions:
            terms_text += f"<br/><b>Additional Covenants:</b> {contract.additional_conditions}"
        elements.append(Paragraph(terms_text, body_style))
        elements.append(Spacer(1, 8))

        # 3. Mutual Obligations & Dispute Resolution
        elements.append(Paragraph("3. STATUTORY RESPONSIBILITIES & DISPUTE RESOLUTION", h2_style))
        legal_text = (
            "<b>Farmer Obligations:</b> The Producer agrees to cultivate, nurture, harvest, and package the agreed crop adhering to good agronomic practices, ensuring timely dispatch to the designated receiving facility.<br/>"
            "<b>Buyer Obligations:</b> The Purchaser agrees to deposit required escrow advances promptly, inspect consignments without unreasonable delay, and release final settlement funds upon verification.<br/>"
            "<b>Cancellation Policy:</b> Unilateral termination after bilateral acceptance is prohibited except under certified force majeure events.<br/>"
            "<b>Dispute Settlement:</b> Disputes shall be mediated by the AgriSure Conciliation Board in accordance with the Model Contract Farming Act framework."
        )
        elements.append(Paragraph(legal_text, body_style))
        elements.append(Spacer(1, 12))

        # 4. Digital Acceptance Box
        elements.append(Paragraph("4. PLATFORM-RECORDED DIGITAL MUTUAL ACCEPTANCE", h2_style))
        sig_data = [
            [
                Paragraph(
                    f"<b>FARMER DIGITAL ACCEPTANCE:</b><br/>"
                    f"Status: <b>{'ACCEPTED' if contract.farmer_accepted else 'PENDING'}</b><br/>"
                    f"Accepted Version: {f'v{contract.farmer_accepted_version}' if contract.farmer_accepted_version else 'N/A'}<br/>"
                    f"Timestamp: {contract.farmer_accepted_at.strftime('%Y-%m-%d %H:%M:%S UTC') if contract.farmer_accepted_at else 'Awaiting Acceptance'}<br/>"
                    f"Signatory: {contract.farmer.get_full_name()}",
                    body_style
                ),
                Paragraph(
                    f"<b>BUYER DIGITAL ACCEPTANCE:</b><br/>"
                    f"Status: <b>{'ACCEPTED' if contract.buyer_accepted else 'PENDING'}</b><br/>"
                    f"Accepted Version: {f'v{contract.buyer_accepted_version}' if contract.buyer_accepted_version else 'N/A'}<br/>"
                    f"Timestamp: {contract.buyer_accepted_at.strftime('%Y-%m-%d %H:%M:%S UTC') if contract.buyer_accepted_at else 'Awaiting Acceptance'}<br/>"
                    f"Signatory: {contract.buyer.get_full_name()}",
                    body_style
                )
            ]
        ]
        t_sig = Table(sig_data, colWidths=[270, 270])
        t_sig.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ecfdf5')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#10b981')),
            ('PADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        elements.append(t_sig)
        elements.append(Spacer(1, 10))

        # Disclaimer
        elements.append(Paragraph(
            "AgriSure Platform Compliance Notice: This contract is digitally recorded and timestamped under the Information Technology Act. "
            "It records platform-mediated mutual electronic agreement between Producer and Purchaser.",
            disclaimer_style
        ))

        doc.build(elements)
        buffer.seek(0)
        
        file_name = f"contract_{contract.contract_number}_v{contract.version}.pdf"
        contract.contract_pdf.save(file_name, ContentFile(buffer.getvalue()), save=False)
        contract.save()
        return contract.contract_pdf

    @staticmethod
    def accept_contract(contract_id, user, ip_address=None, user_agent=''):
        with transaction.atomic():
            contract = Contract.objects.select_for_update().get(id=contract_id)
            
            if contract.status in [Contract.Status.CANCELLED, Contract.Status.COMPLETED]:
                raise ValueError("This contract is closed and cannot be accepted.")
                
            if user != contract.farmer and user != contract.buyer:
                raise ValueError("You are not an authorized party to this contract.")

            now = timezone.now()
            
            # Record explicit acceptance in ContractAcceptance table
            ContractAcceptance.objects.create(
                contract=contract,
                user=user,
                version=contract.version,
                ip_address=ip_address,
                user_agent=user_agent[:255] if user_agent else '',
                disclaimer_acknowledged=True
            )

            if user == contract.farmer:
                contract.farmer_accepted = True
                contract.farmer_accepted_at = now
                contract.farmer_accepted_version = contract.version
                party_label = "Farmer"
            else:
                contract.buyer_accepted = True
                contract.buyer_accepted_at = now
                contract.buyer_accepted_version = contract.version
                party_label = "Buyer"

            # Check if BOTH have accepted the CURRENT version
            both_accepted = (
                contract.farmer_accepted and
                contract.buyer_accepted and
                contract.farmer_accepted_version == contract.version and
                contract.buyer_accepted_version == contract.version
            )

            if both_accepted:
                contract.status = Contract.Status.ACTIVE
                comment = f"Both parties accepted version v{contract.version}! Contract is now ACTIVE and binding."
                
                # Deduct contracted quantity from crop listing stock
                crop = contract.crop_listing
                if crop.quantity_remaining >= contract.quantity:
                    crop.quantity_remaining -= contract.quantity
                    if crop.quantity_remaining == 0:
                        crop.status = CropListing.Status.UNDER_CONTRACT
                    crop.save(update_fields=['quantity_remaining', 'status'])

                # Regenerate updated PDF with mutual timestamps
                ContractService.generate_pdf(contract)
                
                # Notifications
                NotificationService.send(
                    recipient=contract.farmer,
                    notification_type='CONTRACT',
                    title=f'Contract #{contract.contract_number} Activated!',
                    message=f'Contract #{contract.contract_number} for {contract.crop_listing.title} is now active.',
                    link=f'/contracts/{contract.id}/'
                )
                NotificationService.send(
                    recipient=contract.buyer,
                    notification_type='CONTRACT',
                    title=f'Contract #{contract.contract_number} Activated!',
                    message=f'Contract #{contract.contract_number} for {contract.crop_listing.title} is now active.',
                    link=f'/contracts/{contract.id}/'
                )
            else:
                if user == contract.farmer:
                    contract.status = Contract.Status.PENDING_BUYER
                else:
                    contract.status = Contract.Status.PENDING_FARMER
                comment = f"{party_label} {user.get_full_name()} accepted version v{contract.version}. Awaiting counterpart acceptance."
                
                other_party = contract.buyer if user == contract.farmer else contract.farmer
                NotificationService.send(
                    recipient=other_party,
                    notification_type='CONTRACT',
                    title=f'Contract Acceptance Awaiting Your Approval',
                    message=f'{user.get_full_name()} accepted version v{contract.version} of Contract #{contract.contract_number}. Please review and approve.',
                    link=f'/contracts/{contract.id}/'
                )

            contract.save()
            ContractHistory.objects.create(
                contract=contract,
                performed_by=user,
                from_status=contract.status,
                to_status=contract.status,
                comment=comment
            )
            return contract

    @staticmethod
    def propose_amendment(contract_id, user, form_data, amendment_reason=''):
        with transaction.atomic():
            contract = Contract.objects.select_for_update().get(id=contract_id)
            if contract.status in [Contract.Status.COMPLETED, Contract.Status.CANCELLED]:
                raise ValueError("Cannot amend a finalized or cancelled contract.")
                
            if user != contract.farmer and user != contract.buyer:
                raise ValueError("Unauthorized to amend this contract.")

            old_version = contract.version
            contract.version += 1
            now = timezone.now()

            # Apply amended terms
            for field in ['quantity', 'price_per_unit', 'delivery_date', 'delivery_address', 'required_quality_grade', 'quality_specifications', 'payment_terms', 'additional_conditions']:
                if field in form_data and form_data[field] is not None:
                    setattr(contract, field, form_data[field])

            # Reset acceptance flags because version changed
            contract.farmer_accepted = False
            contract.farmer_accepted_at = None
            contract.farmer_accepted_version = None
            contract.buyer_accepted = False
            contract.buyer_accepted_at = None
            contract.buyer_accepted_version = None

            # Proposing party automatically signs the amended version
            if user == contract.farmer:
                contract.farmer_accepted = True
                contract.farmer_accepted_at = now
                contract.farmer_accepted_version = contract.version
                contract.status = Contract.Status.PENDING_BUYER
                target_user = contract.buyer
            else:
                contract.buyer_accepted = True
                contract.buyer_accepted_at = now
                contract.buyer_accepted_version = contract.version
                contract.status = Contract.Status.PENDING_FARMER
                target_user = contract.farmer

            contract.save()
            ContractService.generate_pdf(contract)

            ContractHistory.objects.create(
                contract=contract,
                performed_by=user,
                from_status=contract.status,
                to_status=contract.status,
                comment=f"Contract amendment proposed by {user.get_full_name()} (Version updated v{old_version} -> v{contract.version}). Reason: {amendment_reason}"
            )

            NotificationService.send(
                recipient=target_user,
                notification_type='CONTRACT',
                title=f'Contract Amendment Proposed (v{contract.version})',
                message=f'{user.get_full_name()} proposed an amendment to Contract #{contract.contract_number}. Please review the updated terms.',
                link=f'/contracts/{contract.id}/'
            )
            return contract

    @staticmethod
    def transition_status(contract_id, user, new_status, reason=''):
        with transaction.atomic():
            contract = Contract.objects.select_for_update().get(id=contract_id)
            old_status = contract.status

            if new_status not in dict(Contract.Status.choices):
                raise ValueError(f"Invalid status '{new_status}'.")

            # Check valid transition path
            allowed_next = ContractService.VALID_TRANSITIONS.get(old_status, [])
            if new_status not in allowed_next and not user.is_admin_user:
                raise ValueError(f"Cannot transition contract from {contract.get_status_display()} to {dict(Contract.Status.choices).get(new_status)}.")

            # Role authority checks
            if new_status in [Contract.Status.PRODUCTION_IN_PROGRESS, Contract.Status.READY_FOR_DELIVERY]:
                if user != contract.farmer and not user.is_admin_user:
                    raise ValueError("Only the farmer can mark production or readiness for delivery.")
            elif new_status in [Contract.Status.COMPLETED]:
                if user != contract.buyer and not user.is_admin_user:
                    raise ValueError("Only the buyer or platform admin can mark the contract as completed.")
            elif new_status == Contract.Status.CANCELLED:
                if user != contract.farmer and user != contract.buyer and not user.is_admin_user:
                    raise ValueError("Unauthorized.")
                contract.cancellation_reason = reason

            contract.status = new_status
            contract.save()

            ContractHistory.objects.create(
                contract=contract,
                performed_by=user,
                from_status=old_status,
                to_status=new_status,
                comment=reason or f"Status transitioned to {contract.get_status_display()}"
            )

            other_party = contract.buyer if user == contract.farmer else contract.farmer
            NotificationService.send(
                recipient=other_party,
                notification_type='CONTRACT',
                title=f'Contract #{contract.contract_number}: {contract.get_status_display()}',
                message=f'Contract status updated to {contract.get_status_display()}.',
                link=f'/contracts/{contract.id}/'
            )
            return contract
