'''
Created on Feb 12, 2012

@author: Geoff
'''
from datetime import datetime, timedelta
from dto.display import Display
from dto.link import LinkCancel, LinkGood
from dto.rootdto import RootDTO
from event import PulseEvent
from player import Player
from os import urandom;
from base64 import b64encode

LINK_DEAD_INTERVAL = timedelta(seconds=5)
LINK_DEAD_PRUNE = timedelta(minutes=2)
LINK_IDLE_REFRESH = timedelta(seconds=45)


class SessionManager():
    def __init__(self, dispatcher, datastore, nature):
        self.dispatcher = dispatcher
        self.datastore = datastore
        self.nature = nature;
        self.session_map = {}
        self.player_map = {}
        self.dispatcher.register("refresh_link_status", self.refresh_link_status)
        self.dispatcher.dispatch_p(PulseEvent("refresh_link_status", 20, repeat=True))                      
 
    def get_next_id(self):
        usession_id = b64encode(str(urandom(16)))
        while self.get_session(usession_id):
            usession_id = b64encode(str(urandom(16)))
        return usession_id
    
    def get_session(self, session_id):
        return self.session_map.get(session_id)   
        
    def respond(self, rootDto):
        return rootDto.merge(RootDTO(player_list=self.player_map))
        
    def start_session(self):
        session_id = self.get_next_id()
        session = UserSession(self.dispatcher)
        self.session_map[session_id] = session
        return self.respond(RootDTO(connect=session_id))
                    
    def display_players(self):
        player_list_dto = RootDTO(player_list=self.player_map)
        for session in self.session_map.itervalues():
            session.append(player_list_dto)

    def refresh_link_status(self, *args):
        now = datetime.now()
        for session_id, session in self.session_map.items():
            if session.ld_time:
                if now - session.ld_time > LINK_DEAD_PRUNE:
                    if session.player:
                        self.logout(session)
                    del self.session_map[session_id]
                    continue
            elif session.request:
                if now - session.attach_time > LINK_IDLE_REFRESH:
                    session.append(RootDTO(keepalive=True))
            elif now - session.attach_time > LINK_DEAD_INTERVAL:
                session.link_failed("Timeout")
            if session.player:
                self.player_map[session.player.name] = session.player_info(now)
        self.display_players()
                 
    def login(self, session_id, user_id):
        session = self.session_map.get(session_id)
        player = Player(user_id)
        if not self.datastore.load_object(player):
            return RootDTO(login_error="no_such_user")
        
        welcome = self.nature.baptise(player)
        session.append(welcome)
        self.player_map[player.name] = session.login(player);
        return self.respond(RootDTO(login="good"))
        
    def logout(self, session):
        player = session.player
        player.detach();
        session.player = None
        del self.player_map[player.name]
        return self.respond(RootDTO(logout="logout"))
        
        
class UserSession():
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self.output = RootDTO()
        self.player = None;  
        self.attach_time = datetime.now()
        self.ld_time = None
        self.request = None
        self.pulse_reg = None
        self.dialog = None
        
    def login(self, player):
        self.player = player
        player.session = self
        self.activity_time = datetime.now()
        return self.player_info(self.activity_time)
        
    def player_info(self, now):
        if self.ld_time:
            status = "Link Dead"
        else:
            idle = (now - self.activity_time).seconds;
            if idle < 60:
                status = "Active"
            else:
                status =  "Idle: " + str(idle / 60) + "m"
        info = RootDTO(status=status)
        info.loc = self.player.env.title
        return info
        
    def attach(self, request):
        if self.request:
            self.push(LinkCancel())
        self.attach_time = datetime.now()
        self.ld_time = None
        self.request = request
        self.request.notifyFinish().addErrback(self.link_failed)
    
    def link_failed(self, error):
        self.ld_time = datetime.now()
        self.request = None
    
    def append(self, data):
        if not self.pulse_reg:
            self.pulse_reg = self.dispatcher.register("pulse", self.push_output)
        self.output.merge(data)
         
    def display_line(self, display_line):
        display = Display()
        display.append(display_line)
        self.append(display)
        
    def push_output(self):
        if self.request:
            self.push(self.output.merge(LinkGood()))
            self.output = RootDTO()
            self.pulse_reg.detach()
            self.pulse_reg = None
            
    def push(self, output):
        self.request.write(self.output.json)
        self.request.finish()
        self.request = None