from django.shortcuts import render
from .models import Contact, Gallery, Shop
# Create your views here.
def home(request):
    shop=Shop.objects.all()[0:5]
    print(shop)
    return render(request, 'index.html', {'shop':shop})

def contact(request):
    if request.method=='POST':
        name=request.POST['name']
        email=request.POST['email']
        phone=request.POST['phone']
        subject=request.POST['subject']
        message=request.POST['message']
        contact=Contact(name=name, email=email, phone=phone, subject=subject, message=message)
        contact.save()
        return render(request, 'thankyou.html')
    return render(request, 'contact.html')

def about(request):
    return render(request, 'about.html')

def shop(request):
    shop=Shop.objects.all()
    return render(request, 'shop.html', {'shop':shop})

def gallery(request):
    images=Gallery.objects.all()
    return render(request, 'gallery.html', {'images':images})

def coming_soon(request):
    return render(request, 'coming-soon.html')