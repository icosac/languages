import string
import re
import unicodedata
import json
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
import secrets

from .admin_access import issue_admin_access_token, resolve_admin_access_token
from .forms import (
    AdminAccessRequestForm,
    AdminPanelPasswordForm,
    InviteAcceptForm,
    LoginForm,
    ProfileLLMSettingsForm,
    RegisterForm,
)
from .invitations import resolve_invite
from .mailjet import build_admin_access_url, send_admin_access_email
from .llm import LLMServiceError, generate_llm_response
from .models import LearningWord, UserImprovement, UserProfile, UserWordProgress
from .totp import verify_totp_code


WORD_TYPE_CHOICES = [
    ("noun", "Noun"),
    ("verb", "Verb"),
    ("adjective", "Adjective"),
    ("adverb", "Adverb"),
    ("article", "Article"),
    ("preposition", "Preposition"),
]
WORD_TYPE_LABELS = dict(WORD_TYPE_CHOICES)

SEED_LEXICON_ENTRIES = [
    {"article": "Der", "word": "Zeitgeist", "translation": "Spirit of the times", "difficulty": 3, "word_type": "noun"},
    {"article": "", "word": "Verständnisvoll", "translation": "Understanding", "difficulty": 3, "word_type": "adjective"},
    {"article": "", "word": "Entscheiden", "translation": "Decide", "difficulty": 2, "word_type": "verb"},
    {"article": "", "word": "Plötzlich", "translation": "Suddenly", "difficulty": 2, "word_type": "adverb"},
    {"article": "Die", "word": "Sehnsucht", "translation": "Longing", "difficulty": 3, "word_type": "noun"},
    {"article": "", "word": "Wandern", "translation": "Hike", "difficulty": 2, "word_type": "verb"},
    {"article": "Die", "word": "Freiheit", "translation": "Freedom", "difficulty": 2, "word_type": "noun"},
    {"article": "", "word": "Ehrgeizig", "translation": "Ambitious", "difficulty": 3, "word_type": "adjective"},
    {"article": "", "word": "Hoffentlich", "translation": "Hopefully", "difficulty": 2, "word_type": "adverb"},
    {"article": "", "word": "Glauben", "translation": "Believe", "difficulty": 2, "word_type": "verb"},
    {"article": "Der", "word": "Erfolg", "translation": "Success", "difficulty": 2, "word_type": "noun"},
    {"article": "", "word": "Zufrieden", "translation": "Content", "difficulty": 2, "word_type": "adjective"},
    {"article": "", "word": "Vielleicht", "translation": "Maybe", "difficulty": 1, "word_type": "adverb"},
    {"article": "", "word": "Unternehmen", "translation": "Undertake", "difficulty": 3, "word_type": "verb"},
    {"article": "Das", "word": "Gebäude", "translation": "Building", "difficulty": 2, "word_type": "noun"},
    {"article": "", "word": "Erfahren", "translation": "Experience", "difficulty": 2, "word_type": "verb"},
    {"article": "", "word": "Überzeugt", "translation": "Convinced", "difficulty": 3, "word_type": "adjective"},
    {"article": "", "word": "Gestern", "translation": "Yesterday", "difficulty": 1, "word_type": "adverb"},
    {"article": "", "word": "Versuchen", "translation": "Try", "difficulty": 2, "word_type": "verb"},
    {"article": "Die", "word": "Zukunft", "translation": "Future", "difficulty": 2, "word_type": "noun"},
    {"article": "Der", "word": "Baum", "translation": "Tree", "difficulty": 1, "word_type": "noun"},
    {"article": "Die", "word": "Bibliothek", "translation": "Library", "difficulty": 1, "word_type": "noun"},
    {"article": "Die", "word": "Blume", "translation": "Flower", "difficulty": 1, "word_type": "noun"},
    {"article": "Das", "word": "Fenster", "translation": "Window", "difficulty": 1, "word_type": "noun"},
]
SEEDED_WORD_TYPES = {entry["word"].strip().lower(): entry["word_type"] for entry in SEED_LEXICON_ENTRIES}

WORLD_PROGRESS_CATEGORY_PREFIX = "world_module:"

