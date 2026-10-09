# Soma Link: Technical Specification and Delivery Plan

**Status:** Product and engineering baseline  
**Audience:** Product, curriculum, design, engineering, QA, operations, and school partners  
**Product:** Soma Link, a Kenyan CBE learning and academic-contest platform for Grades 4–12

## 1. Product Definition

Soma Link connects curriculum-aligned learning, teacher-led assessment, learner progress tracking, parent visibility, and competitive academic practice. The platform serves individual learners and institutions, with the same curriculum, identity, assessment, and payment records available across role-specific portals.

### Product principles

- Curriculum mapping is versioned and reviewable; subject names and outcomes are not hard-coded into contest logic.
- Teachers remain the source of truth for continuous assessment. Automated contest results are evidence, not a replacement for teacher judgment.
- Contest scoring is deterministic, server-authoritative, auditable, and fair across supported devices and connection quality.
- Minors' data is private by default. A learner's school, parent, and teachers see only the records needed for their roles.
- Paid access is granted only after a verified payment or valid institutional entitlement. Repeated callbacks must never create duplicate charges or benefits.
- Color communicates status but never carries meaning by itself; text, icons, and accessible contrast are required.

## 2. Executive Architecture

### Logical components

1. **Web client:** Next.js App Router, React, TypeScript, Tailwind CSS, and a shared design-token package. Server-render public pages and curriculum discovery; use client components for the contest arena and scorebook interactions. Put authenticated API access behind a same-origin backend-for-frontend where practical.
2. **Application API:** Django REST Framework, split into bounded Django apps: `accounts`, `curriculum`, `learning`, `assessment`, `contests`, `billing`, `notifications`, and `schools`. Version REST endpoints under `/api/v1/`.
3. **Realtime:** Django Channels on Django's ASGI application with `channels_redis` and a Redis channel layer. Use Daphne or another ASGI-capable server for HTTP and WebSocket traffic. Channels WebSockets must not be routed through a WSGI-only server.
4. **Background work:** Celery workers and Celery Beat, backed by Redis or RabbitMQ, for contest scheduling, result aggregation, certificate generation, payment reconciliation, reminders, and media processing. HTTP requests and WebSocket consumers enqueue work; workers do not own authoritative contest state.
5. **Data:** PostgreSQL as the system of record, with PostGIS for mapwork geometry and spatial questions. Redis is ephemeral coordination/cache/presence only, not the only copy of scores, payments, or contest submissions.
6. **Media:** Store original video and documents in S3-compatible object storage or Cloudinary. Use a managed video pipeline (for example, Cloudinary, Mux, or Cloudflare Stream) to transcode to adaptive HLS/DASH, deliver through a CDN, and issue short-lived signed playback URLs. Do not proxy video bytes through Django.
7. **Payments:** A provider adapter layer for Safaricom Daraja STK Push, Paystack, Flutterwave, and school vouchers. Persist every request, callback, state transition, and reconciliation result in an append-only audit trail.
8. **Operations:** Containerized web, worker, scheduler, Redis, and database services; centralized logs, error reporting, metrics, traces, backups, and alerting. Use the deployment platform for process supervision; run the local demo HTTP service with Django's development server.

### Async ORM and WSGI safety

Django REST views, Django Channels consumers, and WSGI handlers have different execution models. Keep the following boundary explicit:

- In synchronous DRF/Django views hosted by a WSGI server, use the synchronous ORM normally. Do not call `asyncio.run()` from a request handler or wrap ordinary synchronous view work in an event loop.
- In async Django views and Channels `AsyncConsumer`/`AsyncJsonWebsocketConsumer` methods, use Django's async ORM methods (`aget`, `acreate`, `aupdate`, async iteration) where supported. Never evaluate a lazy `QuerySet`, follow a lazy relation, or call a synchronous ORM method directly on the event-loop thread.
- For ORM operations that need a synchronous transaction or are not supported by the async ORM, put the *whole database unit of work* in a synchronous service function and call it with `channels.db.database_sync_to_async`. This adapter also manages old database connections. Without Channels, use `asgiref.sync.sync_to_async` with `thread_sensitive=True` for a synchronous database function.
- Return materialized values (IDs, dictionaries, immutable DTOs) from the sync boundary. Do not return a lazy `QuerySet` or model relation for later evaluation in async code. Keep `transaction.atomic()` and every query it governs inside the same synchronous service function.
- REST and WebSocket paths must call the same domain service for contest eligibility, answer validation, scoring, and payment entitlements; transport handlers must not implement their own ORM/scoring logic.
- Test async code using async clients/consumers and assert that no `SynchronousOnlyOperation` occurs under ASGI. Also test transaction rollback, duplicate answer idempotency, and connection cleanup.

Example Channels boundary for a transactional answer submission:

```python
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class ContestConsumer(AsyncJsonWebsocketConsumer):
    async def receive_json(self, content, **kwargs):
        result = await record_answer(
            attempt_id=self.attempt_id,
            item_id=content["item_id"],
            answer=content["answer"],
        )
        await self.send_json({"type": "answer.ack", **result})


@database_sync_to_async
def record_answer(*, attempt_id, item_id, answer):
    # Load, authorize, validate deadline, and persist inside one transaction.
    # Return a plain dict; do not return a lazy model/queryset.
    ...
```

Keep synchronous Django views behind a WSGI server and Channels WebSockets on an ASGI server. Do not mount the Channels application inside a WSGI container or expect a WSGI server to support WebSockets.

