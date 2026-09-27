from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from config.settings import LOGIN_URL


class ManagerRequiredMixin(LoginRequiredMixin):

    login_url = LOGIN_URL

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not getattr(request.user, "is_manager", False):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class OwnerScopedMixin(LoginRequiredMixin):

    login_url = LOGIN_URL
    owner_field = "owner"

    def get_owner_field(self) -> str:
        return self.owner_field

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_manager:
            return qs
        return qs.filter(**{self.get_owner_field(): self.request.user})


class OwnedObjectMixin(OwnerScopedMixin):

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not self._is_own(obj) and not self.request.user.is_manager:
            raise PermissionDenied
        return obj

    def _is_own(self, obj) -> bool:
        return getattr(obj, self.get_owner_field()) == self.request.user


class OwnerWriteMixin(OwnedObjectMixin):

    def get_object(self, queryset=None):
        # super(OwnedObjectMixin, self) начинает поиск с класса после
        # OwnedObjectMixin и доходит до SingleObjectMixin.get_object —
        # так мы получаем объект, минуя послабление «менеджер может смотреть».
        obj = super(OwnedObjectMixin, self).get_object(queryset)
        if not self._is_own(obj):
            raise PermissionDenied
        return obj


class OwnerCreateMixin(LoginRequiredMixin):

    login_url = LOGIN_URL
    owner_field = "owner"

    def form_valid(self, form):
        setattr(form.instance, self.owner_field, self.request.user)
        return super().form_valid(form)
