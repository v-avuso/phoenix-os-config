/* Isolated driver for the pinned keyd parser and keyboard event engine.
 * Never opens evdev/uinput or connects to the running daemon. */
#include "keyd.h"

static void capture(uint8_t code, uint8_t pressed) {
    printf("%u %u\n", code, pressed);
}

static void layer_change(const struct keyboard *kbd, const struct layer *layer, uint8_t active) {}

int main(int argc, char **argv) {
    struct config config;
    struct key_event events[128];
    size_t count = 0;
    unsigned int code, pressed;
    long timestamp;
    if (argc != 2 || config_parse(&config, argv[1])) return 1;
    while (scanf("%u %u %ld", &code, &pressed, &timestamp) == 3) {
        if (count == 128 || code > 255 || pressed > 1) return 2;
        events[count++] = (struct key_event){.code = code, .pressed = pressed, .timestamp = timestamp};
    }
    struct output output = {.send_key = capture, .on_layer_change = layer_change};
    struct keyboard *kbd = new_keyboard(&config, &output);
    kbd_process_events(kbd, events, count);
    return 0;
}