### Contest event flow

1. An authorized scheduler or teacher publishes a contest. The contest definition, questions, rubric/scoring version, start/end times, and audience are persisted in PostgreSQL.
2. At the scheduled start, Celery/Beat changes the contest state and emits a domain event. The ASGI service broadcasts `contest.started` to the contest's authorized Channels group.
3. A learner joins after server-side eligibility checks. The server creates or resumes a single attempt, assigns that learner a randomized question order, and returns only the current question payload and server-issued deadline.
4. Answers are accepted by an authenticated WebSocket command or REST fallback. The server validates attempt ownership, question assignment, attempt state, and deadline, then writes the answer transactionally. The client timer is display-only.
5. The server calculates marks using a versioned scoring rule. Celery can aggregate larger leaderboards; small live deltas can be broadcast after the committed transaction. Redis may hold short-lived presence and leaderboard cache entries, which can be rebuilt from PostgreSQL.
6. At close, the server rejects late answers, finalizes attempts idempotently, resolves ties using the published tie-break policy, stores final ranks, awards points/badges, and queues certificates.

### Video and live contest separation

Video is asynchronous learning media delivered by a media service and CDN. Contest WebSockets carry small state messages only: contest state, current question, remaining server time, participant count, rank changes, and result summaries. Do not send video or large question-bank payloads through Channels. Offer an HTTP polling fallback for schools with restrictive networks.

### Payment flow

1. The client requests a checkout for a product or contest entry. The API checks price, currency, learner/school eligibility, and idempotency key, then creates a `Payment` in `PENDING` state.
2. For M-Pesa, the backend makes the Daraja STK Push request and records the request/correlation identifiers. It returns a pending response; it does not activate access based only on the browser redirect or STK initiation response.
3. Safaricom calls the configured callback URL. The API validates the expected callback shape and correlation IDs, stores the callback event before processing, deduplicates it, and verifies amount, account reference, phone, and result code against the pending payment.
4. A successful, verified payment transitions once to `SUCCEEDED`; a transaction then grants or renews the subscription entitlement. A failure transitions to `FAILED` without granting access. Unknown or contradictory callbacks go to a reconciliation queue.
5. Paystack and Flutterwave use provider-specific signed webhook verification with the raw request body. School voucher redemption is an atomic one-time transaction with expiry, scope, and redemption limits.
6. A scheduled reconciliation task checks provider status for unresolved transactions. Never log secrets, full card details, or unnecessary learner data.

### Deployment shape

```text
Browser / mobile web
  -> CDN + Next.js web
  -> Django REST API (ASGI) <-> PostgreSQL + PostGIS
        |                    <-> Redis (Channels, cache, presence)
        |                    <-> Object storage / video CDN
        |                    <-> Daraja / Paystack / Flutterwave
        -> Celery workers + Beat (email/SMS, grading, reconciliation, certificates)
```

## 3. Brand and Four-Color UI System

Define tokens centrally and expose them as CSS variables and Tailwind theme values. Use a neutral surface/text palette in addition to the four semantic brand colors.

| Token | Value | Primary meaning | Usage |
|---|---|---|---|
| `soma-green` | `#22C55E` | EE; top rank/victory; active paid entitlement; performance at or above the EE threshold | Positive result, paid badge, victory state, progress above 80% |
| `soma-yellow` | `#EAB308` | ME; live/in-progress state; medium difficulty; pending payment | Live contest indicator, pending invoice, medium task label, 60–79% performance |
| `soma-orange` | `#F97316` | AE; revision needed; leaderboard warning zone; expiring entitlement | Attention/revision state, expiring pass, 40–59% performance |
| `soma-blue` | `#3B82F6` | BE/foundation support; navigation; primary action; video controls | Primary CTA, navigation selection, foundation-level result below 40% |

### Semantic rules

- Default percentage bands: EE `>=80`, ME `>=60 and <80`, AE `>=40 and <60`, BE `<40`. Store the assessment's rubric version and threshold policy with each score; allow curriculum leads to configure a subject/grade rubric. Do not assume a raw percentage alone measures competency.
- Blue has two roles (BE and general navigation/actions). Separate them with explicit labels (`Foundation`, `Continue`), iconography, and component context; never present an unlabeled blue chip as a performance result.
- Yellow is similarly shared by ME, live state, and pending billing. Pair with text and distinct icons/shapes so status is unambiguous.
- Maintain WCAG 2.2 AA contrast for text and controls. Brand colors are not guaranteed to meet contrast for white text; use dark text on yellow and test every foreground/background pair.
- Use color plus text/icon/pattern for status and charts. Provide keyboard focus, reduced-motion behavior, screen-reader announcements for leaderboard changes, and non-color cues on maps/charts.

## 4. Curriculum and CBE Competency Model

Represent curriculum as versioned data rather than page conditionals. Suggested hierarchy:

```text
CurriculumVersion -> Grade/Stage -> Pathway (optional) -> Subject
  -> Strand -> Sub-strand -> LearningOutcome -> RubricDescriptor
```

Cover Grades 4–6 upper primary, Grades 7–9 junior secondary, and Grades 10–12 senior secondary. Seed the subject catalog from the current approved KICD curriculum for each grade/stage. Typical learning areas include Mathematics, English, Kiswahili/KSL where applicable, Integrated Science/Science and Technology, Social Studies, Agriculture, Pre-Technical Studies, Business Studies, Religious Education, Creative Arts/Sports, and other approved learning areas. Senior secondary subjects must be attached to an approved STEM, Social Sciences, or Arts and Sports Science pathway. Curriculum officers must approve and version imports; this specification does not replace the current official KICD subject list.

