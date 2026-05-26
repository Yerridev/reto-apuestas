from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    def create_user(self, email, dni, password=None, **extra_fields):
        if not email:
            raise ValueError(_('El correo electrónico es obligatorio.'))
        if not dni:
            raise ValueError(_('El DNI es obligatorio.'))
        email = self.normalize_email(email)
        user = self.model(email=email, dni=dni, **extra_fields)
        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, dni, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        from apps.users.choices import AccountStatus
        extra_fields.setdefault('account_status', AccountStatus.VERIFICADO)
        return self.create_user(email, dni, password, **extra_fields)
