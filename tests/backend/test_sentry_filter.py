"""
Sentry before_send hook 단위 테스트.
FIX-WEBSOCKET-STOPITERATION-SENTRY-NOISE-20260428.
"""
from app import _sentry_before_send


def test_filters_websocket_stopiteration():
    """websocket_route + wsgi + StopIteration 모두 매칭 시 None 반환 (drop)."""
    event = {
        'transaction': 'websocket_route',
        'exception': {'values': [{
            'type': 'StopIteration',
            'mechanism': {'type': 'wsgi', 'handled': False},
        }]},
    }
    assert _sentry_before_send(event, hint={}) is None


def test_passes_other_transaction_stopiteration():
    """다른 transaction 의 StopIteration 은 정상 전달 (false negative 방지)."""
    event = {
        'transaction': 'some_other_route',
        'exception': {'values': [{
            'type': 'StopIteration',
            'mechanism': {'type': 'wsgi'},
        }]},
    }
    assert _sentry_before_send(event, hint={}) == event


def test_passes_non_stopiteration_at_websocket():
    """websocket_route 의 다른 exception type 은 정상 전달."""
    event = {
        'transaction': 'websocket_route',
        'exception': {'values': [{
            'type': 'ValueError',
            'mechanism': {'type': 'wsgi'},
        }]},
    }
    assert _sentry_before_send(event, hint={}) == event


def test_safe_on_malformed_event():
    """이상한 event 구조에도 안전 fallback (정상 capture)."""
    event = {'transaction': 'websocket_route'}  # exception 키 없음
    assert _sentry_before_send(event, hint={}) == event