A competency score records learner, outcome, assessment, assessor, score/evidence, rubric level, rubric version, and assessment date. Map percentages into EE/ME/AE/BE only where a percentage assessment is valid. Preserve qualitative teacher evidence and moderation history. Contest scores are separately recorded and can be linked as evidence, but do not silently overwrite SBA/teacher-entered scores.

## 5. Data Model

Use UUID primary keys for public-facing entities, UTC timestamps, explicit school/tenant scoping, and database constraints for idempotency and uniqueness. The snippets below are reference Django models; indexes and constraints are part of the specification. Store Kenyan phone numbers normalized to E.164. Financial values use integer minor units or `Decimal`, never binary floats.

### Core Django model reference

```python
import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.gis.db import models as gis_models
from django.db import models


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"
        PARENT = "parent", "Parent"
        SCHOOL_ADMIN = "school_admin", "School Admin"
        PLATFORM_ADMIN = "platform_admin", "Platform Admin"
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    phone_e164 = models.CharField(max_length=16, blank=True)
    # Keep Django's username for compatibility; authenticate via verified email.


class School(UUIDModel):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=40, unique=True)
    county_code = models.CharField(max_length=20, db_index=True)
    timezone = models.CharField(max_length=40, default="Africa/Nairobi")
    is_active = models.BooleanField(default=True)


class SchoolMembership(UUIDModel):
    school = models.ForeignKey(School, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    role = models.CharField(max_length=20)
    grade = models.PositiveSmallIntegerField(null=True, blank=True)
    class_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["school", "user", "role"], name="uniq_school_user_role")]
        indexes = [models.Index(fields=["school", "grade", "class_name"])]


class CurriculumVersion(UUIDModel):
    name = models.CharField(max_length=120)
    source = models.CharField(max_length=120)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_published = models.BooleanField(default=False)


class Subject(UUIDModel):
    curriculum = models.ForeignKey(CurriculumVersion, on_delete=models.PROTECT)
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=160)
    stage = models.CharField(max_length=30)  # upper_primary, junior_secondary, senior_secondary
    grade_min = models.PositiveSmallIntegerField()
    grade_max = models.PositiveSmallIntegerField()
    pathway = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["curriculum", "code", "grade_min", "grade_max", "pathway"], name="uniq_curriculum_subject_scope")]


class Strand(UUIDModel):
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="strands")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT)
    code = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["subject", "code"], name="uniq_subject_strand_code")]


class LearningOutcome(UUIDModel):
    strand = models.ForeignKey(Strand, on_delete=models.PROTECT, related_name="outcomes")
    code = models.CharField(max_length=60)
    statement = models.TextField()
    grade = models.PositiveSmallIntegerField()
    class Meta:
        constraints = [models.UniqueConstraint(fields=["strand", "code", "grade"], name="uniq_strand_outcome_grade")]


class Assessment(UUIDModel):
    school = models.ForeignKey(School, on_delete=models.PROTECT)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=30)  # SBA, assignment, practical, contest_evidence
    rubric_version = models.CharField(max_length=40)
    assessed_at = models.DateTimeField()
    is_published = models.BooleanField(default=False)


class CompetencyScore(UUIDModel):
    assessment = models.ForeignKey(Assessment, on_delete=models.PROTECT)
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="competency_scores")
    outcome = models.ForeignKey(LearningOutcome, on_delete=models.PROTECT)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="scores_entered")
    score_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    rubric_level = models.CharField(max_length=2, choices=[("EE", "Exceeding"), ("ME", "Meeting"), ("AE", "Approaching"), ("BE", "Below")])
    evidence = models.JSONField(default=dict, blank=True)
    teacher_comment = models.TextField(blank=True)
    revision = models.PositiveIntegerField(default=1)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["assessment", "learner", "outcome"], name="uniq_assessment_learner_outcome")]
        indexes = [models.Index(fields=["learner", "outcome", "created_at"])]


class Question(UUIDModel):
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    outcome = models.ForeignKey(LearningOutcome, on_delete=models.PROTECT)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    prompt = models.JSONField()  # sanitized rich text / media references, never executable HTML
    answer_spec = models.JSONField()  # private server-side scoring key
    question_type = models.CharField(max_length=30)
    difficulty = models.CharField(max_length=20)
    marks = models.PositiveSmallIntegerField(default=1)
    is_approved = models.BooleanField(default=False)


class Contest(UUIDModel):
    class Mode(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        CLASS_CHALLENGE = "class_challenge", "Class Challenge"
        PRACTICE = "practice", "Practice"
    title = models.CharField(max_length=200)
    mode = models.CharField(max_length=24, choices=Mode.choices)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    grade_min = models.PositiveSmallIntegerField()
    grade_max = models.PositiveSmallIntegerField()
    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField()
    state = models.CharField(max_length=20, db_index=True)  # draft, scheduled, live, closed, finalized
    scoring_version = models.CharField(max_length=40)
    access_product = models.ForeignKey("SubscriptionProduct", null=True, blank=True, on_delete=models.PROTECT)
    class Meta:
        indexes = [models.Index(fields=["state", "starts_at"]), models.Index(fields=["subject", "grade_min", "grade_max"])]


class ContestItem(UUIDModel):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name="items")
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    position = models.PositiveSmallIntegerField()
    points = models.PositiveSmallIntegerField()
    seconds_allowed = models.PositiveSmallIntegerField()
    class Meta:
        constraints = [models.UniqueConstraint(fields=["contest", "position"], name="uniq_contest_item_position")]


class ContestAttempt(UUIDModel):
    contest = models.ForeignKey(Contest, on_delete=models.PROTECT)
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    started_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    state = models.CharField(max_length=20, db_index=True)
    score = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    question_order = models.JSONField(default=list)  # per-attempt randomized item IDs
    integrity_events = models.JSONField(default=list, blank=True)  # minimized, reviewable signals
    class Meta:
        constraints = [models.UniqueConstraint(fields=["contest", "learner"], name="uniq_contest_learner_attempt")]
        indexes = [models.Index(fields=["contest", "state", "score"])]


class ContestAnswer(UUIDModel):
    attempt = models.ForeignKey(ContestAttempt, on_delete=models.CASCADE, related_name="answers")
    item = models.ForeignKey(ContestItem, on_delete=models.PROTECT)
    answer = models.JSONField()
    is_correct = models.BooleanField(null=True)  # private; do not expose during a live contest
    awarded_points = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    received_at = models.DateTimeField()
    class Meta:
        constraints = [models.UniqueConstraint(fields=["attempt", "item"], name="uniq_attempt_item_answer")]


class LeaderboardEntry(UUIDModel):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    school = models.ForeignKey(School, null=True, on_delete=models.PROTECT)
    county_code = models.CharField(max_length=20, blank=True)
    grade = models.PositiveSmallIntegerField()
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    score = models.DecimalField(max_digits=9, decimal_places=2)
    duration_ms = models.PositiveIntegerField()
    rank = models.PositiveIntegerField(null=True)
    scope_type = models.CharField(max_length=20)  # national, county, school, grade, subject
    scope_key = models.CharField(max_length=100)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["contest", "learner", "scope_type", "scope_key"], name="uniq_contest_leaderboard_scope")]
        indexes = [models.Index(fields=["contest", "scope_type", "scope_key", "rank"])]


class SubscriptionProduct(UUIDModel):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=30)  # subject, grade, contest, institution
    subject = models.ForeignKey(Subject, null=True, blank=True, on_delete=models.PROTECT)
    grade = models.PositiveSmallIntegerField(null=True, blank=True)
    duration_days = models.PositiveSmallIntegerField(null=True, blank=True)
    price_minor = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3, default="KES")
    is_active = models.BooleanField(default=True)
    entitlements = models.JSONField(default=dict)


class Subscription(UUIDModel):
    product = models.ForeignKey(SubscriptionProduct, on_delete=models.PROTECT)
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, db_index=True)  # pending, active, expired, cancelled
    source_payment = models.ForeignKey("Payment", null=True, blank=True, on_delete=models.PROTECT)


class Payment(UUIDModel):
    payer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    product = models.ForeignKey(SubscriptionProduct, on_delete=models.PROTECT)
    subscription = models.ForeignKey(Subscription, null=True, blank=True, on_delete=models.PROTECT)
    provider = models.CharField(max_length=20)  # mpesa, paystack, flutterwave, voucher
    provider_reference = models.CharField(max_length=120, blank=True)
    idempotency_key = models.CharField(max_length=100)
    amount_minor = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3, default="KES")
    status = models.CharField(max_length=20, db_index=True)
    phone_e164 = models.CharField(max_length=16, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["payer", "idempotency_key"], name="uniq_payer_payment_idempotency")]
        indexes = [models.Index(fields=["provider", "provider_reference"]), models.Index(fields=["status", "created_at"])]


class PaymentEvent(UUIDModel):
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="events")
    provider_event_id = models.CharField(max_length=160, unique=True)
    event_type = models.CharField(max_length=60)
    payload_hash = models.CharField(max_length=64)
    received_at = models.DateTimeField()
    processed_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=30)


class Voucher(UUIDModel):
    code_hash = models.CharField(max_length=64, unique=True)  # store hash, show plaintext only once at issuance
    product = models.ForeignKey(SubscriptionProduct, on_delete=models.PROTECT)
    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.PROTECT)
    expires_at = models.DateTimeField(null=True, blank=True)
    redeemed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    redeemed_at = models.DateTimeField(null=True, blank=True)


class PointsLedger(UUIDModel):
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    points_delta = models.IntegerField()
    reason = models.CharField(max_length=40)
    source_id = models.UUIDField()
    idempotency_key = models.CharField(max_length=120, unique=True)


class Badge(UUIDModel):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=240)
    criteria = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)


class LearnerBadge(UUIDModel):
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    badge = models.ForeignKey(Badge, on_delete=models.PROTECT)
    contest = models.ForeignKey(Contest, null=True, blank=True, on_delete=models.PROTECT)
    awarded_at = models.DateTimeField()
    class Meta:
        constraints = [models.UniqueConstraint(fields=["learner", "badge", "contest"], name="uniq_learner_badge_contest")]


class MapworkFeature(UUIDModel):
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    outcome = models.ForeignKey(LearningOutcome, on_delete=models.PROTECT)
    geometry = gis_models.GeometryField(srid=4326)
    properties = models.JSONField(default=dict)
```

