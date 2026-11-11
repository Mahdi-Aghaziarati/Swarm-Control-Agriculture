"""UI hooks only: these functions deliberately send NO flight commands."""


def preflight_check(targets):
    print('Preflight check', targets, flush=True)


def start_animation(targets, delay):
    print('Start animation', targets, 'delay:', delay, flush=True)


def pause_resume(targets):
    print('Pause / Resume', targets, flush=True)


def takeoff(targets, altitude):
    print('Takeoff', targets, 'altitude:', altitude, flush=True)


def land_selected(targets):
    print('Land selected', targets, flush=True)


def disarm_selected(targets):
    print('Disarm selected', targets, flush=True)


def test_leds(targets):
    print('Test leds', targets, flush=True)


def flip(targets):
    print('Flip', targets, flush=True)


def land_all(targets):
    print('Land ALL', targets, flush=True)


def disarm_all(targets):
    print('Disarm ALL', targets, flush=True)


def emergency_land(targets):
    print('Emergency land', targets, flush=True)


# Leader-only hooks. Implement future behavior here, not in the UI thread.
def scan_area(leader):
    print('Scan area', leader, flush=True)


def return_to_nest(leader):
    print('Return to nest', leader, flush=True)


def immediate_land(leader):
    print('Immediate land', leader, flush=True)
