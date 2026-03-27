from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate

from .models import UserProfile

User = get_user_model()


class RegisterForm(forms.Form):
    name = forms.CharField(max_length=150)
    email = forms.EmailField(max_length=254)
    password = forms.CharField(min_length=8, max_length=128)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self):
        name = self.cleaned_data["name"].strip()
        email = self.cleaned_data["email"].strip().lower()
        password = self.cleaned_data["password"]

        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=name,
            password=password,
        )
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(max_length=254)
    password = forms.CharField(max_length=128)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email", "").strip().lower()
        password = cleaned_data.get("password", "")

        if email and password:
            user = None
            email_matches = User.objects.filter(email__iexact=email)
            for candidate in email_matches:
                user = authenticate(username=candidate.username, password=password)
                if user is not None:
                    break
            if user is None:
                raise forms.ValidationError("Invalid email or password.")
            cleaned_data["user"] = user
        return cleaned_data


class InviteAcceptForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField(max_length=254)
    username = forms.CharField(max_length=150)
    password = forms.CharField(min_length=8, max_length=128)
    password_confirm = forms.CharField(min_length=8, max_length=128)
    prefers_username = forms.BooleanField(required=False, initial=False)

    def __init__(self, *args, invite_email: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.invite_email = invite_email.strip().lower()
        self.fields["email"].initial = self.invite_email

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if email != self.invite_email:
            raise forms.ValidationError("Email must match the invited address.")
        return email

    def clean_username(self):
        username = self.cleaned_data["username"].strip().lower()
        if not username:
            raise forms.ValidationError("Username is required.")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password", "")
        password_confirm = cleaned_data.get("password_confirm", "")
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self):
        first_name = self.cleaned_data["first_name"].strip()
        last_name = self.cleaned_data["last_name"].strip()
        email = self.cleaned_data["email"].strip().lower()
        username = self.cleaned_data["username"].strip().lower()
        password = self.cleaned_data["password"]

        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
        )
        profile = UserProfile.objects.get(user=user)
        profile.prefers_full_name = not self.cleaned_data.get("prefers_username", False)
        profile.save(update_fields=["prefers_full_name"])
        return user


class AdminPanelPasswordForm(forms.Form):
    password = forms.CharField(max_length=128, widget=forms.PasswordInput)


class AdminAccessRequestForm(forms.Form):
    access_code = forms.CharField(
        max_length=128,
        widget=forms.PasswordInput(render_value=False),
    )


class ProfileLLMSettingsForm(forms.Form):
    MODEL_CHOICES = [
        ("lumina", "Lumina"),
        ("chatgpt", "ChatGPT"),
        ("claude", "Claude"),
    ]

    llm_model = forms.ChoiceField(choices=MODEL_CHOICES)
    api_key = forms.CharField(
        max_length=512,
        required=False,
        widget=forms.PasswordInput(render_value=False),
    )

    def __init__(self, *args, has_existing_key: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.has_existing_key = has_existing_key

    def clean(self):
        cleaned_data = super().clean()
        llm_model = cleaned_data.get("llm_model", "")
        api_key = (cleaned_data.get("api_key", "") or "").strip()

        if llm_model in {"chatgpt", "claude"} and not api_key and not self.has_existing_key:
            raise forms.ValidationError("API key is required for ChatGPT or Claude.")

        cleaned_data["api_key"] = api_key
        return cleaned_data
