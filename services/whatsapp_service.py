"""WhatsApp: Meta Cloud API and/or Twilio; falls back to logging when unset."""
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


def _normalize_digits(phone: str) -> str:
    """Digits only, suitable for Meta (international, no +)."""
    digits = ''.join(c for c in (phone or '') if c.isdigit())
    return digits


def _phone_e164(phone: str) -> str:
    """India-first E.164 (+...) for Twilio / shared entrypoint."""
    d = _normalize_digits(phone)
    if not d:
        return ''
    if d.startswith('91') and len(d) >= 12:
        return '+' + d
    if len(d) == 10:
        return '+91' + d
    return '+' + d


def _send_meta_graph(to_digits: str, body: str) -> bool:
    token = getattr(settings, 'META_WHATSAPP_TOKEN', '') or ''
    phone_id = getattr(settings, 'META_WHATSAPP_PHONE_NUMBER_ID', '') or ''
    version = getattr(settings, 'META_WHATSAPP_API_VERSION', 'v21.0')
    if not token or not phone_id or not to_digits or not body:
        return False
    url = f'https://graph.facebook.com/{version}/{phone_id}/messages'
    payload = {
        'messaging_product': 'whatsapp',
        'to': to_digits,
        'type': 'text',
        'text': {'preview_url': False, 'body': body[:4096]},
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
            if resp.status >= 400:
                logger.error('Meta WhatsApp HTTP %s: %s', resp.status, raw)
                return False
            logger.info('Meta WhatsApp sent ok: %s', raw[:200])
            return True
    except urllib.error.HTTPError as e:
        err = e.read().decode('utf-8', errors='replace')
        logger.error('Meta WhatsApp HTTPError %s: %s', e.code, err)
        return False
    except Exception as e:
        logger.exception('Meta WhatsApp failed: %s', e)
        return False


def _twilio_client():
    sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '') or ''
    token = getattr(settings, 'TWILIO_AUTH_TOKEN', '') or ''
    if not sid or not token:
        return None
    try:
        from twilio.rest import Client
        return Client(sid, token)
    except Exception as e:
        logger.warning('Twilio client init failed: %s', e)
        return None


def _send_twilio(to_e164: str, body: str) -> bool:
    frm = getattr(settings, 'TWILIO_WHATSAPP_FROM', '') or ''
    if not frm.startswith('whatsapp:'):
        frm = f'whatsapp:{frm}' if frm else ''
    to_wa = to_e164 if to_e164.startswith('whatsapp:') else f'whatsapp:{to_e164}'
    client = _twilio_client()
    if not client or not frm:
        return False
    try:
        client.messages.create(from_=frm, to=to_wa, body=body)
        return True
    except Exception as e:
        logger.exception('Twilio WhatsApp send failed: %s', e)
        return False


def _provider() -> str:
    explicit = (getattr(settings, 'WHATSAPP_PROVIDER', None) or 'auto').strip().lower()
    if explicit in ('meta', 'twilio', 'stub'):
        return explicit
    # auto
    if (getattr(settings, 'META_WHATSAPP_TOKEN', '') or '') and (
        getattr(settings, 'META_WHATSAPP_PHONE_NUMBER_ID', '') or ''
    ):
        return 'meta'
    if (getattr(settings, 'TWILIO_ACCOUNT_SID', '') or '') and (
        getattr(settings, 'TWILIO_WHATSAPP_FROM', '') or ''
    ):
        return 'twilio'
    return 'stub'


def send_whatsapp(to_e164: str, body: str) -> bool:
    """
    to_e164: e.g. +919876543210 (Twilio) or same for normalization to digits (Meta).
    """
    if not to_e164 or not body:
        return False
    provider = _provider()
    digits = _normalize_digits(to_e164)
    if provider == 'meta':
        if not digits:
            logger.warning('Meta WhatsApp: empty digits for %s', to_e164)
            return False
        ok = _send_meta_graph(digits, body)
        if ok:
            return True
        # fall through to Twilio if configured as backup
        if _twilio_client() and (getattr(settings, 'TWILIO_WHATSAPP_FROM', '') or ''):
            phone = _phone_e164(to_e164) or (to_e164 if to_e164.startswith('+') else '')
            return _send_twilio(phone, body) if phone else False
        return False
    if provider == 'twilio':
        if to_e164.startswith('whatsapp:'):
            return _send_twilio(to_e164, body)
        phone = _phone_e164(to_e164)
        return _send_twilio(phone, body) if phone else False
    # stub
    to_wa = to_e164 if to_e164.startswith('whatsapp:') else f'whatsapp:{to_e164}'
    logger.info('[WhatsApp stub] (%s) To %s / digits=%s: %s', provider, to_wa, digits, body[:500])
    return False


def notify_order_placed(order):
    phone = _phone_e164(getattr(order, 'phone', '') or '')
    if not phone:
        return False
    body = (
        f'Your saree order #{order.order_number} has been placed successfully. '
        f'Thank you for shopping with us!'
    )
    return send_whatsapp(phone, body)


def notify_payment_success(order):
    phone = _phone_e164(getattr(order, 'phone', '') or '')
    if not phone:
        return False
    body = f'Payment received for order #{order.order_number}. We will pack your sarees soon.'
    return send_whatsapp(phone, body)


def notify_shipped(order):
    phone = _phone_e164(getattr(order, 'phone', '') or '')
    if not phone:
        return False
    body = f'Your saree order #{order.order_number} has been shipped successfully.'
    return send_whatsapp(phone, body)


def notify_delivered(order):
    phone = _phone_e164(getattr(order, 'phone', '') or '')
    if not phone:
        return False
    body = f'Order #{order.order_number} has been delivered. We hope you love your saree!'
    return send_whatsapp(phone, body)


def notify_cancelled(order):
    phone = _phone_e164(getattr(order, 'phone', '') or '')
    if not phone:
        return False
    body = f'Order #{order.order_number} has been cancelled as requested.'
    return send_whatsapp(phone, body)


def send_promotional(phone: str, message: str) -> bool:
    e164 = _phone_e164(phone)
    return send_whatsapp(e164, message) if e164 else False
