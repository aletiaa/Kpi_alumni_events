from datetime import datetime
from types import SimpleNamespace
import sqlite3
import pytest
from app.models import AdministratorGrant, AdminAudit, InterestTopic, User, News, TelegramNewsSubmission
from app.security import hash_password, create_session_token
from app.services.operational_security import token
from app.services.telegram_commands import dispatch
from app.services.personalization import recommendations
from app.services.topic_catalog import catalog_topics
from test_telegram_commands import update, person
from test_engagement import event

PASSWORD = "Unit-test-password-123"


def manager(client, db, manage=True):
    user = User(email="manager@example.test", full_name="Manager", password_hash=hash_password(PASSWORD),
                role="alumni", is_active=True, is_blocked=False, is_email_verified=True)
    db.add(user)
    db.flush()
    db.add(AdministratorGrant(user_id=user.id, can_manage_admins=manage, granted_by="bootstrap"))
    db.commit()
    identity = SimpleNamespace(user_id=user.id, email=user.email, role="admin")
    client.cookies.set("session", create_session_token(user.id, "admin", user.email, user.full_name))
    return identity


def target(db):
    user = User(email="target@example.test", full_name="Target", password_hash=hash_password(PASSWORD),
                role="alumni", is_active=True, is_blocked=False, is_email_verified=True)
    db.add(user)
    db.commit()
    return user


def test_manager_promotes_and_revokes_with_audit(client, db):
    actor = manager(client, db)
    user = target(db)
    route = f"/admin/operations/administrators/{user.id}"
    fields = dict(csrf=token(actor), password=PASSWORD, confirm="yes", action="admin")
    assert client.post(route, data=fields, follow_redirects=False).status_code==303
    assert db.get(AdministratorGrant, user.id) is not None
    assert db.query(AdminAudit).filter_by(action="administrator:admin", target=str(user.id)).count()==1
    fields["action"]="revoke"
    assert client.post(route, data=fields, follow_redirects=False).status_code==303
    db.expire_all()
    assert db.get(AdministratorGrant, user.id) is None


@pytest.mark.parametrize("field,value,expected", [
    ("csrf", "invalid", 403), ("password", "wrong", 403), ("confirm", "", 400), ("action", "owner", 400)])
def test_promotion_requires_csrf_password_confirmation(client, db, field, value, expected):
    actor=manager(client, db)
    user=target(db)
    fields=dict(csrf=token(actor), password=PASSWORD, confirm="yes", action="admin")
    fields[field]=value
    assert client.post(f"/admin/operations/administrators/{user.id}", data=fields).status_code==expected
    assert db.get(AdministratorGrant, user.id) is None


def test_regular_admin_cannot_promote_or_access_backups(client, db):
    actor=manager(client, db, False)
    user=target(db)
    assert client.get("/admin/operations").status_code==200
    assert client.get("/admin/operations/backups").status_code==403
    assert client.post(f"/admin/operations/administrators/{user.id}", data=dict(
        csrf=token(actor),password=PASSWORD,confirm="yes",action="manager")).status_code==403


def test_manager_cannot_revoke_self_or_block_manager(client, db):
    actor=manager(client, db)
    fields=dict(csrf=token(actor),password=PASSWORD,confirm="yes",action="revoke")
    assert client.post(f"/admin/operations/administrators/{actor.user_id}",data=fields).status_code==409
    assert client.post(f"/admin/users/{actor.user_id}/block").status_code==409
    assert db.get(AdministratorGrant, actor.user_id).can_manage_admins


def test_revocation_invalidates_existing_admin_session(client, db):
    actor=manager(client, db)
    assert client.get("/admin").status_code==200
    db.delete(db.get(AdministratorGrant, actor.user_id))
    db.commit()
    assert client.get("/admin").status_code==403


def test_unverified_account_cannot_be_promoted(client, db):
    actor=manager(client, db)
    user=target(db)
    user.is_email_verified=False
    db.commit()
    assert client.post(f"/admin/operations/administrators/{user.id}",data=dict(
        csrf=token(actor),password=PASSWORD,confirm="yes",action="admin")).status_code==400


def test_deletion_requires_confirmation_and_preserves_news(client, db):
    actor=manager(client, db)
    user=target(db)
    db.add(News(title="Preserved",content="Content",author_id=user.id,is_published=True))
    db.commit()
    route=f"/admin/operations/users/{user.id}/delete"
    assert client.post(route,data=dict(csrf=token(actor),password=PASSWORD)).status_code==400
    assert client.post(route,data=dict(csrf=token(actor),password=PASSWORD,confirm="yes"),
                       follow_redirects=False).status_code==303
    db.expire_all()
    assert db.get(User,user.id) is None
    assert db.query(News).one().author_id is None


def test_event_delete_cannot_bypass_confirmation(client, db):
    actor=manager(client,db)
    item=event(db)
    assert client.post(f"/admin/events/{item.id}/delete").status_code==403
    assert client.post(f"/admin/events/{item.id}/delete",data=dict(
        csrf=token(actor),confirm="yes"),follow_redirects=False).status_code==303


