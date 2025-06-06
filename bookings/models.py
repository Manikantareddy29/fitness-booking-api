# models.py
from django.db import models


# Model
class FitnessClass(models.Model):
    name = models.CharField(max_length=50)
    datetime = models.DateTimeField()
    instructor = models.CharField(max_length=100)
    available_slots = models.PositiveIntegerField(default=0)

    def __str__(self):
        # Return name and datetime in readable format
        return f"{self.name} - {self.datetime.strftime('%d/%m/%Y %I:%M %p')}"

class Booking(models.Model):
    fitness_class = models.ForeignKey(FitnessClass, on_delete=models.CASCADE, related_name='bookings')
    client_name = models.CharField(max_length=100)
    client_email = models.EmailField()
    booked_at = models.DateTimeField(auto_now_add=True)  # automatically set on create

    def __str__(self):
        return f"{self.client_name} booked {self.fitness_class.name}"