WORLD_CONTINENTS = [
    {
        "slug": "europe",
        "label": "Europa",
        "english_label": "Europe",
        "countries": [
            {
                "code": "DE",
                "name": "Germany",
                "geo_names": ["Germany"],
                "nation_answers": ["Deutschland"],
                "nationality_answers": ["Deutscher", "Deutsche", "Deutsch"],
                "language_answers": ["Deutsch"],
                "path": "M238 118 L281 112 L305 144 L292 186 L248 193 L221 156 Z",
                "label_x": 262,
                "label_y": 156,
            },
            {
                "code": "FR",
                "name": "France",
                "geo_names": ["France"],
                "nation_answers": ["Frankreich"],
                "nationality_answers": ["Franzose", "Franzosin", "Franzoesin", "Franzosisch", "Französisch"],
                "language_answers": ["Franzosisch", "Französisch"],
                "path": "M178 162 L219 153 L239 188 L214 223 L173 208 Z",
                "label_x": 207,
                "label_y": 190,
            },
            {
                "code": "ES",
                "name": "Spain",
                "geo_names": ["Spain"],
                "nation_answers": ["Spanien"],
                "nationality_answers": ["Spanier", "Spanierin", "Spanisch"],
                "language_answers": ["Spanisch"],
                "path": "M108 226 L163 216 L181 245 L162 272 L109 275 L86 246 Z",
                "label_x": 132,
                "label_y": 248,
            },
            {
                "code": "IT",
                "name": "Italy",
                "geo_names": ["Italy"],
                "nation_answers": ["Italien"],
                "nationality_answers": ["Italiener", "Italienerin", "Italienisch"],
                "language_answers": ["Italienisch"],
                "path": "M286 202 L312 219 L326 252 L317 287 L292 272 L299 245 L274 225 Z",
                "label_x": 310,
                "label_y": 250,
            },
            {
                "code": "AT",
                "name": "Austria",
                "geo_names": ["Austria"],
                "nation_answers": ["Osterreich", "Österreich"],
                "nationality_answers": ["Osterreicher", "Österreicher", "Osterreicherin", "Österreicherin"],
                "language_answers": ["Deutsch"],
                "path": "M258 178 L303 174 L311 193 L271 202 L247 191 Z",
                "label_x": 279,
                "label_y": 189,
            },
        ],
    },
    {
        "slug": "asia",
        "label": "Asien",
        "english_label": "Asia",
        "countries": [
            {
                "code": "CN",
                "name": "China",
                "geo_names": ["China"],
                "nation_answers": ["China"],
                "nationality_answers": ["Chinese", "Chinesin", "Chinesisch"],
                "language_answers": ["Chinesisch"],
                "path": "M173 126 L255 112 L311 148 L289 208 L231 234 L169 211 L145 165 Z",
                "label_x": 226,
                "label_y": 172,
            },
            {
                "code": "JP",
                "name": "Japan",
                "geo_names": ["Japan"],
                "nation_answers": ["Japan"],
                "nationality_answers": ["Japaner", "Japanerin", "Japanisch"],
                "language_answers": ["Japanisch"],
                "path": "M354 151 L372 136 L387 152 L378 177 L360 186 L347 171 Z",
                "label_x": 366,
                "label_y": 163,
            },
            {
                "code": "IN",
                "name": "India",
                "geo_names": ["India"],
                "nation_answers": ["Indien"],
                "nationality_answers": ["Inder", "Inderin", "Indisch"],
                "language_answers": ["Hindi", "Indisch"],
                "path": "M192 224 L238 216 L252 241 L233 285 L199 272 L182 241 Z",
                "label_x": 219,
                "label_y": 245,
            },
            {
                "code": "KR",
                "name": "South Korea",
                "geo_names": ["South Korea"],
                "nation_answers": ["Sudkorea", "Südkorea"],
                "nationality_answers": ["Sudkoreaner", "Südkoreaner", "Sudkoreanerin", "Südkoreanerin"],
                "language_answers": ["Koreanisch"],
                "path": "M325 154 L343 152 L348 169 L336 184 L319 179 L317 164 Z",
                "label_x": 334,
                "label_y": 167,
            },
        ],
    },
    {
        "slug": "africa",
        "label": "Afrika",
        "english_label": "Africa",
        "countries": [
            {
                "code": "MA",
                "name": "Morocco",
                "geo_names": ["Morocco"],
                "nation_answers": ["Marokko"],
                "nationality_answers": ["Marokkaner", "Marokkanerin", "Marokkanisch"],
                "language_answers": ["Arabisch"],
                "path": "M123 126 L177 126 L177 153 L132 162 L114 142 Z",
                "label_x": 148,
                "label_y": 142,
            },
            {
                "code": "EG",
                "name": "Egypt",
                "geo_names": ["Egypt"],
                "nation_answers": ["Agypten", "Ägypten"],
                "nationality_answers": ["Agypter", "Ägypter", "Agypterin", "Ägypterin"],
                "language_answers": ["Arabisch"],
                "path": "M279 139 L323 137 L336 164 L293 179 L269 163 Z",
                "label_x": 304,
                "label_y": 157,
            },
            {
                "code": "NG",
                "name": "Nigeria",
                "geo_names": ["Nigeria"],
                "nation_answers": ["Nigeria"],
                "nationality_answers": ["Nigerianer", "Nigerianerin", "Nigerianisch"],
                "language_answers": ["Englisch"],
                "path": "M186 204 L233 201 L244 236 L214 258 L179 238 Z",
                "label_x": 212,
                "label_y": 228,
            },
            {
                "code": "ZA",
                "name": "South Africa",
                "geo_names": ["South Africa"],
                "nation_answers": ["Sudafrika", "Südafrika"],
                "nationality_answers": ["Sudafrikaner", "Südafrikaner", "Sudafrikanerin", "Südafrikanerin"],
                "language_answers": ["Englisch"],
                "path": "M196 274 L258 274 L284 309 L252 334 L192 323 L174 296 Z",
                "label_x": 230,
                "label_y": 304,
            },
        ],
    },
    {
        "slug": "america",
        "label": "Amerika",
        "english_label": "Americas",
        "countries": [
            {
                "code": "CA",
                "name": "Canada",
                "geo_names": ["Canada"],
                "nation_answers": ["Kanada"],
                "nationality_answers": ["Kanadier", "Kanadierin", "Kanadisch"],
                "language_answers": ["Englisch", "Franzosisch", "Französisch"],
                "path": "M102 84 L188 74 L242 118 L218 166 L132 168 L88 131 Z",
                "label_x": 160,
                "label_y": 123,
            },
            {
                "code": "US",
                "name": "United States",
                "geo_names": ["United States of America", "United States"],
                "nation_answers": ["USA", "Vereinigte Staaten"],
                "nationality_answers": ["Amerikaner", "Amerikanerin", "Amerikanisch"],
                "language_answers": ["Englisch"],
                "path": "M112 172 L226 164 L246 212 L214 239 L136 239 L104 206 Z",
                "label_x": 176,
                "label_y": 201,
            },
            {
                "code": "BR",
                "name": "Brazil",
                "geo_names": ["Brazil"],
                "nation_answers": ["Brasilien"],
                "nationality_answers": ["Brasilianer", "Brasilianerin", "Brasilianisch"],
                "language_answers": ["Portugiesisch", "Portugisisch"],
                "path": "M236 245 L312 237 L341 282 L314 344 L251 336 L221 293 Z",
                "label_x": 284,
                "label_y": 287,
            },
            {
                "code": "AR",
                "name": "Argentina",
                "geo_names": ["Argentina"],
                "nation_answers": ["Argentinien"],
                "nationality_answers": ["Argentinier", "Argentinierin", "Argentinisch"],
                "language_answers": ["Spanisch"],
                "path": "M243 349 L294 343 L301 406 L276 451 L243 436 L227 389 Z",
                "label_x": 271,
                "label_y": 394,
            },
            {
                "code": "MX",
                "name": "Mexico",
                "geo_names": ["Mexico"],
                "nation_answers": ["Mexiko"],
                "nationality_answers": ["Mexikaner", "Mexikanerin", "Mexikanisch"],
                "language_answers": ["Spanisch"],
                "path": "M86 222 L129 212 L151 239 L134 266 L93 263 L76 241 Z",
                "label_x": 114,
                "label_y": 241,
            },
        ],
    },
    {
        "slug": "oceania",
        "label": "Ozeanien",
        "english_label": "Oceania",
        "countries": [
            {
                "code": "AU",
                "name": "Australia",
                "geo_names": ["Australia"],
                "nation_answers": ["Australien"],
                "nationality_answers": ["Australier", "Australierin", "Australisch"],
                "language_answers": ["Englisch"],
                "path": "M208 236 L299 231 L348 274 L328 332 L246 347 L184 302 Z",
                "label_x": 265,
                "label_y": 292,
            },
            {
                "code": "NZ",
                "name": "New Zealand",
                "geo_names": ["New Zealand"],
                "nation_answers": ["Neuseeland"],
                "nationality_answers": ["Neuseelander", "Neuseeländer", "Neuseelanderin", "Neuseeländerin"],
                "language_answers": ["Englisch"],
                "path": "M389 292 L408 279 L422 296 L418 322 L398 336 L383 319 Z",
                "label_x": 404,
                "label_y": 307,
            },
            {
                "code": "FJ",
                "name": "Fiji",
                "geo_names": ["Fiji"],
                "nation_answers": ["Fidschi"],
                "nationality_answers": ["Fidschianer", "Fidschianerin"],
                "language_answers": ["Englisch"],
                "path": "M364 236 L378 229 L389 242 L382 258 L367 258 Z",
                "label_x": 377,
                "label_y": 246,
            },
            {
                "code": "PG",
                "name": "Papua New Guinea",
                "geo_names": ["Papua New Guinea"],
                "nation_answers": ["Papua Neuguinea", "Papua-Neuguinea"],
                "nationality_answers": [
                    "Papua Neuguineer",
                    "Papua Neuguineerin",
                    "Papua-Neuguineer",
                    "Papua-Neuguineerin",
                ],
                "language_answers": ["Englisch"],
                "path": "M314 201 L364 196 L386 223 L362 246 L316 241 L296 219 Z",
                "label_x": 345,
                "label_y": 221,
            },
        ],
    },
]

