from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import SECRET_KEY, TELEGRAM_ENABLED
from app.db import get_db
from app.deps import require_admin
from app.models import BotCampaign, Event, News, TelegramLink, TelegramState, TelegramDelivery
from app.services.telegram_live import begin_link, send_campaign, TelegramError
from app.services.bot_bridge import demo_recipients, export_events
from app.models import TelegramBroadcast, TelegramRecipientDelivery, TelegramSubscription, User
from app.services.telegram_broadcasts import AUDIENCES, recipients, queue, cancel
from app.services.telegram_health import health
from app.models import TelegramUpload, TelegramBotReply, TelegramNewsSubmission
import json

router = APIRouter(prefix="/admin/bots", tags=["bot-administration"])
signer = URLSafeTimedSerializer(SECRET_KEY, salt="bot-admin")


def verify_csrf(token, admin):
    try:
        if signer.loads(token, max_age=7200) != admin.email:
            raise BadSignature("Wrong administrator")
    except BadSignature:
        raise HTTPException(403, "Оновіть сторінку та повторіть дію.")


@router.get("")
def dashboard(request: Request, source: str = "", source_id: int = 0, code: str = "",
              db: Session = Depends(get_db), admin=Depends(require_admin)):
    preview = ""
    if source:
        model = {"event": Event, "news": News}.get(source)
        item = db.get(model, source_id) if model else None
        if item is None:
            raise HTTPException(404)
        body = item.description if source == "event" else item.content
        preview = (item.title + "\n\n" + (item.short_description or body or ""))[:4000]
    return request.app.state.templates.TemplateResponse(request, "admin/bots.html", {
        "request": request, "app_name": "AlumnixHub", "ident": admin,
        "csrf": signer.dumps(admin.email), "preview": preview,
        "campaigns": db.query(BotCampaign).order_by(BotCampaign.id.desc()).limit(50).all(),
        "events": db.query(Event).order_by(Event.start_time.desc()).limit(30).all(),
        "news": db.query(News).filter_by(is_published=True).order_by(News.created_at.desc()).limit(30).all(),
        "demo_recipients": demo_recipients,
        "telegram_enabled": TELEGRAM_ENABLED,
        "bot_health":health(request, db),
        "telegram_state": db.get(TelegramState, 1),
        "telegram_link": db.get(TelegramLink, admin.email),
        "link_code": code,
        "reply_counts":dict(db.query(TelegramBotReply.status, func.count()).group_by(TelegramBotReply.status)),
        "recipient_counts":dict(db.query(TelegramRecipientDelivery.status, func.count()).group_by(TelegramRecipientDelivery.status)),
        "pending_submissions":db.query(TelegramNewsSubmission).filter_by(status="pending").count(),
        "deliveries": {d.campaign_id: d for d in db.query(TelegramDelivery).order_by(TelegramDelivery.campaign_id.desc()).limit(100)},
    })


@router.post("/link")
def link_account(request: Request, csrf: str = Form(""), db: Session = Depends(get_db), admin=Depends(require_admin)):
    verify_csrf(csrf, admin)
    if not TELEGRAM_ENABLED:
        raise HTTPException(409)
    code = begin_link(db, admin.email)
    # Render directly: linking secrets must not enter URL/access logs.
    response = dashboard(request, db=db, admin=admin, code=code)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.post("/campaigns/{campaign_id}/send")
def send_live(campaign_id: int, csrf: str = Form(""), db: Session = Depends(get_db), admin=Depends(require_admin)):
    verify_csrf(csrf, admin)
    if not TELEGRAM_ENABLED:
        raise HTTPException(409)
    campaign = db.get(BotCampaign, campaign_id)
    if not campaign or campaign.audience != "telegram_self":
        raise HTTPException(400)
    if campaign.created_by != admin.email:
        raise HTTPException(403)
    try:
        send_campaign(db, campaign, admin.email)
    except TelegramError:
        raise HTTPException(409, "Telegram не підключено") from None
    return RedirectResponse("/admin/bots#campaigns", status_code=303)


@router.post("/campaigns")
def create_campaign(body: str = Form(..., max_length=4000), audience: str = Form(...), topic: str = Form('news'),
                    csrf: str = Form(""), db: Session = Depends(get_db), admin=Depends(require_admin)):
    verify_csrf(csrf, admin)
    if not body.strip() or audience not in {"all", "alumni", "student", "telegram_self"} | AUDIENCES:
        raise HTTPException(400)
    if audience in AUDIENCES and (not TELEGRAM_ENABLED or topic not in {'news', 'events'}):
        raise HTTPException(400)
    campaign = BotCampaign(body=body.strip(), audience=audience, created_by=admin.email)
    db.add(campaign)
    db.flush()
    if audience in AUDIENCES:
        db.add(TelegramBroadcast(campaign_id=campaign.id, topic=topic))
    db.commit()
    if audience in AUDIENCES:
        return RedirectResponse(f'/admin/bots/campaigns/{campaign.id}', status_code=303)
    return RedirectResponse("/admin/bots#campaigns", status_code=303)


@router.post("/campaigns/{campaign_id}/simulate")
def simulate(campaign_id: int, csrf: str = Form(""), db: Session = Depends(get_db), admin=Depends(require_admin)):
    verify_csrf(csrf, admin)
    # Conditional update makes repeated submissions idempotent.
    campaign = db.get(BotCampaign, campaign_id)
    if not campaign:
        raise HTTPException(404)
    if campaign.audience == "telegram_self" or campaign.audience in AUDIENCES:
        raise HTTPException(400)
    db.query(BotCampaign).filter(BotCampaign.id == campaign_id, BotCampaign.simulated_at.is_(None)).update(
        {BotCampaign.simulated_at: datetime.utcnow()})
    db.commit()
    return RedirectResponse("/admin/bots#campaigns", status_code=303)


