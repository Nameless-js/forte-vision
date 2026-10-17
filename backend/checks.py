"""Optional model observations. Absence is unknown, never confirmation."""
import math

CHECK_IDS = {'subject_visible', 'object_state_visible', 'action_sequence', 'alternative_explanation'}


def validate_checks(checks):
    if not isinstance(checks, list) or len(checks) > len(CHECK_IDS):
        raise ValueError('invalid_checks')
    seen = set()
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError('invalid_check')
        key = check.get('id')
        if key not in CHECK_IDS or key in seen:
            raise ValueError('invalid_check_id')
        seen.add(key)
        if check.get('status') not in ('confirmed', 'refuted', 'unknown'):
            raise ValueError('invalid_check_status')
        if check['status'] != 'unknown' and not str(check.get('note', '')).strip():
            raise ValueError('check_observation_required')
        if 'timestamp_sec' in check:
            timestamp = check['timestamp_sec']
            if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp) or timestamp < 0:
                raise ValueError('invalid_check_timestamp')
        if 'note' in check and (not isinstance(check['note'], str) or len(check['note']) > 2000):
            raise ValueError('invalid_check_note')
        translations = check.get('translations', {})
        if not isinstance(translations, dict) or any(key not in ('ru', 'kk', 'en') or not isinstance(note, str) or len(note) > 2000 for key, note in translations.items()):
            raise ValueError('invalid_check_translations')
