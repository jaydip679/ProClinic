ProClinic UI Kit + Prototype Package

Contents:
- png/: High-resolution screen boards (desktop/tablet/mobile)
- design-system.css: tokenized component styling
- prototype.js: interactive flow logic
- proclinic-icons.svg: icon sprite
- design_system.html: component library + interactive prototype page
- prescription_a4.html / invoice_a4.html: printable templates
- permission_error.html: restricted access screen
- proclinic_design_handoff.md: implementation + token + API handoff notes

Open in app:
1) Start Django server
2) Visit /design-system/ for component library + clickable prototype
3) Visit /design-system/prescription-a4/ and /design-system/invoice-a4/ for print templates

Prototype flow:
Login -> Role dashboard -> Booking conflict -> Doctor prescription -> Invoice -> Payment
