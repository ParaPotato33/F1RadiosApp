import json
import os
import random
import xlsxwriter
import requests
import pygame
import pandas as pd
from kivy.app import App
from urllib.request import urlopen
from kivy.core.window import Window
from openai import OpenAI
from functools import partial
from kivy.properties import StringProperty, BooleanProperty, ListProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock

Window.fullscreen = 'auto'
Window.clearcolor = (0.2, 0.2, 0.2, 1)

randomMessages = ['Example Message: tyres', 'Example Message: Null', 'Example Message: pit']

class DriverUI(BoxLayout):
    driverNumber = StringProperty()
    driverName = StringProperty()
    audioChannel = StringProperty()
    transcript = StringProperty()
    keyWords = ListProperty([])
    stt = BooleanProperty()
    imageUrl = StringProperty()

    pygame.init()
    pygame.mixer.init()
    pygame.mixer.set_num_channels(20)
    for i in range(20):
        pygame.mixer.Channel(i).set_volume(0)
        pygame.mixer.Channel(i).set_endevent()

    def check_audio(self, audioChannel, recordings, *largs):
        if not pygame.mixer.Channel(int(audioChannel)).get_busy():
            print(int(audioChannel))
            self.play_audio(self.driverNumber, audioChannel, recordings)

    def mute(self, audioChannel, state):
        if state == 'down':
            pygame.mixer.Channel(int(audioChannel)).set_volume(1)
        else:
            pygame.mixer.Channel(int(audioChannel)).set_volume(0)

    def start(self):
        print(self.driverNumber)
        savePath = f'_internal/DriverFiles/{self.driverNumber}/'
        for f in os.listdir(savePath):
            if f[-4:] == '.xlsx':
                os.remove(savePath + f)
        workbook = xlsxwriter.Workbook(f'_internal/DriverFiles/{self.driverNumber}/RadioLogs{self.driverNumber}.xlsx')
        workbook.add_worksheet()
        workbook.close()
        #open(f'DriverFiles/{self.driverNumber}/RadioLogs{self.driverNumber}.xlsx', 'x').close()
        self.get_message(self.driverNumber, self.audioChannel)


    def get_message(self, driverNumber, audioChannel):
        recordings = []
        response = urlopen(f"https://api.openf1.org/v1/team_radio?session_key=9157&driver_number={driverNumber}")
        data = json.loads(response.read().decode('utf-8'))
        savePath = f'_internal/DriverFiles/{driverNumber}/'
        for f in os.listdir(savePath):
            if f[-4:] == '.mp3':
                os.remove(savePath + f)
        for obj in data:
            recordings.append(obj['recording_url'])
        print(recordings)

        self.play_audio(driverNumber, audioChannel, recordings)

    def play_audio(self, driverNumber, audioChannel, recordings):
        if len(recordings) == 0:
            print('Done')
            self.transcript = ''
            self.keyWords = []
        else:
            url = recordings[0]
            recordings.remove(url)

            savePath = f'_internal/DriverFiles/{driverNumber}/'
            r = OpenAI()

            date = [url[-13:-11] + '/' + url[-15:-13] + '/' + url[-19:-15]]
            time = [url[-10:-8] + ':' + url[-8:-6] + ':' + url[-6:-4]]

            recording = requests.get(url)
            fileName = url.split('/')[-1]

            with open(savePath + url.split('/')[-1], 'wb') as f:
                f.write(recording.content)
                f.close()

                if self.stt == True:
                    print(self.stt)
                    audioFile = open(savePath + fileName, 'rb')
                    self.transcript = '"' + r.audio.transcriptions.create(model='whisper-1', file=audioFile).text + '"'
                else:
                    rand = random.randrange(0, len(randomMessages))
                    print(rand)
                    self.transcript = '"' + randomMessages[rand] + '"'

                existing_sheet = pd.read_excel(savePath + f'RadioLogs{driverNumber}.xlsx', sheet_name='Sheet1')
                new_data = pd.DataFrame({'Date': date, 'Time': time, 'Message': self.transcript})
                new_sheet = pd.concat([existing_sheet, new_data])
                new_sheet.to_excel(savePath + f'RadioLogs{driverNumber}.xlsx', sheet_name='Sheet1', index=False)

            pygame.mixer.Channel(int(audioChannel))
            self.keyWords = self.transcript.split(' ')
            self.keyWords[0] = self.keyWords[0][1:]
            self.keyWords[-1] = self.keyWords[-1][:-1]

            print(savePath + fileName)
            print(audioChannel)
            pygame.mixer.Channel(int(audioChannel)).play(pygame.mixer.Sound(savePath + fileName))
            Clock.schedule_interval(partial(self.check_audio, audioChannel, recordings), 1)

class MainPage(BoxLayout):
    all_width = NumericProperty(4)
    tyre_width = NumericProperty(2)
    pit_width = NumericProperty(2)
    tyres = ['tyres', 'tyre', 'Tyres', 'Tyre']
    pits = ['pit', 'Pit', 'pits', 'Pits']

    def all_tab(self, *largs):
        if self.ids['all_btn'].state == 'down':
            self.all_width = 4
            for child in self.ids['driverLayout'].children:
                child.opacity = 1
                if child.transcript == '':
                    child.opacity = 0.1
            Clock.schedule_once(partial(self.all_tab), 1)
        else:
            self.all_width = 2

    def tyre_tab(self, *largs):
        if self.ids['tyre_btn'].state == 'down':
            self.tyre_width = 4
            for child in self.ids['driverLayout'].children:
                child.opacity = 0.1
                for tyre in self.tyres:
                    if tyre in child.keyWords:
                        child.opacity = 1
            Clock.schedule_once(partial(self.tyre_tab), 1)
        else:
            self.tyre_width = 2

    def pit_tab(self, *largs):
        if self.ids['pit_btn'].state == 'down':
            self.pit_width = 4
            for child in self.ids['driverLayout'].children:
                child.opacity = 0.1
                for pit in self.pits:
                    if pit in child.keyWords:
                        child.opacity = 1
            Clock.schedule_once(partial(self.pit_tab), 1)
        else:
            self.pit_width = 2

    def start(self):
        self.ids.start_btn.disabled = True
        self.ids.start_btn.background_color = (100, 0, 0, 0.8)
        for child in self.ids['driverLayout'].children:
            child.start()
        self.all_tab()

class F1RadiosApp(App):
    def build(self):
        return MainPage()

if __name__ == '__main__':
    F1RadiosApp().run()