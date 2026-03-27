from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("api/llm/chat/", views.llm_chat_api, name="llm_chat_api"),
    path("admin_login", views.admin_login_page, name="admin_login"),
    path("admin_login/", views.admin_login_page),
    path("admin_logout", views.admin_logout_page, name="admin_logout"),
    path("admin_logout/", views.admin_logout_page),
    path("admin/", views.admin_panel_page, name="admin_panel"),
    path("invite/<str:token>/", views.invite_accept_page, name="invite_accept"),
    path("login/", views.login_page, name="login"),
    path("register/", views.register_page, name="register"),
    path("logout/", views.logout_page, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("course-path/", views.course_path, name="course_path"),
    path("level/a1-1/", views.level_page, name="level_a1_1"),
    path("lesson/articles/", views.lesson_page, name="lesson_articles"),
    path("lesson/world/", views.world_module_page, name="lesson_world"),
    path("vocabulary/lexicon/", views.vocabulary_lexicon_page, name="vocabulary_lexicon"),
    path("vocabulary/test/", views.vocabulary_test_page, name="vocabulary_test"),
    path("vocabulary/spelling/", views.spelling_test_page, name="spelling_test"),
    path("profile/", views.profile_page, name="profile"),
]