### Schema notes and integrity rules

- Add an `AUTH_USER_MODEL` setting before the first migration. User roles are authorization hints, not sufficient authorization by themselves; enforce school membership and object-level access on every query.
- Add a `ParentLearnerLink` table with verified relationship, consent/status, and effective dates. A parent may link to multiple learners; a learner may have multiple authorized guardians.
- `ContestAttempt` is unique per contest/learner unless the contest explicitly allows retries; if retries are enabled, include an attempt number in the uniqueness constraint and publish the retry rule.
- `ContestAnswer` writes are idempotent per attempt/item. Use a transaction and lock the attempt row during final submission. Keep answer keys and correctness flags server-side until contest close.
- For multi-school leaderboard visibility, derive scope from a verified active membership. Do not trust a client-provided school or county filter without authorization checks.
- Prefer normalized payment state transitions and immutable `PaymentEvent` rows. Grant entitlements in the same database transaction as marking a payment successful; dispatch notifications after commit.
- Store uploaded media separately; database records hold object keys, MIME type, size, checksum, ownership, visibility, and retention policy, not binary files.
- Enable PostGIS geometry indexes for mapwork. Restrict geometry type and SRID per learning activity and validate uploaded GeoJSON size and coordinates.

## 6. Portal and UI/UX Guidelines

