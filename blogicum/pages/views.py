from django.shortcuts import render
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth import login


def about(request):
    return render(request, "pages/about.html")


def rules(request):
    return render(request, "pages/rules.html")


def csrf_failure(request, reason=''):
    return render(request, 'pages/403csrf.html', status=403)


def page_not_found(request, exception):
    return render(request, 'pages/404.html', status=404)


def server_error(request):
    return render(request, 'pages/500.html', status=500)


class RegistrationView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('blog:index')
    template_name = 'registration/registration_form.html'
    
    def form_valid(self, form):
        creation_response = super().form_valid(form)
        login(self.request, self.object)
        return creation_response


registration = RegistrationView.as_view()