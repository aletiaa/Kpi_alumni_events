from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models import Event


def seed_events_if_empty(db: Session) -> int:
    """
    Inserts demo events only if the events table is empty.
    Returns number of inserted events.
    """
    if db.query(Event).first():
        return 0

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    def make_event(
        *,
        title: str,
        description: str,
        location: str,
        start_offset_days: int,
        start_hour: int,
        duration_hours: int,
        capacity: int,
        registration_cutoff_hours: int = 6,
        short_description: str | None = None,
    ) -> Event:
        start_time = now + timedelta(days=start_offset_days, hours=start_hour)
        end_time = start_time + timedelta(hours=duration_hours)
        registration_deadline = start_time - timedelta(hours=registration_cutoff_hours)

        return Event(
            title=title,
            description=description,
            short_description=short_description,  # NEW
            location=location,
            start_time=start_time,
            end_time=end_time,
            registration_deadline=registration_deadline,
            capacity=capacity,
        )

    events = [
        make_event(
            title="KPI Freshers Networking Night",
            short_description="Meet new students, explore clubs, and get practical campus tips in a relaxed networking format.",
            description="Welcome event for first-year students: networking, student clubs, and campus orientation tips.",
            location="KPI Main Hall",
            start_offset_days=2,
            start_hour=18,
            duration_hours=3,
            capacity=200,
        ),
        make_event(
            title="AI & NLP Workshop (FastAPI + Transformers)",
            short_description="Hands-on NLP session: embeddings, text classification, and integrating Transformers into FastAPI services.",
            description="Hands-on workshop covering text classification, embeddings, and NLP integration in web services.",
            location="KPI IT Center",
            start_offset_days=5,
            start_hour=16,
            duration_hours=2,
            capacity=80,
        ),
        make_event(
            title="Alumni Career Talk: Data & Finance Analytics",
            short_description="Alumni-led talk on analytics careers: interviews, skills roadmap, and building a portfolio for data/finance roles.",
            description="KPI alumni discuss career paths, interviews, and analytics-focused portfolios.",
            location="KPI Lecture Room 3",
            start_offset_days=7,
            start_hour=17,
            duration_hours=2,
            capacity=120,
        ),
        make_event(
            title="Startup Pitch Evening (KPI Students)",
            short_description=None,  # left empty intentionally
            description="Students pitch startup ideas and receive feedback from mentors and alumni.",
            location="KPI Innovation Hub",
            start_offset_days=9,
            start_hour=18,
            duration_hours=3,
            capacity=150,
        ),
        make_event(
            title="Cybersecurity Basics for Students",
            short_description="Core cyber hygiene: spotting phishing, using MFA, improving passwords, and responding to common incidents.",
            description="Introduction to phishing, password hygiene, MFA, and basic incident response.",
            location="KPI Room 214",
            start_offset_days=11,
            start_hour=15,
            duration_hours=2,
            capacity=90,
        ),
        make_event(
            title="IoT Demo Day: Attendance Tracking Prototype",
            short_description=None,  # left empty intentionally
            description="Live demo of IoT-based attendance tracking with analytics dashboard and Q&A session.",
            location="KPI Lab A1",
            start_offset_days=13,
            start_hour=14,
            duration_hours=2,
            capacity=60,
        ),
        make_event(
            title="Guest Lecture: Modern Web Services Architecture",
            short_description="Guest lecture on scalable web systems: microservices patterns, PostgreSQL, queues, and deployment best practices.",
            description="Microservices, PostgreSQL, message queues, and deployment patterns for scalable systems.",
            location="KPI Online (Zoom)",
            start_offset_days=15,
            start_hour=19,
            duration_hours=2,
            capacity=500,
        ),
        make_event(
            title="KPI Alumni Reunion Meetup",
            short_description="Informal meetup for KPI alumni and students to network, reconnect, and start collaborations.",
            description="Informal meetup for KPI alumni and students focused on networking and collaboration.",
            location="KPI Campus Café",
            start_offset_days=18,
            start_hour=18,
            duration_hours=3,
            capacity=180,
        ),
        make_event(
            title="Exam Prep Session: Innovation Management",
            short_description=None,  # left empty intentionally
            description="Revision session with practice questions and discussion of key innovation frameworks.",
            location="KPI Seminar Room B2",
            start_offset_days=20,
            start_hour=16,
            duration_hours=2,
            capacity=100,
        ),
        make_event(
            title="Volunteer Fair (Student & Alumni Projects)",
            short_description="Discover volunteering initiatives and student/alumni-led projects; meet teams and learn how to join.",
            description="Meet volunteering initiatives and charity projects led by students and alumni.",
            location="KPI Courtyard",
            start_offset_days=22,
            start_hour=12,
            duration_hours=4,
            capacity=300,
        ),
        make_event(
            title="KPI Hackathon Weekend",
            short_description="48-hour hackathon across AI/NLP, IoT, and dashboards with mentoring, demos, and team collaboration.",
            description="48-hour hackathon with tracks in AI/NLP, IoT, and web dashboards.",
            location="KPI Tech Hall",
            start_offset_days=25,
            start_hour=10,
            duration_hours=48,
            capacity=250,
            registration_cutoff_hours=24,
        ),
        make_event(
            title="Research Showcase: ML & Data Engineering",
            short_description=None,  # left empty intentionally
            description="Poster-style showcase of student research and applied ML demonstrations.",
            location="KPI Library",
            start_offset_days=28,
            start_hour=13,
            duration_hours=3,
            capacity=140,
        ),
    ]

    db.add_all(events)
    db.commit()
    return len(events)
