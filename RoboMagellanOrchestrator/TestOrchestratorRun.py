import os
import keyboard

import airsim
import airsim.airsim_types as at
import rm_bot_client.rm_bot_client as rm_bot_client
import robo_magellan_orchestrator.robo_magellan_orchestrator as robo_magellan_orchestrator

def get_control_signals():
    w_pressed = keyboard.is_pressed('w')
    s_pressed = keyboard.is_pressed('s')
    a_pressed = keyboard.is_pressed('a')
    d_pressed = keyboard.is_pressed('d')

    throttle = 0.7
    n_throttle = -1.0 * throttle

    if w_pressed:
        if a_pressed:
            return (0, throttle)
        elif d_pressed:
            return (throttle, 0)
        elif s_pressed:
            return (0, 0)
        else:
            return (throttle, throttle)

    elif s_pressed:
        if (a_pressed):
            return (n_throttle, 0)
        elif (d_pressed):
            return (0, n_throttle)
        else:
            return (n_throttle, n_throttle)

    elif a_pressed:
        if d_pressed:
            return (0, 0)
        else:
            return (n_throttle, throttle)

    elif d_pressed:
        return (throttle, n_throttle)

    return (0, 0)

def main():
    client = rm_bot_client.RmBotClient()
    orchestrator = robo_magellan_orchestrator.RoboMagellanCompetitionOrchestrator('TestOrchestrationConfiguration.json')

    orchestrator.set_debug_draw_enabled(True)
    orchestrator.set_random_seed(47)
    orchestrator.start_new_run(client)

    os.system('cls')
    print('Competition is now running.')

    status = orchestrator.get_run_summary(client)
    while (not status['runComplete']):
        left_throttle, right_throttle = get_control_signals()
        client.drive(left_throttle, right_throttle)

        orchestrator.run_tick(client)
        status = orchestrator.get_run_summary(client)

    client.drive(0, 0)
    status_string = orchestrator.get_run_summary_string(client)
    orchestrator.clean_up_run(client)

    os.system('cls')
    print(status_string)
    print('Graceful termination.')
        
if __name__ == '__main__':
    main()
