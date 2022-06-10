from django.db import models

# Create your models here.
class Contact(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField(max_length=100)
    phone = models.CharField(max_length=50)
    subject = models.CharField(max_length=50)
    message = models.TextField()

    def __str__(self):
        return self.name

class Shop(models.Model):
    name = models.CharField(max_length=50)
    image = models.ImageField(upload_to='shop_images')

    def __str__(self):
        return self.name

class Gallery(models.Model):
    image = models.ImageField(upload_to='gallery_images')

    def __str__(self):
        return self.image.name