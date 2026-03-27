from django.contrib import admin
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone

from .invitations import issue_invite, make_raw_token, token_hash
from .mailjet import build_invite_url, send_invite_email
from .models import Invitation, LearningWord, UserImprovement, UserProfile, UserWordProgress


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
	list_display = (
		"user",
		"current_language",
		"current_level",
		"streak_days",
		"prefers_full_name",
	)
	search_fields = ("user__username", "user__email")


@admin.register(LearningWord)
class LearningWordAdmin(admin.ModelAdmin):
    list_display = ("language", "article", "word", "translation", "difficulty")
    search_fields = ("word", "translation")
    list_filter = ("language", "difficulty")


@admin.register(UserWordProgress)
class UserWordProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "word", "status", "mastery_score", "review_count")
    search_fields = ("user__username", "word__word")
    list_filter = ("status",)


@admin.register(UserImprovement)
class UserImprovementAdmin(admin.ModelAdmin):
	list_display = ("user", "category", "score_delta", "created_at")
	search_fields = ("user__username", "category")
	list_filter = ("category",)


@admin.action(description="Revoke selected invitations")
def revoke_invitations(modeladmin, request, queryset):
	count = 0
	for invite in queryset:
		if invite.revoked_at is None:
			invite.revoke()
			count += 1
	modeladmin.message_user(request, f"Revoked {count} invitation(s).", level=messages.INFO)


@admin.action(description="Resend selected invitations (creates replacement token)")
def resend_invitations(modeladmin, request, queryset):
	sent = 0
	failed = 0
	for invite in queryset:
		try:
			new_invite, raw_token = issue_invite(email=invite.email, invited_by=request.user)
			send_invite_email(invite.email, build_invite_url(raw_token))
			invite.revoke()
			sent += 1
		except Exception:
			failed += 1
	modeladmin.message_user(
		request,
		f"Resent: {sent}, failed: {failed}.",
		level=messages.INFO,
	)


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
	list_display = (
		"email",
		"invited_by",
		"created_at",
		"expires_at",
		"used_at",
		"revoked_at",
	)
	search_fields = ("email", "invited_by__username")
	list_filter = ("used_at", "revoked_at")
	readonly_fields = ("token_hash", "created_at", "used_at", "revoked_at")
	actions = [revoke_invitations, resend_invitations]

	def save_model(self, request, obj, form, change):
		if not change and not obj.token_hash:
			raw_token = make_raw_token()
			obj.token_hash = token_hash(raw_token)
			if not obj.expires_at:
				obj.expires_at = timezone.now() + timedelta(days=7)
			super().save_model(request, obj, form, change)
			invite_url = build_invite_url(raw_token)
			self.message_user(
				request,
				(
					"Invitation created. Copy this one-time acceptance URL now: "
					f"{invite_url}"
				),
				level=messages.WARNING,
			)
			return
		super().save_model(request, obj, form, change)