WORLD_CONTINENTS_BY_SLUG = {continent["slug"]: continent for continent in WORLD_CONTINENTS}
WORLD_COUNTRY_TO_CONTINENT = {}
for _continent in WORLD_CONTINENTS:
    for _country in _continent["countries"]:
        WORLD_COUNTRY_TO_CONTINENT[_country["code"]] = _continent["slug"]


def _normalize_text(value: str) -> str:
    normalized = " ".join((value or "").strip().lower().split())
    for token in [",", ".", ";", ":", "!", "?", "'", '"']:
        normalized = normalized.replace(token, "")
    return normalized


def _normalize_translation(value: str) -> str:
    normalized = _normalize_text(value)
    for prefix in ("the ", "a ", "an ", "to "):
        if normalized.startswith(prefix):
            return normalized[len(prefix):]
    return normalized


def _translation_matches(expected: str, submitted: str) -> bool:
    submitted_normalized = _normalize_translation(submitted)
    return bool(submitted_normalized) and submitted_normalized == _normalize_translation(expected)


def _word_display(word: LearningWord) -> str:
    return f"{word.article} {word.word}".strip()


def _word_type_for_word(word: LearningWord) -> str:
    lookup = SEEDED_WORD_TYPES.get(word.word.strip().lower())
    if lookup:
        return lookup
    if word.article:
        return "noun"

    lowered = word.word.strip().lower()
    if lowered.endswith(("en", "eln", "ern", "ieren")):
        return "verb"
    if lowered.endswith(("lich", "ig", "isch", "bar", "sam", "los")):
        return "adjective"
    if lowered.endswith(("weise", "wärts", "mals", "ends")):
        return "adverb"
    return "noun"


def _seed_learning_words(language: str) -> None:
    for entry in SEED_LEXICON_ENTRIES:
        LearningWord.objects.get_or_create(
            language=language,
            article=entry["article"],
            word=entry["word"],
            defaults={
                "translation": entry["translation"],
                "difficulty": entry["difficulty"],
            },
        )


def _ensure_user_progress_for_language(user, language: str, count: int | None = None) -> None:
    _seed_learning_words(language)
    seeded_keys = {
        (entry["article"], entry["word"])
        for entry in SEED_LEXICON_ENTRIES
    }
    words_qs = [
        word
        for word in LearningWord.objects.filter(language=language).order_by("id")
        if (word.article, word.word) in seeded_keys
    ]
    if count is not None:
        words_qs = words_qs[:count]

    existing_word_ids = set(
        UserWordProgress.objects.filter(user=user, word__language=language).values_list("word_id", flat=True)
    )
    progress_rows = [
        UserWordProgress(user=user, word=word)
        for word in words_qs
        if word.id not in existing_word_ids
    ]
    if progress_rows:
        UserWordProgress.objects.bulk_create(progress_rows)
def _practice_rows(user, language: str, count: int = 20) -> list[dict]:
    _ensure_user_progress_for_language(user, language, count=count)
    progress_rows = list(
        UserWordProgress.objects.filter(user=user, word__language=language)
        .select_related("word")
        .order_by("word_id")[:count]
    )

    rows = []
    for progress in progress_rows:
        word = progress.word
        expected_type = _word_type_for_word(word)
        rows.append(
            {
                "id": word.id,
                "word": word,
                "display_word": _word_display(word),
                "translation": word.translation,
                "expected_type": expected_type,
                "expected_type_label": WORD_TYPE_LABELS.get(expected_type, "Noun"),
            }
        )
    return rows


def _update_word_progress(user, word: LearningWord, score: int, max_score: int) -> None:
    progress, _ = UserWordProgress.objects.get_or_create(user=user, word=word)
    progress.review_count += 1
    progress.last_reviewed_at = timezone.now()

    if score >= max_score:
        gain = 16
    elif score > 0:
        gain = 8
    else:
        gain = 2
    progress.mastery_score = min(100, progress.mastery_score + gain)

    if progress.mastery_score >= 80:
        progress.status = UserWordProgress.STATUS_LEARNED
    else:
        progress.status = UserWordProgress.STATUS_LEARNING
    progress.save(update_fields=["review_count", "last_reviewed_at", "mastery_score", "status"])


