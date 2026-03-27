from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .fields import EncryptedTextField


class UserProfile(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	current_language = models.CharField(max_length=40, default="German")
	current_level = models.CharField(max_length=20, default="A1.1")
	weekly_goal = models.CharField(max_length=40, default="5 lessons")
	streak_days = models.PositiveIntegerField(default=0)
	prefers_full_name = models.BooleanField(default=True)
	llm_model = models.CharField(max_length=20, default="lumina")
	llm_api_key = EncryptedTextField(blank=True, default="")
	encrypted_notes = EncryptedTextField(blank=True, default="")

	def __str__(self) -> str:
		return f"Profile<{self.user.username}>"


class LearningWord(models.Model):
    language = models.CharField(max_length=40, default="German")
    article = models.CharField(max_length=8, blank=True, default="")
    word = models.CharField(max_length=100)
    translation = models.CharField(max_length=160)
    difficulty = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("language", "article", "word")

    def __str__(self) -> str:
        prefix = f"{self.article} " if self.article else ""
        return f"{prefix}{self.word}"


class UserWordProgress(models.Model):
    STATUS_NEW = "new"
    STATUS_LEARNING = "learning"
    STATUS_LEARNED = "learned"
    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_LEARNING, "Learning"),
        (STATUS_LEARNED, "Learned"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    word = models.ForeignKey(LearningWord, on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_NEW)
    mastery_score = models.PositiveSmallIntegerField(default=0)
    review_count = models.PositiveIntegerField(default=0)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "word")


class UserImprovement(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	category = models.CharField(max_length=40)
	score_delta = models.IntegerField(default=0)
	encrypted_note = EncryptedTextField(blank=True, default="")
	created_at = models.DateTimeField(auto_now_add=True)


class Invitation(models.Model):
	email = models.EmailField(db_index=True)
	token_hash = models.CharField(max_length=64, unique=True)
	invited_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="sent_invitations",
	)
	created_at = models.DateTimeField(auto_now_add=True)
	expires_at = models.DateTimeField()
	used_at = models.DateTimeField(null=True, blank=True)
	revoked_at = models.DateTimeField(null=True, blank=True)

	def __str__(self) -> str:
		return f"Invite<{self.email}>"

	@property
	def is_active(self) -> bool:
		now = timezone.now()
		return self.revoked_at is None and self.used_at is None and self.expires_at > now

	def mark_used(self) -> None:
		self.used_at = timezone.now()
		self.save(update_fields=["used_at"])

	def revoke(self) -> None:
		self.revoked_at = timezone.now()
		self.save(update_fields=["revoked_at"])


class AdminAccessToken(models.Model):
	email = models.EmailField(db_index=True)
	token_hash = models.CharField(max_length=64, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)
	expires_at = models.DateTimeField()
	used_at = models.DateTimeField(null=True, blank=True)
	revoked_at = models.DateTimeField(null=True, blank=True)

	def __str__(self) -> str:
		return f"AdminAccessToken<{self.email}>"

	@property
	def is_active(self) -> bool:
		now = timezone.now()
		return self.revoked_at is None and self.used_at is None and self.expires_at > now

	def mark_used(self) -> None:
		self.used_at = timezone.now()
		self.save(update_fields=["used_at"])

	def revoke(self) -> None:
		self.revoked_at = timezone.now()
		self.save(update_fields=["revoked_at"])


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
