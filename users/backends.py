from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):

    def user_can_authenticate(self, user):
        if not super().user_can_authenticate(user):
            return False
        if user.is_blocked:
            return False
        if user.is_superuser:
            return True
        return user.is_email_verified
