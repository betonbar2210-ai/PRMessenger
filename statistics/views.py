from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.views.generic import TemplateView

from config.settings import LOGIN_URL
from statistics.services import collect

CACHE_TIMEOUT = 60


class StatisticsView(LoginRequiredMixin, TemplateView):
    template_name = "statistics/statistics.html"
    login_url = LOGIN_URL

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        key = f"statistics:report:v1:{user.pk}:{'all' if user.is_manager else 'own'}"
        data = cache.get(key)
        if data is None:
            data = collect(user)
            cache.set(key, data, CACHE_TIMEOUT)
        data = dict(data)
        data["is_manager"] = user.is_manager
        data["scope"] = "все пользователи" if user.is_manager else "мои рассылки"
        context.update(data)
        return context
