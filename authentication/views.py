# Django imports
from django.shortcuts import render, redirect, reverse, HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _

# Application imports
from .models import LoginToken
from .forms import SignUpForm, LoginForm
from .decorators import anonymous_required


@anonymous_required
def signup_view(request):
    """
    Renders or processes the signup form through which
    a user can register himself.
    """
    # For POST requests, process the form data
    if request.method == 'POST':

        form = SignUpForm(request.POST)

        if form.is_valid():

            # Save user
            user = form.save()

            # If user exists
            if user is not None:
                # Create and send token
                LoginToken.objects.create_and_send(user=user)
                # Redirect to login view with token sent alert
                login_url = reverse('login')
                login_url += str('?token_sent')
                return redirect(login_url)

            # If user does not exist, redirect to login page
            return redirect('login')

    # If it is another request, instantiate empty form
    else:
        form = SignUpForm()

    return render(request, 'authentication/signup.html', {'form': form})


@anonymous_required
def login_view(request):
    """
    Renders or processes the login form. If the data is valid,
    a token is sent and the user redirected to the token verification
    page. Otherwise, the login form is rendered.
    """
    # For POST requests, process the form data
    if request.method == 'POST':

        form = LoginForm(request.POST)

        if form.is_valid():

            # Get user
            try:
                user = get_user_model().objects.get(email=form.cleaned_data['email'])
            except get_user_model().DoesNotExist:
                user = None

            # If user exists
            if user is not None:
                # Create and send token
                LoginToken.objects.create_and_send(user=user)
                # Render login template with token sent alert
                form = LoginForm()
                return render(request, 'authentication/login.html', {'form': form, 'token_sent': True})

    else:
        form = LoginForm()
        if 'invalid_token' in request.GET:
            return render(request, 'authentication/login.html', {'form': form, 'invalid_token': True})
        if 'token_sent' in request.GET:
            return render(request, 'authentication/login.html', {'form': form, 'token_sent': True})

    return render(request, 'authentication/login.html', {'form': form})


def token_verification_view(request, email_b64, code):
    """
    Checks login token. If the token is valid, the user is
    redirected to the login home page. If not, she is being
    redirected to the login page and an error is displayed.
    """
    email = LoginToken.b64_decoded(email_b64)
    # Authenticate
    user = authenticate(email=email, code=code)
    # If authentication is successful, log user in
    if user is not None:
        login(request, user)
        # Redirect user to login home
        return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
    # Render login template with invalid token parameter
    login_url = reverse('login')
    login_url += str('?invalid_token')
    return redirect(login_url)


@login_required(redirect_field_name=None)
def logout_view(request):
    """
    Logs a user out and redirects her to the login page.
    """
    logout(request)
    return redirect('login')


@login_required(redirect_field_name=None)
def home_view(request):
    """
    Login home view. For test purposes.
    """
    return HttpResponse(request.user.email)
