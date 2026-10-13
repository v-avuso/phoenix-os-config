"""Versioned semantic authorization; policy is installed configuration, never caller input."""
import json
import re
import secrets
import syslog
import unicodedata
from pathlib import Path

DIAGNOSTICS = ('kernel-journal', 'dmesg', 'trace-summary', 'trace-format', 'service-status', 'wakeup-get', 'wakeup-set')
FIELDS = {'version', 'operation', 'arguments', 'task', 'reason'}

def text(value, limit, label):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or any(unicodedata.category(c).startswith('C') for c in value):
        raise ValueError('invalid ' + label)
    return value.strip()

def named(operation, arguments, task, reason):
    return dict(version=1, operation=operation, arguments=arguments, task=task, reason=reason)

def default_policy(review, client, operator, devices=(), services=(), target='metal', updater=None):
    """Repository-only compatibility for focused fixtures; never an installed fallback."""
    return dict(version=1, securityReviewEnabled=bool(review), clientUid=client, operatorUid=operator,
                updaterUid=operator if updater is None else updater, target=target, diagnostics={'admin.' + op: 'automatic' for op in DIAGNOSTICS},
                wakeupDevices=list(devices), statusServices=list(services))

def policy(config):
    value = config.get('authorizationPolicy')
    if isinstance(value, str):
        value = json.loads(Path(value).read_text())
    if value is None:
        if str(Path(__file__).resolve()).startswith('/nix/store/'):
            raise ValueError('installed authorization policy missing')
        value = default_policy(config.get('modelReviewEnabled', True), config.get('clientUid', config.get('client_uid', 1000)),
                               config.get('operatorUid', config.get('clientUid', config.get('client_uid', 1000))),
                               config.get('wakeup_devices', []), config.get('status_services', []), config.get('target', 'metal'), config.get('updaterUid'))
    if not isinstance(value, dict) or set(value) != {'version', 'securityReviewEnabled', 'clientUid', 'operatorUid', 'updaterUid', 'target', 'diagnostics', 'wakeupDevices', 'statusServices'}:
        raise ValueError('invalid installed authorization policy')
    if type(value['version']) is not int or value['version'] != 1 or type(value['securityReviewEnabled']) is not bool:
        raise ValueError('invalid installed authorization policy version')
    if any(type(value[key]) is not int or value[key] < 0 for key in ('clientUid', 'operatorUid', 'updaterUid')):
        raise ValueError('invalid installed caller policy')
    if value['target'] not in {'metal', 'vm'} or not isinstance(value['diagnostics'], dict) or set(value['diagnostics']) != {'admin.' + op for op in DIAGNOSTICS} or any(mode not in {'automatic', 'human', 'denied'} for mode in value['diagnostics'].values()):
        raise ValueError('invalid installed decision policy')
    for configured, installed in [('clientUid', 'clientUid'), ('client_uid', 'clientUid'), ('operatorUid', 'operatorUid'), ('updaterUid', 'updaterUid')]:
        if configured in config and (type(config[configured]) is not int or config[configured] != value[installed]):
            raise ValueError('contradictory installed caller policy')
    if 'modelReviewEnabled' in config and config['modelReviewEnabled'] != value['securityReviewEnabled']:
        raise ValueError('contradictory installed review policy')
    return value

def validate(request, installed):
    if not isinstance(request, dict) or set(request) != FIELDS or type(request['version']) is not int or request['version'] != 1:
        raise ValueError('unsupported authorization envelope')
    text(request['reason'], 300, 'nonsecret reason')
    task = text(request['task'], 100, 'task')
    if not re.fullmatch(r'[A-Za-z0-9._:/+ -]{1,100}', task):
        raise ValueError('invalid task')
    operation, args = request['operation'], request['arguments']
    if not isinstance(operation, str) or not isinstance(args, dict):
        raise ValueError('invalid named operation')
    if operation.startswith('deployment.'):
        action = operation.removeprefix('deployment.')
        if action not in {'test', 'switch', 'boot', 'update'} or set(args) != {'target'} or args['target'] != installed['target']:
            raise ValueError('unsupported deployment arguments')
        return 'automatic' if action == 'update' else ('security-review' if installed['securityReviewEnabled'] else 'human')
    if operation not in installed['diagnostics']:
        raise ValueError('unknown named operation')
    op = operation.removeprefix('admin.')
    fields = {'kernel-journal': {'lines'}, 'trace-format': {'event'}, 'service-status': {'service'},
              'wakeup-get': {'device'}, 'wakeup-set': {'device', 'state'}}.get(op, set())
    if set(args) != fields:
        raise ValueError('unsupported diagnostic arguments')
    if op == 'kernel-journal' and (type(args['lines']) is not int or not 1 <= args['lines'] <= 2000):
        raise ValueError('lines must be an integer 1..2000')
    if op == 'trace-format' and (not isinstance(args['event'], str) or not re.fullmatch(r'(?:xhci-hcd|usb|kprobes)/[a-zA-Z0-9_]{1,100}', args['event'])):
        raise ValueError('unsupported trace event')
    if op == 'service-status' and (not isinstance(args['service'], str) or args['service'] not in installed['statusServices']):
        raise ValueError('service is not allowlisted')
    if op.startswith('wakeup-') and (not isinstance(args['device'], str) or args['device'] not in installed['wakeupDevices']):
        raise ValueError('device is not allowlisted')
    if op == 'wakeup-set' and (not isinstance(args['state'], str) or args['state'] not in {'enabled', 'disabled'}):
        raise ValueError('invalid wakeup state')
    return installed['diagnostics'][operation]

