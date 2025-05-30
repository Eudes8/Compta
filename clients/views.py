from django.shortcuts import render, get_object_or_404
from .models import Client

def client_list(request):
    clients = Client.objects.all()
    return render(request, 'clients/client_list.html', {'clients': clients})

def client_detail(request, client_id):
    client = get_object_or_404(Client, pk=client_id)
    return render(request, 'clients/client_detail.html', {'client': client})