def test_new_topics_can_be_managed_without_code(client, db):
    actor=manager(client,db)
    assert client.post("/admin/operations/topics",data=dict(csrf=token(actor),
        label_uk="Астрономія",label_en="Astronomy",aliases="зорі\nspace research",active="yes"),
        follow_redirects=False).status_code==303
    catalog=db.query(InterestTopic).all()
    topic=catalog[0]
    assert catalog_topics("Space research for alumni",catalog)=={topic.key}
    topic.is_active=False
    db.commit()
    assert catalog_topics("Astronomy",catalog)==set()


def test_telegram_submission_stays_draft_and_is_idempotent(client, db):
    user=person(db)
    incoming=update("/submit_news Test news\nA proposed article")
    dispatch(db,incoming)
    db.commit()
    dispatch(db,incoming)
    db.commit()
    assert db.query(News).count()==1
    assert not db.query(News).one().is_published
    actor=manager(client,db)
    assert client.get("/admin/operations/submissions").status_code==200
    assert client.post("/admin/operations/submissions/1",data=dict(csrf=token(actor),
        action="publish",confirm="yes"),follow_redirects=False).status_code==303
    db.expire_all()
    assert db.query(News).one().is_published
    assert db.query(TelegramNewsSubmission).one().status=="published"


def test_unlinked_telegram_user_cannot_submit_news(db):
    dispatch(db,update("/submit_news Unauthorized\nBody"))
    db.commit()
    assert db.query(News).count()==0


def test_private_backup_restore_and_tamper_detection(db, tmp_path, monkeypatch):
    from app.services import backups
    path=tmp_path/"source.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        connection.execute("INSERT INTO users VALUES (1,'Before')")
    monkeypatch.setattr(backups,"DATABASE_URL","sqlite:///"+str(path))
    monkeypatch.setattr(backups,"BASE_DIR",tmp_path)
    monkeypatch.setattr(backups,"ADMINS_CSV_PATH",str(tmp_path/"absent.csv"))
    monkeypatch.setattr(backups,"SETTINGS",())
    record=backups.create_backup(db)
    assert record.verified_at is not None
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO users VALUES (2,'After')")
    backups.verify_backup(record)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]==2
    backups.backup_path(record).write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        backups.verify_backup(record)


@pytest.mark.parametrize("page",["","/audit","/topics","/submissions","/backups"])
def test_operations_pages_render_for_manager(client,db,page):
    manager(client,db)
    assert client.get("/admin/operations"+page).status_code==200


def test_delegated_admin_telegram_link_is_single_use(client, db):
    from app.services.telegram_live import begin_link, consume_update
    actor = manager(client, db)
    code = begin_link(db, actor.email)
    incoming = update("/start " + code)
    consume_update(db, incoming)
    db.commit()
    from app.models import TelegramLink
    link = db.get(TelegramLink, actor.email)
    assert link.chat_id == str(incoming["message"]["chat"]["id"])
    assert link.code_hash is None
    incoming["message"]["chat"]["id"] += 1
    incoming["message"]["from"]["id"] += 1
    consume_update(db, incoming)
    assert link.chat_id != str(incoming["message"]["chat"]["id"])


def test_revoked_admin_cannot_link_telegram(client, db):
    from app.services import telegram_live
    actor = manager(client, db)
    code = telegram_live.begin_link(db, actor.email)
    db.delete(db.get(AdministratorGrant, actor.user_id))
    db.commit()
    telegram_live.consume_update(db, update("/start " + code))
    from app.models import TelegramLink
    assert db.get(TelegramLink, actor.email).chat_id is None


def test_backup_retention_preserves_fourteen_and_unmanaged_files(db, tmp_path, monkeypatch):
    from app.services import backups
    from app.models import BackupRecord
    monkeypatch.setattr(backups, "DATABASE_URL", "sqlite:///" + str(tmp_path / "source.db"))
    directory = backups.backup_directory()
    directory.mkdir()
    unrelated = directory / "manual-backup.db"
    unrelated.write_bytes(b"keep")
    for index in range(16):
        record = BackupRecord(filename=f"backup-20261002-120000-{index:08x}.tar.gz", checksum="0" * 64)
        db.add(record)
        backups.backup_path(record).write_bytes(b"archive")
    db.commit()
    backups.prune_backups(db)
    assert db.query(BackupRecord).count() == 14
    assert len(list(directory.glob("*.tar.gz"))) == 14
    assert unrelated.exists()


def test_topic_key_survives_label_rename(db):
    topic = InterestTopic(key="custom_astronomy", label_uk="Астрономія", label_en="Astronomy", aliases="")
    db.add(topic)
    db.commit()
    topic.label_en = "Space science"
    assert catalog_topics("custom_astronomy", [topic]) == {topic.key}