Use a consistent shell with role-aware navigation, school/grade context, notifications, and a visible account switcher where a user has multiple roles. On mobile, prioritize the current task and collapse secondary navigation into an accessible drawer. Avoid showing a learner's full name, school, and rank together on public leaderboards unless the school and guardian privacy policy explicitly permits it.

### Live Contest Arena

- **Pre-join state:** contest title, subject/grade, organizer, start time, duration, rules, eligibility, entry-pass state, accessibility options, and connection check. Provide a clear join action and an alternative text-only mode.
- **Live layout:** stable header with contest state and server-synced time; central question canvas; answer controls; question progress that does not reveal future answers; optional map/practical canvas; help/report issue action. Keep other learners' answers hidden.
- **Integrity cues:** explain when fullscreen is requested and what tab visibility events are recorded. A browser cannot reliably prevent cheating; log minimized, reviewable signals with timestamps and do not auto-disqualify on a single focus change. Provide an appeal path.
- **Network recovery:** persist accepted answers server-side, display acknowledged/pending state per answer, reconnect with the attempt token, and restore the current question/deadline. Never silently resubmit a different answer after reconnect.
- **Results:** show score, EE/ME/AE/BE rubric interpretation, rank and scope filter, topic-level strengths/revision areas, points/badges, and certificate download if earned. Present private rank before public-school details.

### Teacher Scorebook and Contest Builder

- **Scorebook:** roster rows and learning-outcome columns, grade/class/subject filters, rubric-level dropdown with label and color, evidence/comment drawer, unsaved/validation/error state, last editor/time, and export/print. Support keyboard-only entry and bulk import preview; never silently overwrite a concurrent edit.
- **Entry workflow:** autosave draft with an explicit saved indicator; publish/finalize separately. Use optimistic concurrency (`revision`/ETag), show a conflict comparison, and record who changed what. Flag at-risk learners with transparent criteria (for example, repeated BE results across recent assessments) and allow teacher dismissal/notes.
- **Contest builder:** choose mode, subject, grade, class/school audience, schedule, duration, entry rules, question bank filters, randomization, per-question timer, scoring/tie-break policy, accommodations, and preview. Validate question count, answer keys, copyright/source metadata, and schedule conflicts before publish.
- Do not label learner-level performance as a diagnosis. Risk indicators must be explainable and visible only to authorized staff/guardians.

### Student Dashboard

- Show current grade/pathway and subjects, today's next activity, assigned work, recent competency trend, active contests, and one clear next action.
- Subject cards lead into strand/sub-strand progress. Competency radar charts include a table or list alternative, define the scale, and distinguish missing evidence from low scores.
- Keep reward progress visible but secondary to learning. Points are an auditable ledger; do not imply points can be exchanged for cash.
- Video lessons show duration, captions, transcript, playback speed, offline/low-bandwidth option where licensed, and progress resume. Include player-only zoom controls at 100%, 125%, 150%, and 175%, plus reset to 100%; zoom the picture within a clipped 16:9 viewport without scaling the surrounding page. Use labelled zoom-in/out/reset buttons, announce the current percentage to assistive technology, disable controls at min/max, and keep the player keyboard-operable. Zoom is a local viewing preference and must not change the source video or assessment state. Interactive mapwork must support keyboard and screen reader alternatives.

### Parent Portal

- Provide a learner switcher limited to verified `ParentLearnerLink` relationships. Each learner view shows cross-subject progress, rubric descriptors, teacher comments, published report cards, upcoming work, and recent contest participation/results.
- Separate teacher-entered CBA/SBA evidence from automated contest results; show dates, subject/outcome, and the source of every result. Notify guardians about significant published updates without exposing other learners in a class leaderboard.
- Show each learner's active access passes, expiry, renewal options, M-Pesa payment state, receipts, and support contact. A guardian can manage multiple learners and see school-issued entitlements without purchasing duplicates.

### Admin Console

- **Contest scheduler:** calendar and list views for national, county, school, and class contests; filters by grade, subject, pathway, status, capacity, and entitlement. Show schedule conflicts, audience scope, publishing status, and a controlled pause/cancel flow.
- **Question bank:** search by curriculum version, outcome, grade, subject, difficulty, type, source/license, author, and moderation state. Preview questions and answer keys only for authorized reviewers; keep edits versioned and record approvals.
- **Payment audit:** filter transactions by provider, state, date, school, product, and reconciliation status. Expose provider references and redacted phone/account details, callback history, amount comparison, and a controlled refund/reconcile action with reason and audit trail.
- **Analytics:** aggregate enrollment, active learners, subject/outcome coverage, contest completion, payment conversion, and platform health. Default to aggregate data; learner-level drill-down requires a separate permission and audit event.

