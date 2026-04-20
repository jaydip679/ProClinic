# Ensure Django uses BillingConfig (which registers signals in ready())
# even when INSTALLED_APPS lists 'billing' as a plain string.
default_app_config = 'billing.apps.BillingConfig'
