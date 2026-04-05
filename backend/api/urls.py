from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from patients.views import PatientViewSet
from .views import (
    AppointmentViewSet, 
    PrescriptionViewSet, 
    InvoiceViewSet, 
    PublicationViewSet
)

router = DefaultRouter()
router.register(r'patients', PatientViewSet)
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'prescriptions', PrescriptionViewSet, basename='prescription')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'publications', PublicationViewSet, basename='publication')

urlpatterns = [
    path('', include(router.urls)),
    # JWT Auth Endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Patient-facing endpoints
    path('patient/', include('api.patient_urls')),
]