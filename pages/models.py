from unicodedata import category
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

class Category(models.Model):
    name=models.CharField(max_length=500)

    def __str__(self):
        return self.name


class Nominated_Brand(models.Model):
    name=models.CharField(max_length=100)
    nominated=models.IntegerField(default=1)
    category = models.CharField(max_length=500)
    def __str__(self):
        return self.name+','+self.category+','+ str(self.nominated)


class Nomination_visiblility(models.Model):
    visibility=models.BooleanField(default=False)

    def __str__(self):
        return str(self.visibility)

class Vote_visiblility(models.Model):
    visibility=models.BooleanField(default=False)

    def __str__(self):
        return str(self.visibility)

class Nominee(models.Model):
    # name = models.CharField(max_length=50)
    email= models.EmailField(max_length=100)
    brand_name= models.CharField(max_length=50)
    category = models.CharField(max_length=500)
    year=models.CharField(max_length=100)

    def __str__(self):
        return self.email

