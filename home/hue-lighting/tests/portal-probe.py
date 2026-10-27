import sys
from gi.repository import Gio, GLib
connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
loop = GLib.MainLoop()
responses = []
def response(*args):
    responses.append(args[5].unpack())
    loop.quit()
subscription = connection.signal_subscribe('org.freedesktop.portal.Desktop', 'org.freedesktop.portal.Request', 'Response', None, None, Gio.DBusSignalFlags.NONE, response, None)
def request(method, signature, arguments, expected=0):
    responses.clear()
    connection.call_sync('org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop', 'org.freedesktop.portal.ScreenCast', method, GLib.Variant(signature, arguments), GLib.VariantType.new('(o)'), Gio.DBusCallFlags.NONE, 10000, None)
    def expired():
        responses.append((99, {})); loop.quit(); return False
    timeout = GLib.timeout_add_seconds(15, expired)
    if not responses: loop.run()
    if responses[0][0] != 99: GLib.source_remove(timeout)
    code, data = responses[0]
    if code != expected: raise RuntimeError(f'{method} returned {code}; expected {expected}')
    return data
session = request('CreateSession', '(a{sv})', ({'session_handle_token': GLib.Variant('s', 'hue_probe_session')},))['session_handle']
# Hyprland prompts during SelectSources. Declining closes the session itself.
request('SelectSources', '(oa{sv})', (session, {'types': GLib.Variant('u', 1), 'multiple': GLib.Variant('b', False), 'persist_mode': GLib.Variant('u', 2)}), expected=1)