### Paywall and Checkout Modal

- State exactly what the learner receives, the learner/grade/subject scope, price in KES, billing term, renewal/expiry, refund/contact policy, and whether a school license already grants access.
- Offer M-Pesa phone entry, supported card/mobile-money alternatives, school voucher entry, loading/pending/success/failure states, and a safe retry path.
- Explain that STK initiation is pending until provider confirmation. A dismissed modal must not lose transaction status; show receipt/history outside the modal.
- Prevent duplicate checkout with a client idempotency key, and do not gate free content or current school entitlements by mistake.

## 7. API and Realtime Contract

All endpoints are HTTPS, versioned, paginated where applicable, validated server-side, and scoped to the authenticated actor's role, school membership, grade, and assigned learners. Use a consistent error format with `code`, human-readable `detail`, optional field errors, and `request_id`. Use DRF throttles on authentication, answer, voucher, and payment endpoints. Web clients use short-lived access credentials in secure HttpOnly cookies with CSRF protection; rotate refresh credentials and support revocation.

### REST routes

| Method and path | Purpose / authorization |
|---|---|
| `GET /api/v1/me` | Current identity, active role, memberships, and entitlements |
| `GET /api/v1/curriculum/subjects?grade=7&pathway=` | Published subjects for a curriculum version and grade |
| `GET /api/v1/learners/{learner_id}/progress?subject=` | Authorized student, linked guardian, or assigned teacher progress |
| `GET /api/v1/guardians/me/learners` | Verified linked learners and guardian-visible published progress summaries |
| `GET /api/v1/guardians/me/contest-updates` | Contest participation/results for verified linked learners |
| `GET /api/v1/learning/lessons/{lesson_id}/playback` | Verify learner/school entitlement and return a short-lived signed adaptive-stream URL plus captions/transcript metadata |
| `GET /api/v1/teachers/classes/{class_id}/scorebook?assessment=` | Teacher/admin roster and scorebook with revision/ETag |
| `PUT /api/v1/teachers/assessments/{assessment_id}/scores/bulk` | Validate and save a batch of competency scores; teacher/admin only |
| `PATCH /api/v1/teachers/assessments/{assessment_id}/learners/{learner_id}/scores/{score_id}` | Update a score/evidence record with `If-Match` revision |
| `POST /api/v1/contests` | Create draft contest; teacher or contest admin, scoped to authorized class/school |
| `POST /api/v1/contests/{contest_id}/publish` | Validate and publish/schedule contest |
| `POST /api/v1/admin/contests/{contest_id}/schedule` | Platform admin schedules or reschedules a contest with scope/capacity validation |
| `GET /api/v1/admin/questions?subject=&grade=&status=` | Authorized question-bank review and moderation queue |
| `POST /api/v1/admin/questions/{question_id}/approve` | Record reviewer approval and publish an immutable question version |
| `GET /api/v1/admin/payments/audit?provider=&status=&from=&to=` | Finance/admin audit view with redacted provider data and callback history |
| `GET /api/v1/admin/analytics?from=&to=&school=` | Permission-gated aggregate platform and school metrics |
| `GET /api/v1/contests?grade=&subject=&scope=` | Discover contests visible to the learner |
| `POST /api/v1/contests/{contest_id}/join` | Eligibility/pass check; returns attempt ID, server deadline, and WS token |
| `POST /api/v1/contests/{contest_id}/attempts/{attempt_id}/answers` | HTTP fallback for answer submission; idempotent by attempt/item |
| `POST /api/v1/contests/{contest_id}/attempts/{attempt_id}/submit` | Finalize attempt; repeat requests return the same final result |
| `GET /api/v1/contests/{contest_id}/leaderboard?scope=school&cursor=` | Authorized, paginated ranks; public fields are privacy-filtered |
| `GET /api/v1/learners/{learner_id}/badges` | Earned badges and certificate metadata |
| `GET /api/v1/products?grade=&subject=` | Available passes, school license options, and current entitlements |
| `POST /api/v1/payments/mpesa/stk-push` | Start an idempotent STK request; returns `payment_id` and `PENDING` |
| `POST /api/v1/payments/paystack/initialize` | Initialize Paystack checkout; server calculates amount |
| `POST /api/v1/payments/flutterwave/initialize` | Initialize Flutterwave checkout; server calculates amount |
| `POST /api/v1/payments/vouchers/redeem` | Atomically redeem voucher for authenticated learner/school |
| `GET /api/v1/payments/{payment_id}` | Poll payment state/receipt for the payer or authorized school finance role |
| `POST /api/v1/webhooks/mpesa/stk` | Daraja callback; provider correlation/idempotency verification; no browser auth |
| `POST /api/v1/webhooks/paystack` | Verify provider signature against raw request body, then enqueue processing |
| `POST /api/v1/webhooks/flutterwave` | Verify provider signature/hash, then enqueue processing |

### Teacher grade-entry contract

`PUT /api/v1/teachers/assessments/{assessment_id}/scores/bulk` accepts an `Idempotency-Key` and payload similar to:

