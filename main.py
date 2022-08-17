#!/usr/bin/python3
import threading
import time
import PySimpleGUI as sg
from scrape import Extractor, Action, exportFile


def run_scrape(window, api, target, month):
    reactions = api.getInteractions(Action.LIKES, target, int(month), int(month) + 1)
    comments = api.getInteractions(Action.COMMENTS, target, int(month), int(month) + 1)
    uShares = api.getShares(Action.SHARES, target, int(month), int(month) + 1)
    gShares = api.getShares(Action.GROUP_SHARES, target, int(month), int(month) + 1)
    if len(reactions) > 0:
        exportFile(reactions, 'likes')
    if len(comments) > 0:
        exportFile(comments, 'comments')
    if len(uShares) > 0:
        exportFile(uShares, 'wall_share')
    if len(gShares) > 0:
        exportFile(gShares, 'group_share')
    api.quit()
    window.write_event_value('-THREAD-', f"Likes: {len(reactions)} - Comments: {len(comments)} - Wall shares: {len(uShares)} - Group Shares: {len(gShares)}")


def the_gui():
    layout = [[sg.Text("Profiles")], [sg.Input(key='-profile-')],
              [sg.Text("Month")], [sg.Input(key='-month-')],
              [sg.Text("Target page")], [sg.Input(key='-target-')],
              [sg.Text(size=(70, 1), key='-OUTPUT-')],
              [sg.Button('Search')]]

    window = sg.Window('Just Demo', layout)
    api = None

    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED:
            try:
                api.quit()
            except:
                pass
            break

        if event == "Search":
            window['-OUTPUT-'].update('running...')
            api = Extractor(profile=values['-profile-'])
            threading.Thread(target=run_scrape, args=(window, api, values['-target-'], values['-month-'],)).start()

        if event == '-THREAD-':
            window['-OUTPUT-'].update(values[event])

    window.close()


if __name__ == '__main__':
    the_gui()
