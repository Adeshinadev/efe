from django.shortcuts import redirect, render
from .models import Category, Contact, Gallery, Nominated_Brand, Nomination_visiblility, Nominee, Shop, Vote_visiblility
from django.contrib import messages

from datetime import date
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
todays_date = date.today()

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

def efe_portal(request):
    return render(request, 'vote.html')

def nominate_redirect(request):
    category=Category.objects.all()
    return render(request,'nominate.html', {'categories':category})


def nominate(request):
    if request.method=='POST':
        email=request.POST['email']
        brand_name=request.POST['brand_name'].lower()
        category=request.POST['category']
        category_get=Category.objects.get(id=int(category))
        nominated=Nominated_Brand.objects.filter(name=brand_name,category=category_get.name).first()
        if category=='Select A Category...':
            messages.info(request, 'Please select it valid category')
            return redirect('nominate_redirect')
        else:
            nominate=Nominee.objects.filter(email=email, brand_name=brand_name,year=todays_date.year, category=category_get.name)
            if nominate:
                messages.info(request, 'you have nominated this brand already.')
                return redirect('nominate_redirect')
            else:
                if nominated:
                    nominated.nominated= nominated.nominated+1
                    nominee=Nominee(email=email, brand_name=brand_name, category=category_get.name,year=todays_date.year)
                    nominated.save()
                    nominee.save()
                    messages.info(request, f'Sucess! you have nominated {brand_name}')
                    return redirect('nominate_redirect')
                nominee=Nominee(email=email, brand_name=brand_name, category=category_get.name,year=todays_date.year)
                Nominated_Brand_save=Nominated_Brand(name=brand_name,category=category_get.name)
                Nominated_Brand_save.save()
                nominee.save()
                messages.info(request, f'Sucess! you have nominated {brand_name}')
                return redirect('nominate_redirect')
    else:
        if Nomination_visiblility.objects.all().first().visibility:
            category=Category.objects.all()
            return render(request, 'nominate.html', {'categories':category})
       
        return render(request,'coming-soon.html')


def dashboard(request):
    if request.user.is_authenticated and request.user.is_staff:
        nomination_status=Nomination_visiblility.objects.all().first()
        election_status=Vote_visiblility.objects.all().first()
        categories=Category.objects.all()
        return render(request, 'dahsboard2.html',{'nomination_status':nomination_status,'election_status':election_status,'categories':categories})
    else:
        return redirect('login')


def login(request):
    if request.method=='POST':
        username=request.POST['username']
        password=request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            auth_login(request, user)
            return redirect('dashboard')
          
        else:
            messages.info(request,'incorrect credentials')
            return render(request, 'login.html')
    return render(request, 'login.html')

def modify_nomination_status(request,id):
    if id==1:
        Nomination_visiblility.objects.all().delete()
        Nomination_visiblility_save=Nomination_visiblility(visibility=True)
        Nomination_visiblility_save.save()
        messages.info(request, f'Nomination page is now available for {todays_date.year}')
        return redirect('dashboard')
    else:
        Nomination_visiblility.objects.all().delete()
        Nomination_visiblility_save=Nomination_visiblility(visibility=False)
        Nomination_visiblility_save.save()
        messages.info(request, f'Nomination page has been closed for {todays_date.year}')
        return redirect('dashboard')


def election_status(request,id):
    if id==1:
        Vote_visiblility.objects.all().delete()
        Vote_visiblility_save=Vote_visiblility(visibility=True)
        Nomination_visiblility.objects.all().delete()
        Nomination_visiblility_save=Nomination_visiblility(visibility=False)
        Nomination_visiblility_save.save()
        Vote_visiblility_save.save()
        messages.info(request, f'Voting page is now available for {todays_date.year}')
        return redirect('dashboard')
    else:
        Vote_visiblility.objects.all().delete()
        Vote_visiblility_save=Vote_visiblility(visibility=False)
        Vote_visiblility_save.save()
        messages.info(request, f'Voting page has been closed for {todays_date.year}')
        return redirect('dashboard')


    
def nomination_result(request):
    category_id=request.POST['category_id']
    category=Category.objects.get(pk=category_id)
    print(category)
    nominated_brands=Nominated_Brand.objects.filter(category=category.name)
    print(nominated_brands)
    return render(request,'nomination_result.html',{'nominated_brands':nominated_brands})