def _split_term(raw_term: str) -> tuple[str, str]:
    parts = raw_term.strip().split(maxsplit=1)
    if len(parts) == 2 and parts[0].strip().lower() in {"der", "die", "das"}:
        return parts[0].capitalize(), parts[1].strip()
    return "", raw_term.strip()


def _normalize_world_answer(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", (value or "").strip().lower())
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.replace("-", " ")
    normalized = re.sub(r"[^\w\s/]", "", normalized)
    return " ".join(normalized.split())


def _world_answer_matches(submitted: str, accepted_values: list[str]) -> bool:
    normalized_submitted = _normalize_world_answer(submitted)
    if not normalized_submitted:
        return False

    normalized_accepted = {
        _normalize_world_answer(value) for value in accepted_values if _normalize_world_answer(value)
    }
    if normalized_submitted in normalized_accepted:
        return True

    fragments = {
        part.strip()
        for part in re.split(r"[/,;]| oder | or ", normalized_submitted)
        if part.strip()
    }
    return bool(fragments & normalized_accepted)


def _world_progress_for_user(user) -> dict[str, dict]:
    rows = UserImprovement.objects.filter(
        user=user,
        category__startswith=WORLD_PROGRESS_CATEGORY_PREFIX,
    ).order_by("created_at")
    progress = {}
    for row in rows:
        country_code = (row.category[len(WORLD_PROGRESS_CATEGORY_PREFIX):] or "").upper()
        if country_code not in WORLD_COUNTRY_TO_CONTINENT:
            continue

        item = progress.setdefault(
            country_code,
            {
                "attempts": 0,
                "best_score": 0,
                "last_score": 0,
                "last_submitted_at": row.created_at,
                "completed_at": None,
            },
        )
        item["attempts"] += 1
        item["last_score"] = row.score_delta
        item["last_submitted_at"] = row.created_at
        if row.score_delta > item["best_score"]:
            item["best_score"] = row.score_delta
        if row.score_delta >= 3:
            item["completed_at"] = row.created_at
    return progress


def _world_continent_metrics(continent: dict, progress: dict[str, dict]) -> tuple[int, int, int]:
    total = len(continent["countries"])
    completed = sum(1 for row in continent["countries"] if progress.get(row["code"], {}).get("best_score", 0) >= 3)
    percent = int((completed / (total or 1)) * 100)
    return completed, total, percent


def _base_context() -> dict:
    return {
        "nav_items": [
            {"label": "Dashboard", "url": "/dashboard/"},
            {"label": "Lexicon", "url": "/vocabulary/lexicon/"},
            {"label": "Course Path", "url": "/course-path/"},
            {"label": "Lesson", "url": "/lesson/articles/"},
            {"label": "Profile", "url": "/profile/"},
        ],
    }


def _display_name(user, profile) -> str:
    full_name = f"{user.first_name} {user.last_name}".strip()
    if profile.prefers_full_name and full_name:
        return full_name
    return user.username


def _avatar_initials(user) -> str:
    first = (user.first_name or "").strip()
    last = (user.last_name or "").strip()
    if first and last:
        return f"{first[0]}{last[0]}".upper()
    if first:
        return first[:2].upper()
    username = (user.username or "").strip()
    if username:
        cleaned = username.replace(".", " ").replace("_", " ").strip()
        parts = [part for part in cleaned.split() if part]
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[1][0]}".upper()
        return cleaned[:2].upper()
    email = (user.email or "").strip()
    local = email.split("@", 1)[0] if "@" in email else email
    return (local[:2] or "U").upper()


def landing(request):
    context = _base_context()
    context.update(
        {
            "hero_title": "Learn Languages with Calm Focus",
            "hero_subtitle": "An editorial and structured way to build fluency through small, consistent sessions.",
            "levels": [
                {
                    "code": "A1",
                    "title": "Foundations",
                    "description": "Core structure, greetings, and everyday nouns.",
                    "status": "completed",
                    "progress": 100,
                },
                {
                    "code": "A1.1",
                    "title": "Articles & Patterns",
                    "description": "Der, die, das with practical sentence rhythm.",
                    "status": "in_progress",
                    "progress": 42,
                },
                {
                    "code": "A2",
                    "title": "Conversation",
                    "description": "Daily interactions and social settings.",
                    "status": "locked",
                    "progress": 0,
                },
            ],
        }
    )
    return render(request, "core/pages/landing.html", context)


def login_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            login(request, form.cleaned_data["user"])
            messages.success(request, "Welcome back.")
            return redirect("dashboard")
    else:
        form = LoginForm()

    context = _base_context()
    context.update({"page_title": "Sign In", "form": form})
    return render(request, "core/pages/login.html", context)


def register_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if getattr(settings, "INVITE_ONLY_SIGNUP", True):
        context = _base_context()
        context.update({"page_title": "Create Account", "invite_only": True})
        return render(request, "core/pages/register.html", context)

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect("dashboard")
    else:
        form = RegisterForm()

    context = _base_context()
    context.update({"page_title": "Create Account", "form": form})
    return render(request, "core/pages/register.html", context)


def invite_accept_page(request, token: str):
    if request.user.is_authenticated:
        return redirect("dashboard")

    invite = resolve_invite(token)
    if invite is None:
        context = _base_context()
        context.update({"page_title": "Invitation Invalid"})
        return render(request, "core/pages/invite_invalid.html", context, status=410)

    if request.method == "POST":
        form = InviteAcceptForm(request.POST, invite_email=invite.email)
        if form.is_valid():
            user = form.save()
            invite.mark_used()
            login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect("dashboard")
    else:
        form = InviteAcceptForm(invite_email=invite.email)

    context = _base_context()
    context.update({"page_title": "Accept Invitation", "form": form})
    return render(request, "core/pages/invite_accept.html", context)