@router.get("/events.json")
def events_export(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return JSONResponse(export_events(db), headers={
        "Content-Disposition": 'attachment; filename="events.json"', "Cache-Control": "no-store"})


def get_broadcast(db, campaign_id):
    broadcast = db.get(TelegramBroadcast, campaign_id)
    campaign = db.get(BotCampaign, campaign_id)
    if not campaign or not broadcast:
        raise HTTPException(404)
    return campaign, broadcast


@router.get('/campaigns/{campaign_id}')
def review(campaign_id: int, request: Request, page: int = 1,
           db: Session = Depends(get_db), admin=Depends(require_admin)):
    campaign, broadcast = get_broadcast(db, campaign_id)
    page = max(1, page)
    selected = recipients(db, campaign, broadcast)
    rows = db.query(TelegramRecipientDelivery, User).join(User).filter(
        TelegramRecipientDelivery.campaign_id == campaign_id).order_by(User.id).offset((page-1)*50).limit(51).all()
    counts = dict(db.query(TelegramRecipientDelivery.status, func.count()).filter_by(
        campaign_id=campaign_id).group_by(TelegramRecipientDelivery.status).all())
    return request.app.state.templates.TemplateResponse(request, 'admin/broadcast.html', {
        'request':request, 'app_name':'AlumnixHub', 'ident':admin, 'csrf':signer.dumps(admin.email),
        'campaign':campaign, 'broadcast':broadcast, 'eligible_count':selected.count(),
        'counts':counts, 'rows':rows[:50], 'has_next':len(rows)>50, 'page':page,
        'preview_people':db.query(User).filter(User.id.in_(selected.with_entities(
            TelegramSubscription.user_id).scalar_subquery())).order_by(User.id).limit(50).all()
            if not broadcast.queued_at else []})


@router.post('/campaigns/{campaign_id}/queue')
def queue_broadcast(campaign_id: int, csrf: str = Form(''), confirm: str = Form(''),
                    db: Session = Depends(get_db), admin=Depends(require_admin)):
    verify_csrf(csrf, admin)
    campaign, broadcast = get_broadcast(db, campaign_id)
    if campaign.created_by != admin.email:
        raise HTTPException(403)
    if not TELEGRAM_ENABLED or confirm != 'yes':
        raise HTTPException(400)
    if not broadcast.queued_at and not recipients(db, campaign, broadcast).count():
        raise HTTPException(409, 'Немає підписників для цієї аудиторії.')
    queue(db, campaign, broadcast)
    return RedirectResponse(f'/admin/bots/campaigns/{campaign_id}', status_code=303)


@router.get('/status')
def bot_status(request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    link = db.get(TelegramLink,admin.email)
    state = db.get(TelegramState, 1)
    return {'online':health(request,db)['online'], 'linked':bool(link and link.chat_id),
            'checked_at':state.checked_at.isoformat() if state and state.checked_at else None,
            'status':state.status if state else 'not_checked',
            'replies':dict(db.query(TelegramBotReply.status, func.count()).group_by(TelegramBotReply.status)),
            'deliveries':dict(db.query(TelegramRecipientDelivery.status, func.count()).group_by(TelegramRecipientDelivery.status))}


@router.get('/files')
def files(request: Request, page: int = 1, db: Session = Depends(get_db), admin=Depends(require_admin)):
    page = max(1,page)
    rows = db.query(TelegramUpload, User).join(User).order_by(TelegramUpload.id.desc()).offset((page-1)*30).limit(31).all()
    return request.app.state.templates.TemplateResponse(request,'admin/telegram_files.html',{
        'request':request,'app_name':'AlumnixHub','ident':admin,'csrf':signer.dumps(admin.email),
        'rows':rows[:30],'page':page,'has_next':len(rows)>30,
        'linked':db.query(TelegramLink).filter(TelegramLink.admin_email==admin.email,TelegramLink.chat_id.is_not(None)).first()})


@router.post('/files/{file_id}/forward')
def forward_file(file_id: int, csrf: str = Form(''), db: Session = Depends(get_db), admin=Depends(require_admin)):
    verify_csrf(csrf,admin)
    upload = db.get(TelegramUpload,file_id)
    link = db.get(TelegramLink,admin.email)
    if not upload:
        raise HTTPException(404)
    if not TELEGRAM_ENABLED or not link or not link.chat_id:
        raise HTTPException(409,'Telegram не підключено')
    key = f'admin-file:{file_id}:{link.chat_id}'
    if not db.get(TelegramBotReply,key):
        method = {'photo':'sendPhoto','document':'sendDocument','video':'sendVideo'}[upload.kind]
        db.add(TelegramBotReply(key=key,chat_id=link.chat_id,method=method,
            payload=json.dumps({'chat_id':link.chat_id,upload.kind:upload.file_id,'_admin':admin.email})))
        db.commit()
    return RedirectResponse('/admin/bots/files?queued=1',status_code=303)


@router.post('/campaigns/{campaign_id}/cancel')
def cancel_broadcast(campaign_id: int, csrf: str = Form(''),
                     db: Session = Depends(get_db), admin=Depends(require_admin)):
    verify_csrf(csrf, admin)
    get_broadcast(db, campaign_id)
    cancel(db, campaign_id)
    return RedirectResponse(f'/admin/bots/campaigns/{campaign_id}', status_code=303)
