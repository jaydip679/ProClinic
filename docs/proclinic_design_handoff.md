# ProClinic UI Design Handoff

## Deliverables
- Component library + tokens: `frontend/static/proclinic/design-system.css`
- Icon set (SVG sprite): `frontend/static/proclinic/icons/proclinic-icons.svg`
- Interactive prototype: `/design-system/` -> `frontend/templates/prototype/design_system.html`
- Prescription A4 template: `/design-system/prescription-a4/` -> `frontend/templates/prototype/prescription_a4.html`
- Invoice A4 template: `/design-system/invoice-a4/` -> `frontend/templates/prototype/invoice_a4.html`
- Friendly permission screen: `/permission-denied/` -> `frontend/templates/prototype/permission_error.html`
- Packaged export ZIP: `deliverables/proclinic_ui_kit_prototype.zip`

## Token set
```css
:root {
  --pc-color-primary: #0CA789;
  --pc-color-primary-strong: #087A66;
  --pc-color-secondary: #2C3E91;
  --pc-color-alert: #FFD166;
  --pc-color-danger: #E23E57;
  --pc-color-bg: #F7F9FB;
  --pc-color-mid: #98A1B3;
  --pc-color-dark: #24323B;

  --pc-space-2: 8px;
  --pc-space-4: 16px;
  --pc-space-5: 24px;
  --pc-space-6: 32px;

  --pc-h1: 32px - 36px;
  --pc-h2: 24px - 28px;
  --pc-h3: 18px - 20px;
  --pc-body: 14px - 16px;
}
```

## Component coverage
- Header, Sidebar (role-aware)
- Buttons: primary / secondary / ghost / destructive
- Inputs, selects, date-time picker, file input
- Tables + status chips + pagination
- Cards and stat tiles
- Badges/chips: Scheduled, Confirmed, Completed, Pending, Paid
- Modal, toast, tooltip, inline error
- Calendar events (confirmed/pending/cancelled color coding)
- Multi-row prescription composer pattern
- A4 prescription and invoice templates

## Priority screen coverage
1. Landing/Login/Role selection
2. Dashboards: Admin, Doctor, Patient (+ role variants for Receptionist, Pharmacist, Accountant)
3. Patient profile + EHR timeline + documents
4. Appointment booking with conflict modal
5. Prescription creator with medicine rows
6. Billing + invoice detail (GST line visible)
7. Research upload + approval
8. Audit logs
9. AI helpdesk modal (MVP)
10. Settings + user profile

## Permissions reflected in UI
- Admin only: create staff accounts and assign roles.
- Receptionist: register patient and book/check-in on patient behalf.
- Doctor: manage availability/unavailability and clinical actions.
- Pharmacist/Admin: edit dispense status.
- Accountant: mark invoice paid + issue receipt.
- Patient: only view/pay own records and invoices.

Restricted actions are hidden by role (`data-roles` in prototype), and restricted URL fallback points to `/permission-denied/`.

## Prototype flows implemented
- Role login -> role dashboard
- Booking conflict logic:
  - `start_time < existing_end && end_time > existing_start`
- Conflict modal includes exact overlaps + alternative slots + override path
- Reception check-in with room assignment toast
- Prescription validation (quantity + severe allergy hard stop)
- Invoice GST calculation (`subtotal * 0.18`) + payment step
- Audit destructive-action modal with mandatory reason
- AI helpdesk canned-response modal

## Accessibility and responsive QA
- Focus-visible styles on interactive controls
- Modal roles: `role="dialog"`, `aria-modal="true"`
- Inline errors use `role="alert"`
- Status chips keep text labels
- Desktop: 1440, Tablet: 768-1024, Mobile: 375

Contrast checks used:
- `#FFFFFF` on `#087A66`: `5.26:1` (Pass)
- `#FFFFFF` on `#2C3E91`: `9.52:1` (Pass)
- `#24323B` on `#F7F9FB`: `12.48:1` (Pass)
- `#0B6E59` on `#DAF7F0`: `5.47:1` (Pass)

## Figma-friendly naming map
- `Button/Primary`
- `Button/Secondary`
- `Button/Ghost`
- `Button/Destructive`
- `Card/Stat`
- `Card/List`
- `Table/Header`
- `Table/Row`
- `Modal/BookingConflict`
- `Modal/AuditConfirm`
- `Chip/Confirmed`
- `Chip/Paid`
- `Calendar/EventConfirmed`
- `Calendar/EventPending`
- `Calendar/EventCancelled`
- `Form/Input`
- `Form/Select`
- `Form/DateTime`
- `Tooltip/Default`

## Sample JSON payloads
```json
{
  "patient": {
    "id": "PAT-920",
    "name": "Nitin Sharma",
    "dob": "1998-08-12",
    "blood_group": "O+",
    "allergies": ["Penicillin"]
  },
  "appointment": {
    "id": "APT-1007",
    "doctor": "Dr. A. Desai",
    "start_time": "2026-02-20T10:30:00Z",
    "end_time": "2026-02-20T11:00:00Z",
    "status": "Confirmed"
  },
  "invoice": {
    "id": "INV-557",
    "items": [
      {"label": "Consultation", "amount": 500},
      {"label": "Medicines", "amount": 800}
    ],
    "gst_percent": 18,
    "gst_amount": 234,
    "total": 1534
  }
}
```

## Endpoint references
- `GET /api/patients/`
- `GET /api/appointments/`
- `POST /appointments/book/`
- `POST /prescriptions/add/`
- `POST /billing/new/`
- `GET /audit/logs/`
- `POST /publications/submit/`
- `GET /design-system/`
- `GET /permission-denied/`