@login_required
def dashboard(request):
    profile = UserProfile.objects.get(user=request.user)
    learned_count = UserWordProgress.objects.filter(
        user=request.user, status=UserWordProgress.STATUS_LEARNED
    ).count()
    total_words = LearningWord.objects.count() or 1
    progress_percent = min(100, int((learned_count / total_words) * 100))

    context = _base_context()
    context.update(
        {
            "page_title": "Dashboard",
            "user_name": _display_name(request.user, profile),
            "avatar_initials": _avatar_initials(request.user),
            "track_name": f"{profile.current_language} {profile.current_level}",
            "track_progress": progress_percent,
            "lessons": [
                {
                    "title": "Definite Articles",
                    "description": "Understanding der, die, das in context.",
                    "minutes": 12,
                    "status": "in_progress",
                },
                {
                    "title": "Common Nouns",
                    "description": "Practical nouns for home, work, and city.",
                    "minutes": 15,
                    "status": "next",
                },
                {
                    "title": "Article Drills",
                    "description": "Short exercises to reinforce patterns.",
                    "minutes": 10,
                    "status": "locked",
                },
            ],
            "milestones": [
                {"title": "10 day streak", "done": True},
                {"title": "A1 unit complete", "done": False},
                {"title": "50 vocabulary items", "done": False},
            ],
        }
    )
    return render(request, "core/pages/dashboard.html", context)


@login_required
def course_path(request):
    context = _base_context()
    context.update(
        {
            "page_title": "Course Path",
            "path_levels": [
                {
                    "code": "A1",
                    "title": "Foundations",
                    "description": "Pronouns, greetings, sentence basics.",
                    "status": "completed",
                    "progress": 100,
                    "lessons": 18,
                },
                {
                    "code": "A1.1",
                    "title": "Articles",
                    "description": "Article awareness and noun association.",
                    "status": "in_progress",
                    "progress": 42,
                    "lessons": 14,
                },
                {
                    "code": "A2",
                    "title": "Dialogue",
                    "description": "Conversational confidence in daily moments.",
                    "status": "locked",
                    "progress": 0,
                    "lessons": 20,
                },
            ],
        }
    )
    return render(request, "core/pages/course_path.html", context)


@login_required
def level_page(request):
    lessons = [
        {
            "title": "What Is a Definite Article?",
            "description": "Discover when to use der, die, and das.",
            "minutes": 12,
            "status": "completed",
            "url": "/lesson/articles/",
        },
        {
            "title": "Countries & Nationalities",
            "description": "Practice nation, nationality, and language with a clickable world map.",
            "minutes": 14,
            "status": "in_progress",
            "url": "/lesson/world/",
        },
        {
            "title": "Mini Assessment",
            "description": "A short check before moving forward.",
            "minutes": 8,
            "status": "locked",
            "url": "",
        },
    ]

    context = _base_context()
    context.update(
        {
            "page_title": "Level A1.1",
            "level_code": "A1.1",
            "level_title": "Articles & Global Vocabulary",
            "level_description": "Master noun articles and apply them to countries, nationalities, and languages.",
            "progress": 60,
            "lessons": lessons,
            "completed_lessons": sum(1 for lesson in lessons if lesson["status"] == "completed"),
        }
    )
    return render(request, "core/pages/level.html", context)


@login_required
def lesson_page(request):
    context = _base_context()
    context.update(
        {
            "page_title": "Lesson",
            "lesson_title": "Articles in Everyday Context",
            "lesson_intro": "Use structure and repetition to make article usage intuitive.",
            "dashboard_url": "/dashboard/",
            "lectures_url": "/level/a1-1/",
            "lectures_label": "A1.1 Lectures",
            "progress": 42,
            "sections": [
                {
                    "title": "Core Idea",
                    "body": "In German, every noun has a grammatical gender and article. Memorize article and noun together.",
                    "tip": "Say article+noun aloud as one unit.",
                },
                {
                    "title": "Examples",
                    "body": "Der Tisch, die Lampe, das Buch. Keep each pair visible in your notes.",
                    "tip": "Write 3 short sentences for each noun.",
                },
            ],
        }
    )
    return render(request, "core/pages/lesson.html", context)


