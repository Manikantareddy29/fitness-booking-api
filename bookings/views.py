from django.utils import timezone
from django.contrib.auth import authenticate
from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.schemas import AutoSchema
from rest_framework.compat import coreapi, coreschema
from .models import FitnessClass, Booking
from .serializers import FitnessClassSerializer, BookingSerializer
from .permissions import IsSuperUser
from rest_framework import serializers


import logging

logger = logging.getLogger(__name__)

class FitnessClassList(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            try:
                classes = FitnessClass.objects.filter(datetime__gte=timezone.now())
            except Exception as e:
                logger.error(f"Error querying FitnessClass: {str(e)}")
                return Response(
                    {"error": "An error occurred while querying classes."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            try:
                serializer = FitnessClassSerializer(classes, many=True)
            except Exception as e:
                logger.error(f"Error serializing fitness classes: {str(e)}")
                return Response(
                    {"error": "An error occurred while serializing classes."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Unexpected error in FitnessClassList view: {str(e)}")
            return Response(
                {"error": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class FitnessClassCreateAdmin(APIView):
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        try:
            try:
                serializer = FitnessClassSerializer(data=request.data)
            except Exception as e:
                logger.error(f"Error initializing serializer: {str(e)}")
                return Response(
                    {"error": "Failed to initialize serializer."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            if serializer.is_valid():
                try:
                    fitness_class = serializer.save()
                    response_data = {
                        "Fitness class": fitness_class.name,
                        "date time": fitness_class.datetime.strftime('%d/%m/%Y %I:%M %p'),
                        "Instructor": fitness_class.instructor,
                        "Available slots": fitness_class.available_slots
                    }
                    return Response(response_data, status=status.HTTP_201_CREATED)
                except Exception as e:
                    logger.error(f"Error saving fitness class: {str(e)}")
                    return Response(
                        {"error": "An error occurred while saving the fitness class."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                logger.warning(f"Validation failed: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Unexpected error in FitnessClassCreateAdmin view: {str(e)}")
            return Response(
                {"error": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class BookingCreate(CreateAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        try:
            fitness_class = serializer.validated_data.get('fitness_class')

            if not fitness_class:
                raise serializers.ValidationError("Fitness class is required.")

            if fitness_class.available_slots < 1:
                raise serializers.ValidationError("No available slots for this class.")

            fitness_class.available_slots -= 1
            fitness_class.save()
            serializer.save()

        except serializers.ValidationError as ve:
            logger.warning(f"Validation error during booking: {ve}")
            raise ve

        except Exception as e:
            logger.error(f"Unexpected error during booking creation: {str(e)}")
            raise serializers.ValidationError("An unexpected error occurred. Please try again later.")

class BookingListByEmail(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            email = request.query_params.get('email')
            if not email:
                return Response(
                    {"error": "Email parameter is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            tz_name = request.query_params.get('timezone', 'Asia/Kolkata')

            try:
                bookings = Booking.objects.filter(client_email=email)
            except Exception as e:
                logger.error(f"Error querying bookings for email {email}: {str(e)}")
                return Response(
                    {"error": "An error occurred while fetching bookings."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            try:
                serializer = BookingSerializer(bookings, many=True, context={'timezone': tz_name})
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Error serializing bookings: {str(e)}")
                return Response(
                    {"error": "An error occurred while serializing bookings."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Unexpected error in BookingListByEmail view: {str(e)}")
            return Response(
                {"error": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
