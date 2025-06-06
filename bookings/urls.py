from django.urls import path
from .views import *
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('classes/', FitnessClassList.as_view(), name='fitness-class-list'),
    path('create/classes/', FitnessClassCreateAdmin.as_view(), name='fitness-class-create-admin'),
    path('book/', BookingCreate.as_view(), name='booking-create'),
    path('bookings/', BookingListByEmail.as_view(), name='booking-list-by-email'),
    path('fitness-classes/', FitnessClassList.as_view(), name='fitness-classes-list'),
]