def diagnostic(args, reason, task='phoenix-admin'):
    if not isinstance(args, list) or not args or any(not isinstance(v, str) for v in args):
        raise ValueError('invalid diagnostic arguments')
    op, *values = args
    fields = {'kernel-journal': ['lines'], 'trace-format': ['event'], 'service-status': ['service'], 'wakeup-get': ['device'], 'wakeup-set': ['device', 'state']}.get(op, [])
    if op == 'kernel-journal' and not values: values = ['500']
    if len(fields) != len(values): raise ValueError('invalid argument count')
    typed = dict(zip(fields, values))
    if op == 'kernel-journal':
        if not re.fullmatch(r'[1-9][0-9]{0,3}', typed['lines']): raise ValueError('invalid line count')
        typed['lines'] = int(typed['lines'])
    return named('admin.' + op, typed, task, reason)

def diagnostic_argv(request):
    op = request['operation'].removeprefix('admin.')
    fields = {'kernel-journal': ['lines'], 'trace-format': ['event'], 'service-status': ['service'], 'wakeup-get': ['device'], 'wakeup-set': ['device', 'state']}.get(op, [])
    return [op, *(str(request['arguments'][field]) for field in fields)]

def correlation(value):
    if value is not None and (not isinstance(value, str) or not re.fullmatch('[a-f0-9]{32}', value)):
        raise ValueError('invalid preflight correlation')
    return value

def audit(event, identifier, uid, pid, request=None, decision='denied', category=None, trusted=True, preflight_id=None):
    record = dict(version=1, event=event, id=identifier, uid=uid, pid=pid, decision=decision, trusted=trusted)
    if request is not None:
        # Only validated semantic metadata reaches this branch; never source/output.
        record.update(operation=request['operation'], task=request['task'], reason=request['reason'])
    if category is not None: record['category'] = category
    if preflight_id is not None: record['clientPreflightId'] = correlation(preflight_id)
    syslog.openlog('phoenix-authorization')
    syslog.syslog(syslog.LOG_INFO, json.dumps(record, ensure_ascii=True, sort_keys=True))

def execution_caller(operation, installed, uid, operator=False):
    """A kernel UID may use the updater role only for the fixed update operation."""
    if type(uid) is not int:
        return False
    if operator:
        return uid == installed['operatorUid']
    return uid == installed['clientUid'] or (uid == installed['updaterUid'] and operation == 'deployment.update')

def preflight(request, installed, uid, pid, operator=False, preflight_id=None):
    identifier = secrets.token_hex(16)
    try:
        correlation(preflight_id)
        if not (execution_caller(request.get('operation') if isinstance(request, dict) else None, installed, uid, operator) or (not operator and type(uid) is int and uid == installed['operatorUid'])):
            raise ValueError('caller denied')
        decision = validate(request, installed)
    except (ValueError, TypeError, KeyError):
        audit('preflight', identifier, uid, pid, category='invalid-or-denied')
        raise ValueError('invalid or denied authorization request') from None
    audit('preflight', identifier, uid, pid, request, decision, preflight_id=preflight_id)
    return dict(ok=True, id=identifier, decision=decision)

def require(request, installed, uid, pid, operator=False, preflight_id=None):
    if not execution_caller(request.get('operation') if isinstance(request, dict) else None, installed, uid, operator):
        audit('rejected', secrets.token_hex(16), uid, pid, category='caller-denied')
        raise ValueError('caller denied for execution')
    result = preflight(request, installed, uid, pid, operator, preflight_id)
    decision = result['decision']
    allowed = decision in {'automatic', 'security-review'} if not operator else decision == 'human'
    if not allowed:
        audit('denied', result['id'], uid, pid, request, decision, category='host-authentication-required' if decision == 'human' else 'policy-denied')
        raise ValueError('host-authentication-required' if decision == 'human' else 'operation denied by installed policy')
    return result