@login_required
def world_module_page(request):
    requested_continent = (request.GET.get("continent", "") or "").strip().lower()
    requested_country = (request.GET.get("country", "") or "").strip().upper()

    if request.method == "POST":
        requested_continent = (request.POST.get("continent", "") or "").strip().lower()
        requested_country = (request.POST.get("country", "") or "").strip().upper()

    active_continent = WORLD_CONTINENTS_BY_SLUG.get(requested_continent, WORLD_CONTINENTS[0])
    continent_countries_by_code = {country["code"]: country for country in active_continent["countries"]}

    if requested_country and requested_country not in continent_countries_by_code:
        fallback_continent_slug = WORLD_COUNTRY_TO_CONTINENT.get(requested_country)
        if fallback_continent_slug:
            active_continent = WORLD_CONTINENTS_BY_SLUG[fallback_continent_slug]
            continent_countries_by_code = {country["code"]: country for country in active_continent["countries"]}

    active_country = continent_countries_by_code.get(requested_country) or active_continent["countries"][0]

    submitted_values = {"nation": "", "nationality": "", "language": ""}
    evaluation = {
        "submitted": False,
        "nation_correct": False,
        "nationality_correct": False,
        "language_correct": False,
        "score": 0,
    }

    if request.method == "POST":
        submitted_values = {
            "nation": (request.POST.get("nation", "") or "").strip(),
            "nationality": (request.POST.get("nationality", "") or "").strip(),
            "language": (request.POST.get("language", "") or "").strip(),
        }
        nation_correct = _world_answer_matches(submitted_values["nation"], active_country["nation_answers"])
        nationality_correct = _world_answer_matches(
            submitted_values["nationality"],
            active_country["nationality_answers"],
        )
        language_correct = _world_answer_matches(
            submitted_values["language"],
            active_country["language_answers"],
        )
        score = int(nation_correct) + int(nationality_correct) + int(language_correct)

        UserImprovement.objects.create(
            user=request.user,
            category=f"{WORLD_PROGRESS_CATEGORY_PREFIX}{active_country['code']}",
            score_delta=score,
            encrypted_note=(
                f"{active_continent['slug']}|{submitted_values['nation']}|"
                f"{submitted_values['nationality']}|{submitted_values['language']}"
            ),
        )

        evaluation = {
            "submitted": True,
            "nation_correct": nation_correct,
            "nationality_correct": nationality_correct,
            "language_correct": language_correct,
            "score": score,
        }
        if score == 3:
            messages.success(
                request,
                f"Excellent. {active_country['name']} has been marked as completed for this module.",
            )
        elif score == 0:
            messages.error(request, "No correct fields yet. Review the tip and try again.")
        else:
            messages.info(request, "Good progress. Refine and try again to complete all three fields.")

    progress = _world_progress_for_user(request.user)
    continent_tabs = []
    for continent in WORLD_CONTINENTS:
        completed, total, percent = _world_continent_metrics(continent, progress)
        continent_tabs.append(
            {
                "slug": continent["slug"],
                "label": continent["label"],
                "is_active": continent["slug"] == active_continent["slug"],
                "completed": completed,
                "total": total,
                "percent": percent,
            }
        )

    active_completed, active_total, active_percent = _world_continent_metrics(active_continent, progress)
    countries = []
    for country in active_continent["countries"]:
        country_progress = progress.get(country["code"], {})
        countries.append(
            {
                **country,
                "is_active": country["code"] == active_country["code"],
                "is_mastered": country_progress.get("best_score", 0) >= 3,
                "attempts": country_progress.get("attempts", 0),
                "last_score": country_progress.get("last_score", 0),
            }
        )
    mastered_codes = [country["code"] for country in countries if country["is_mastered"]]
    active_progress = progress.get(active_country["code"], {})

    completed_rows = []
    for country in active_continent["countries"]:
        country_progress = progress.get(country["code"], {})
        if country_progress.get("completed_at"):
            completed_rows.append(
                {
                    **country,
                    "completed_at": country_progress["completed_at"],
                }
            )
    completed_rows.sort(key=lambda row: row["completed_at"], reverse=True)
    recently_learned = completed_rows[:4]
    if len(recently_learned) < 4:
        existing_codes = {row["code"] for row in recently_learned}
        for country in active_continent["countries"]:
            if country["code"] in existing_codes:
                continue
            recently_learned.append(country)
            if len(recently_learned) == 4:
                break

    context = _base_context()
    context.update(
        {
            "page_title": "Countries & Nationalities",
            "active_continent": active_continent,
            "active_country": active_country,
            "continent_tabs": continent_tabs,
            "continent_progress_percent": active_percent,
            "continent_completed": active_completed,
            "continent_total": active_total,
            "countries": countries,
            "mastered_codes": mastered_codes,
            "active_country_attempts": active_progress.get("attempts", 0),
            "active_country_last_score": active_progress.get("last_score", 0),
            "submitted_values": submitted_values,
            "evaluation": evaluation,
            "recently_learned": recently_learned,
        }
    )
    return render(request, "core/pages/world_module.html", context)


@login_required
def vocabulary_lexicon_page(request):
    profile = UserProfile.objects.get(user=request.user)
    language = profile.current_language or "German"
    _ensure_user_progress_for_language(request.user, language)

    if request.method == "POST":
        term = (request.POST.get("term", "") or "").strip()
        translation = (request.POST.get("translation", "") or "").strip()
        if not term or not translation:
            messages.error(request, "Both term and translation are required.")
            return redirect("vocabulary_lexicon")

        article, word = _split_term(term)
        if not word:
            messages.error(request, "Please provide a valid word.")
            return redirect("vocabulary_lexicon")

        entry, _ = LearningWord.objects.get_or_create(
            language=language,
            article=article,
            word=word,
            defaults={"translation": translation, "difficulty": 2},
        )
        _, created_progress = UserWordProgress.objects.get_or_create(user=request.user, word=entry)
        if created_progress:
            messages.success(request, "Word added to your lexicon.")
        else:
            messages.info(request, "This term already exists in your lexicon.")
        return redirect("vocabulary_lexicon")

    search_query = (request.GET.get("q", "") or "").strip()
    current_letter = (request.GET.get("letter", "ALL") or "ALL").upper()
    if current_letter != "ALL" and current_letter not in string.ascii_uppercase:
        current_letter = "ALL"

    all_words_qs = UserWordProgress.objects.filter(user=request.user, word__language=language).select_related("word")
    if search_query:
        all_words_qs = all_words_qs.filter(
            Q(word__word__icontains=search_query)
            | Q(word__translation__icontains=search_query)
            | Q(word__article__icontains=search_query)
        )

    available_letters = set()
    for progress in all_words_qs:
        initial = (progress.word.word[:1] or "").upper()
        if initial in string.ascii_uppercase:
            available_letters.add(initial)

    filtered_qs = all_words_qs
    if current_letter != "ALL":
        filtered_qs = filtered_qs.filter(word__word__istartswith=current_letter)

    grouped = {}
    for progress in filtered_qs.order_by("word__word"):
        word = progress.word
        letter = (word.word[:1] or "#").upper()
        grouped.setdefault(letter, []).append(
            {
                "id": word.id,
                "display_word": _word_display(word),
                "translation": word.translation,
            }
        )

    grouped_words = [{"letter": letter, "items": items} for letter, items in sorted(grouped.items())]

    total_words = UserWordProgress.objects.filter(user=request.user, word__language=language).count()
    learned_count = UserWordProgress.objects.filter(
        user=request.user,
        status=UserWordProgress.STATUS_LEARNED,
        word__language=language,
    ).count()
    mastery_percent = min(100, int((learned_count / (total_words or 1)) * 100))

    context = _base_context()
    context.update(
        {
            "page_title": "My Lexicon",
            "word_count": total_words,
            "filtered_count": filtered_qs.count(),
            "search_query": search_query,
            "current_letter": current_letter,
            "alphabet": ["ALL", *string.ascii_uppercase],
            "available_letters": available_letters,
            "grouped_words": grouped_words,
            "daily_streak": profile.streak_days or 0,
            "mastery_percent": mastery_percent,
            "target_language": "EN",
        }
    )
    return render(request, "core/pages/vocabulary_lexicon.html", context)