```json
{
  "rubric_version": "cbe-2026-v1",
  "scores": [
    {
      "learner_id": "uuid",
      "outcome_id": "uuid",
      "score_percent": 76.5,
      "rubric_level": "ME",
      "teacher_comment": "Explains the process; include evidence for the final step.",
      "evidence": {"artifact_id": "uuid"},
      "expected_revision": 2
    }
  ]
}
```

The API verifies the teacher owns or is assigned to the class and assessment; every learner is on that roster; outcomes belong to the assessment subject/grade; rubric level and numeric band are consistent with the chosen rubric version; and evidence is accessible to that school. Return per-row accepted/rejected status and new revision. Use a transaction per batch or clearly report partial success; the product should choose all-or-nothing for a single class save to avoid misleading the teacher. Emit an audit event for create/update/publish.

### Contest WebSocket contract

**URL:** `wss://<host>/ws/v1/contests/{contest_id}/live/`  
Authenticate via the secure session cookie (preferred) or a short-lived, single-purpose join token. Do not put long-lived bearer tokens in query strings. Authorize group membership before accepting the socket.

Client commands:

- `attempt.resume`: attempt ID and last acknowledged event sequence.
- `answer.submit`: attempt ID, contest item ID, answer payload, client-generated answer UUID, and observed client timestamp (diagnostic only).
- `presence.heartbeat`: optional heartbeat; rate limited.
- `contest.leave`: leave presence group without deleting an attempt.

Server events:

- `contest.state`: contest state, server time, and server-side deadline.
- `contest.started` / `contest.paused` / `contest.ended`: authorized transition with sequence number.
- `question.current`: only the learner's assigned question and its timer; never include the answer key.
- `answer.ack`: answer UUID, accepted/rejected state, server received time, and current revision.
- `leaderboard.delta`: privacy-filtered rank/score delta for the requested authorized scope.
- `attempt.result`: final score, rubric mapping, and allowed feedback after policy permits disclosure.
- `error`: stable machine code, safe message, and retryability.

Every server event includes `event_id`, monotonic per-contest `sequence`, and `server_time`. Clients deduplicate by `event_id`, ignore older sequence numbers, reconnect with jittered exponential backoff, and reconcile state with REST after reconnect. Never broadcast one learner's answer text, personal contact data, or hidden correctness to other participants. Enforce message-size/rate limits and disconnect abusive clients.

### M-Pesa callback rules

- Configure a stable HTTPS callback URL and unique `accountReference`/`transactionDesc` correlation to an internal payment ID that does not expose learner PII.
- Validate expected fields, merchant request ID, checkout request ID, amount, currency, receipt, and pending-payment association. Verify provider status through the supported Daraja query/reconciliation path when callback data is incomplete or contradictory.
- Persist an idempotent `PaymentEvent` before mutating subscription state. Enforce uniqueness on provider event/checkout identifiers and wrap state update plus entitlement grant in `transaction.atomic()` with row locks.
- Respond to valid callbacks promptly; enqueue slow side effects after commit. Unknown callback IDs are recorded and alerted, not discarded. Redact MSISDN and credentials from logs and define retention/access policy for raw provider payloads.

## 8. Security, Privacy, Reliability, and Acceptance Criteria

- **Authorization:** deny by default; test direct object-reference attacks across schools, teachers, parents, and learners. Platform-admin actions require stronger authentication and audit logging.
- **Minors and privacy:** map flows to Kenya's Data Protection Act and applicable ODPC guidance; obtain valid guardian/school consent where required; document controller/processor roles; minimize public leaderboard identity; provide correction, access, retention, and deletion workflows consistent with safeguarding and legal obligations.
- **Contest integrity:** server-authoritative clock and scoring, per-attempt random order, one accepted answer per item unless explicitly revised, question-bank version snapshots, immutable score events, and published tie-break rules. Fullscreen and tab visibility are deterrents/signals only, not proof of cheating.
- **Payment integrity:** signed webhooks, provider correlation, idempotency, reconciliation, receipt, refund/reversal states, and audit trail. Never use client-reported amount or client redirect as payment confirmation.
- **Accessibility:** target WCAG 2.2 AA; test keyboard navigation, screen readers, zoom/reflow, captions/transcripts, and color-vision accessibility. Supply non-map alternatives for spatial tasks.
- **Reliability:** target 99.9% monthly availability after launch; contest answer acknowledgement p95 under 500 ms in-region during expected load; leaderboard update p95 under 2 seconds; payment callback processing p95 under 10 seconds excluding provider delays. Load-test at 2x forecast peak before national contests.
- **Recovery:** PostgreSQL point-in-time recovery, tested backups, Redis rebuild procedures, queue retry/dead-letter policies, and documented incident response. Contest state can be reconciled from database events after a worker or socket restart.
- **Auditability:** log actor, school, entity, before/after revision, timestamp, and request ID for grade changes, contest publication/finalization, entitlement changes, and admin actions. Restrict audit read access.

## 9. Step-by-Step Implementation Roadmap

Effort estimates are directional for a cross-functional team of roughly 5–8 people; validate after curriculum, payment-provider, and school-pilot discovery. Each phase ends with a release gate, not just feature completion.

### Phase 0 — Discovery and foundations (2–3 weeks)

