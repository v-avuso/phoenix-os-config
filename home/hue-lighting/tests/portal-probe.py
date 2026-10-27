import sys
from gi.repository import Gio, GLib
connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
loop = GLib.MainLoop()
responses = []
def response(*args):
    responses.append(args[5].unpack())
    loop.quit()
subscription = connection.signal_subscribe('org.freedesktop.portal.Desktop', 'org.freedesktop.portal.Request', 'Response', None, None, Gio.DBusSignalFlags.NONE, response, None)
def request(method, signature, arguments):
    responses.clear()
    connection.call_sync('org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop', 'org.freedesktop.portal.ScreenCast', method, GLib.Variant(signature, arguments), GLib.VariantType.new('(o)'), Gio.DBusCallFlags.NONE, 10000, None)
    def expired():
        responses.append((99, {})); loop.quit(); return False
    timeout = GLib.timeout_add_seconds(15, expired)
    if not responses: loop.run()
    if responses[0][0] != 99: GLib.source_remove(timeout)
    code, data = responses[0]
    if code != 0: raise RuntimeError(f'{method} failed with response {code}')
    return data
session = request('CreateSession', '(a{sv})', ({'session_handle_token': GLib.Variant('s', 'hue_probe_session')},))['session_handle']
try:
    request('SelectSources', '(oa{sv})', (session, {'types': GLib.Variant('u', 1), 'multiple': GLib.Variant('b', False), 'persist_mode': GLib.Variant('u', 0)}))
    result = request('Start', '(osa{sv})', (session, '', {}))
    streams = result['streams']
    assert len(streams) == 1
    properties = streams[0][1]
    assert properties['mapping_id'] == sys.argv[1], properties
    print('PASS: Hue app identity routed automatic capture to the configured live display')
    print('Captured source size:', properties['size'])
finally:
    connection.call_sync('org.freedesktop.portal.Desktop', session, 'org.freedesktop.portal.Session', 'Close', None, None, Gio.DBusCallFlags.NONE, 2000, None)