@login_required
def vocabulary_test_page(request):
    profile = UserProfile.objects.get(user=request.user)
    language = profile.current_language or "German"
    rows = _practice_rows(request.user, language)
    submitted_rows = []
    score = 0
    max_score = 0
    submitted = False
    completed_count = 0

    if request.method == "POST":
        submitted = True
        word_ids = [int(raw_id) for raw_id in request.POST.getlist("word_id") if raw_id.isdigit()]
        row_map = {row["id"]: row for row in rows}
        ordered_rows = [row_map[word_id] for word_id in word_ids if word_id in row_map]

        for row in ordered_rows:
            selected_type = (request.POST.get(f"type_{row['id']}", "") or "").strip().lower()
            submitted_translation = (request.POST.get(f"translation_{row['id']}", "") or "").strip()
            if selected_type or submitted_translation:
                completed_count += 1

            type_correct = selected_type == row["expected_type"]
            translation_correct = _translation_matches(row["translation"], submitted_translation)
            row_score = int(type_correct) + int(translation_correct)
            score += row_score
            max_score += 2

            _update_word_progress(request.user, row["word"], row_score, max_score=2)
            submitted_rows.append(
                {
                    **row,
                    "selected_type": selected_type,
                    "submitted_translation": submitted_translation,
                    "type_correct": type_correct,
                    "translation_correct": translation_correct,
                }
            )
    else:
        submitted_rows = [
            {
                **row,
                "selected_type": "",
                "submitted_translation": "",
                "type_correct": False,
                "translation_correct": False,
            }
            for row in rows
        ]

    percent = int((score / (max_score or 1)) * 100) if submitted else 0

    context = _base_context()
    context.update(
        {
            "page_title": "Vocabulary Test",
            "test_rows": submitted_rows,
            "word_type_choices": WORD_TYPE_CHOICES,
            "submitted": submitted,
            "score": score,
            "max_score": max_score or (len(rows) * 2),
            "score_percent": percent,
            "completed_count": completed_count if submitted else 0,
            "total_items": len(rows),
        }
    )
    return render(request, "core/pages/vocabulary_test.html", context)


@login_required
def spelling_test_page(request):
    profile = UserProfile.objects.get(user=request.user)
    language = profile.current_language or "German"
    rows = _practice_rows(request.user, language)

    submitted_rows = []
    score = 0
    max_score = 0
    submitted = False
    draft_saved = False
    completed_count = 0

    if request.method == "POST":
        action = (request.POST.get("action", "submit") or "submit").lower()
        draft_saved = action == "save"
        submitted = not draft_saved

        word_ids = [int(raw_id) for raw_id in request.POST.getlist("word_id") if raw_id.isdigit()]
        row_map = {row["id"]: row for row in rows}
        ordered_rows = [row_map[word_id] for word_id in word_ids if word_id in row_map]

        for row in ordered_rows:
            transcription = (request.POST.get(f"transcription_{row['id']}", "") or "").strip()
            selected_type = (request.POST.get(f"type_{row['id']}", "") or "").strip().lower()
            submitted_translation = (request.POST.get(f"translation_{row['id']}", "") or "").strip()
            if transcription or selected_type or submitted_translation:
                completed_count += 1

            expected_full = _normalize_text(row["display_word"])
            expected_word_only = _normalize_text(row["word"].word)
            transcription_normalized = _normalize_text(transcription)
            spelling_correct = bool(transcription_normalized) and transcription_normalized in {
                expected_full,
                expected_word_only,
            }
            type_correct = selected_type == row["expected_type"]
            translation_correct = _translation_matches(row["translation"], submitted_translation)
            row_score = int(spelling_correct) + int(type_correct) + int(translation_correct)

            if submitted:
                score += row_score
                max_score += 3
                _update_word_progress(request.user, row["word"], row_score, max_score=3)

            submitted_rows.append(
                {
                    **row,
                    "transcription": transcription,
                    "selected_type": selected_type,
                    "submitted_translation": submitted_translation,
                    "spelling_correct": spelling_correct,
                    "type_correct": type_correct,
                    "translation_correct": translation_correct,
                }
            )

        if draft_saved:
            messages.success(request, "Draft saved.")
    else:
        submitted_rows = [
            {
                **row,
                "transcription": "",
                "selected_type": "",
                "submitted_translation": "",
                "spelling_correct": False,
                "type_correct": False,
                "translation_correct": False,
            }
            for row in rows
        ]

    percent = int((score / (max_score or 1)) * 100) if submitted else 0

    context = _base_context()
    context.update(
        {
            "page_title": "Spelling Test",
            "test_rows": submitted_rows,
            "word_type_choices": WORD_TYPE_CHOICES,
            "submitted": submitted,
            "draft_saved": draft_saved,
            "score": score,
            "max_score": max_score or (len(rows) * 3),
            "score_percent": percent,
            "completed_count": completed_count,
            "total_items": len(rows),
        }
    )
    return render(request, "core/pages/spelling_test.html", context)