1. Confirm target launch counties, school onboarding model, guardian consent, age-appropriate privacy, and roles.
2. Obtain/validate the official Grades 4–12 subject, strand, outcome, and pathway datasets with a curriculum advisor; define version/import approval workflow.
3. Select M-Pesa production credentials and provider callback/reconciliation path; verify payment terms, refunds, contest-entry rules, and tax/accounting requirements.
4. Run learner/teacher/parent usability sessions for low-end Android devices, low bandwidth, Kiswahili/English, accessibility, and school connectivity.
5. Define data classification, threat model, retention schedule, service objectives, and measurable pilot success metrics.
6. Establish repository/CI, development environments, container orchestration for local work, PostgreSQL/PostGIS, Redis, ASGI, Celery, object storage, and secret handling.

**Gate:** signed product scope, approved curriculum sample, architecture decision records, privacy/security review, and testable UX prototypes.

### Phase 1 — MVP: Core Learning, SBA, and Contests (10–14 weeks)

1. Implement custom identity, school memberships, parent-learner links, role/object permissions, session lifecycle, and audit events.
2. Build curriculum import/versioning for one pilot grade band and a representative set of subjects, strands, outcomes, and EE/ME/AE/BE rubric descriptors.
3. Deliver teacher class roster, assignment creation, scorebook entry, revision/conflict handling, evidence/comments, and basic learner-at-risk indicators with explainable rules.
4. Deliver student/parent dashboards, subject progress, teacher-published reports, and initial video/resource library with CDN/signed playback, low-bandwidth fallbacks, captions/transcripts, playback speed, progress resume, and accessible 100–175% player zoom controls.
5. Build Practice Arena and teacher-created class challenges first: question bank approval, randomized ordering, server timer, submission, immediate post-submit feedback, and scoped leaderboards.
6. Add scheduled contest lifecycle and websocket state sync, with REST fallback and reconnect support. Start with pilot-scale concurrent-user limits and controlled school events.
7. Seed operational data, notifications, basic badges/points ledger, and printable clearly unofficial Soma Link certificates.
8. Implement payment sandbox adapter and school voucher support. Gate paid content only after verified sandbox callback/reconciliation behavior; do not launch real-money charging until finance/legal/security sign-off.
9. Add automated tests: model constraints, authorization matrix, scoring determinism, timer edge cases, duplicate answers, concurrent submissions, callback idempotency, and accessibility smoke checks.

**MVP acceptance:** pilot learners can access approved grade/subject content; teachers can record and correct SBA scores with audit history; eligible learners complete a contest under reconnects; results and ranks are reproducible; parents see only linked learners; no duplicate payment event grants duplicate access; keyboard/screen-reader paths work for core tasks.

### Phase 2 — Monetization and school pilots (8–12 weeks)

1. Introduce product catalog and entitlement service for Individual Subject Pass, All-Subject Grade Pass (monthly/term), Contest Pass, and Institutional License.
2. Integrate M-Pesa STK Push in production with signed/provider-verified event processing, reconciliation, refund/reversal support, receipts, and finance audit exports.
3. Add Paystack/Flutterwave only after provider coverage and finance requirements are confirmed; keep provider adapters isolated and use one canonical payment state machine.
4. Build school onboarding, CSV roster import validation, class management, voucher generation/redemption, school billing views, and license seat/expiry management.
5. Run controlled pilots across urban/rural and different connectivity/device conditions; instrument funnel, latency, contest completion, teacher workload, payment success, and support volume.
6. Calibrate rubric explanations, contest fairness, item difficulty, learner-risk thresholds, points redemption, and subscription price/package conversion with school and parent feedback.
7. Conduct penetration test, privacy impact assessment, payment reconciliation exercise, restore drill, accessibility review, and load test at forecast national-contest capacity.

**Gate:** signed school agreements, production payment approvals, support/refund procedures, privacy and security sign-off, validated financial reconciliation, and pilot success metrics met.

### Phase 3 — Full production rollout (12+ weeks; staged)

1. Expand approved curriculum coverage across Grades 4–12, subjects, senior-secondary pathways, and curriculum versions; publish content provenance and review status.
2. Scale national/termly contests with capacity reservations, queue backpressure, regional load tests, operational command dashboard, and incident communications.
3. Add advanced question authoring/moderation, practical/mapwork tools with PostGIS, richer teacher analytics, moderation workflows, certificates, and multilingual content support.
4. Roll out institution contracts, school-wide entitlements, finance reconciliation reports, parent renewal workflows, vouchers, and provider fallbacks.
5. Add recommendation/personalization only from reviewed competency evidence, with explainability and teacher controls; do not use opaque rankings for high-impact decisions.
6. Formalize SRE: on-call rotations, SLO/error budgets, disaster recovery objectives, dependency upgrades, data governance review, and quarterly access audits.
7. Release by cohort: internal staff, a small pilot, county cohorts, then national availability. Monitor support load and payment/contest integrity between cohorts.

**Production exit criteria:** SLOs met for two consecutive release windows; tested backup restore and failover; reconciliation variance within finance-approved tolerance; no unresolved critical security/privacy issues; support and safeguarding teams staffed; curriculum owner signs off published data.

## 10. Decisions to Confirm Before Build

- Which KICD curriculum version and approved source dataset will be the canonical launch baseline?
- Is the initial contest leaderboard public, school-only, or anonymized by default, especially for minors?
- Are contest points redeemable only for Soma Link digital content, and what expiry/fraud controls apply?
- Which payment provider is the launch provider, who is merchant of record, and what refund/reversal policy applies?
- What school license contract and roster/seat model should be supported at launch?
- What accessibility accommodations are allowed in timed contests, and how do accommodations affect timer fairness?
- Does a school require on-premise/offline operation, or is low-bandwidth reconnect support sufficient for the first release?