@login_required
def profile_page(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    improvement_total = UserImprovement.objects.filter(user=request.user).count()

    if request.method == "POST":
        llm_form = ProfileLLMSettingsForm(
            request.POST,
            has_existing_key=bool(profile.llm_api_key),
        )
        if llm_form.is_valid():
            profile.llm_model = llm_form.cleaned_data["llm_model"]
            update_fields = ["llm_model"]
            if llm_form.cleaned_data["api_key"]:
                profile.llm_api_key = llm_form.cleaned_data["api_key"]
                update_fields.append("llm_api_key")
            profile.save(update_fields=update_fields)
            messages.success(request, "AI settings updated.")
            return redirect("profile")
    else:
        llm_form = ProfileLLMSettingsForm(
            initial={"llm_model": profile.llm_model},
            has_existing_key=bool(profile.llm_api_key),
        )

    context = _base_context()
    context.update(
        {
            "page_title": "Profile",
            "llm_form": llm_form,
            "has_llm_api_key": bool(profile.llm_api_key),
            "profile": {
                "name": _display_name(request.user, profile),
                "avatar_initials": _avatar_initials(request.user),
                "language": profile.current_language,
                "level": profile.current_level,
                "weekly_goal": profile.weekly_goal,
                "streak": profile.streak_days,
                "progress": min(100, 20 + improvement_total * 5),
            }
        }
    )
    return render(request, "core/pages/profile.html", context)


def llm_chat_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    prompt = (payload.get("prompt") or "").strip()
    system_prompt = (payload.get("system_prompt") or "").strip()
    provided_messages = payload.get("messages") or []

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if prompt:
        messages.append({"role": "user", "content": prompt})
    elif isinstance(provided_messages, list):
        for item in provided_messages:
            if not isinstance(item, dict):
                continue
            role = (item.get("role") or "").strip().lower()
            content = (item.get("content") or "").strip()
            if role in {"system", "user", "assistant"} and content:
                messages.append({"role": role, "content": content})

    if not messages:
        return JsonResponse(
            {"error": "Provide either 'prompt' or a non-empty 'messages' list."},
            status=400,
        )

    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    provider = (payload.get("provider") or "openai").strip().lower()
    model = (payload.get("model") or getattr(settings, "OPENAI_DEFAULT_MODEL", "gpt-4.1-mini")).strip()
    temperature = float(payload.get("temperature", 0.7))
    max_tokens = int(payload.get("max_tokens", 500))

    api_key = ""
    if provider == "openai":
        api_key = (profile.llm_api_key or "").strip() or (getattr(settings, "OPENAI_API_KEY", "") or "").strip()

    try:
        result = generate_llm_response(
            provider=provider,
            api_key=api_key,
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            openai_api_base=getattr(settings, "OPENAI_API_BASE", "https://api.openai.com/v1"),
        )
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid 'temperature' or 'max_tokens' value."}, status=400)
    except LLMServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=exc.status_code)

    return JsonResponse(result, status=200)


@login_required
def logout_page(request):
    logout(request)
    messages.info(request, "Signed out successfully.")
    return redirect("landing")


def admin_login_page(request):
    if request.method == "POST":
        form = AdminAccessRequestForm(request.POST)
        if not form.is_valid():
            context = _base_context()
            context.update({
                "page_title": "Admin Login",
                "form": form,
            })
            return render(request, "core/pages/admin_login.html", context, status=400)

        configured_totp_secret = getattr(settings, "ADMIN_ACCESS_TOTP_SECRET", "").strip()
        submitted_request_code = form.cleaned_data["access_code"]
        if not configured_totp_secret:
            messages.error(request, "ADMIN_ACCESS_TOTP_SECRET is not configured.")
            return redirect("admin_login")

        totp_window = max(0, int(getattr(settings, "ADMIN_ACCESS_TOTP_WINDOW", 1)))
        if not verify_totp_code(
            configured_totp_secret,
            submitted_request_code,
            window=totp_window,
        ):
            messages.error(request, "Invalid authentication code.")
            return redirect("admin_login")

        admin_email = getattr(settings, "ADMIN_ACCESS_EMAIL", "enricosaccon96@gmail.com").strip().lower()
        if not getattr(settings, "ADMIN_PANEL_PASSWORD", ""):
            messages.error(request, "ADMIN_PANEL_PASSWORD is not configured.")
            return redirect("admin_login")
        try:
            _token, raw_token = issue_admin_access_token(admin_email)
            access_url = build_admin_access_url(raw_token)
            send_admin_access_email(recipient_email=admin_email, access_url=access_url)
        except Exception as exc:
            messages.error(request, f"Could not send admin link: {exc}")
        else:
            messages.success(request, "Admin access link sent.")
        return redirect("admin_login")

    form = AdminAccessRequestForm()
    context = _base_context()
    context.update({
        "page_title": "Admin Login",
        "form": form,
    })
    return render(request, "core/pages/admin_login.html", context)


def admin_logout_page(request):
    if request.method == "POST":
        request.session.pop("admin_panel_ok", None)
        request.session.pop("admin_pending_token_id", None)
        messages.info(request, "Admin session ended.")
        return redirect("admin_login")
    return redirect("admin_panel")


def admin_panel_page(request):
    if request.session.get("admin_panel_ok"):
        users = get_user_model().objects.order_by("id").values(
            "id", "username", "email", "first_name", "last_name", "is_staff", "is_superuser"
        )
        context = _base_context()
        context.update({"page_title": "Admin", "users": users, "admin_unlocked": True})
        return render(request, "core/pages/admin_panel.html", context)

    if request.method == "GET" and request.GET.get("access_token"):
        token = resolve_admin_access_token(request.GET.get("access_token", ""))
        if token is None:
            context = _base_context()
            context.update({"page_title": "Admin", "invalid_token": True})
            return render(request, "core/pages/admin_panel.html", context, status=410)
        request.session["admin_pending_token_id"] = token.id

    pending_token_id = request.session.get("admin_pending_token_id")
    if not pending_token_id:
        messages.info(request, "Request a one-time link first.")
        return redirect("admin_login")

    token = (
        resolve_admin_access_token(request.GET.get("access_token", ""))
        if request.method == "GET" and request.GET.get("access_token")
        else None
    )
    if token is None:
        from .models import AdminAccessToken

        token = AdminAccessToken.objects.filter(id=pending_token_id).first()
        if token is None or not token.is_active:
            request.session.pop("admin_pending_token_id", None)
            context = _base_context()
            context.update({"page_title": "Admin", "invalid_token": True})
            return render(request, "core/pages/admin_panel.html", context, status=410)

    if request.method == "POST":
        form = AdminPanelPasswordForm(request.POST)
        if form.is_valid():
            configured_password = getattr(settings, "ADMIN_PANEL_PASSWORD", "")
            submitted_password = form.cleaned_data["password"]
            if not configured_password:
                form.add_error("password", "Admin password is not configured.")
                context = _base_context()
                context.update({"page_title": "Admin", "form": form, "admin_unlocked": False})
                return render(request, "core/pages/admin_panel.html", context)
            if configured_password and secrets.compare_digest(submitted_password, configured_password):
                token.mark_used()
                request.session["admin_panel_ok"] = True
                request.session.pop("admin_pending_token_id", None)
                return redirect("admin_panel")
            form.add_error("password", "Invalid admin password.")
    else:
        form = AdminPanelPasswordForm()

    context = _base_context()
    context.update({"page_title": "Admin", "form": form, "admin_unlocked": False})
    return render(request, "core/pages/admin_panel.html", context)
