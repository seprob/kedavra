import xmpp, json, sys
import time, threading, datetime
from numpy import character

time_ids = {} # Slownik zawierajacy identyfikatory wiadomosci i odpowiadajace im czasy (w sumie od wyslania pierwszej wiadomosci). Zmienna jest globalna aby mozna bylo odpowiednio interpretowac zagubione wiadomosci.
    
class ping_thread(threading.Thread):
    def __init__(self, jid_to_ping):
        threading.Thread.__init__(self)
        
        self.jid_to_ping = jid_to_ping
        self.client = xmpp.Client(pinger_jid.getDomain(), debug = []) # Obiekt polaczenia (bez trybu debagowania).
        self.file_handle = open(log_filename, "a")
        self.log_file_lock = threading.Lock() # Klasa blokujaca dostep (w tym wypadku do pliku logowania).
        self.received = 0 # Okresla czy wiadomosc zostala juz odebrana (domyslnie nie czyli 0).
        self.each_time_ids = {} # Slownik zawierajacy identyfikatory wiadomosci i odpowiadajace im czasy (czas odpowiedzi na konkretne zapytanie).
        self.now = time.time() # Aktualny czas (uzywany do czasu uplyniecia odpowiedzi).
        self.try_no = 0 # Numer aktualnej proby "dobicia" sie.
        self.sum_time = time.time() # Aktualny czas (do sumowania).
        self.ids_received = {} # Slownik okreslajacy czy wiadomosc o danym identyfikatorze nie przekroczyla czasu odebrania.
        self.lost_ids = [] # Zagubione wiadomosci (zachowywane dla aktualnego odpytywania).
        
    def run(self):
        connection = self.client.connect() # Ustanawiamy polaczenie z naszym JID-em.
        
        if not connection:
            print "Nie moglem sie polaczyc dla przypadku pingowania JID-a %s." % (self.jid_to_ping)
            
        authentication = self.client.auth(pinger_jid.getNode(), data["jid_password"], resource = pinger_jid.getResource())
        
        if not authentication:
            print "Nie moglem dokonac autentykacji dla przypadku pingowania JID-a %s." % (self.jid_to_ping)
            
        self.client.RegisterHandler("message", self.message_handler) # Jaka funkcje wywolac w wypadku przyjscia nowej wiadomosci (pierwszy argument to konkretna zwrotka (z ang. "stanza").    

        availability = xmpp.protocol.Presence() # Obiekt dostepnosci.

        self.client.send(availability) # Dzieki temu JID zacznie byc widoczny jako dostepny.
        
        self.sum_time = time.time()
        
        # Zaczynamy "dobijanie".
        
        retry = 0
        
        while retry < data["retries"]:
            self.received = 0 # Domyslnie wiadomosc nieodebrana.
            
            self.try_no += 1
            
            times = datetime.datetime.now()
            
            id = time.strftime("%Y%m%d,%H%M%S") + str(times.microsecond)[:3] + "," + self.jid_to_ping + "," + str(self.try_no) + "," + str(time.time()) # Generujemy unikalny identyfikator.

            message = xmpp.protocol.Message(to = self.jid_to_ping, body = "ping" + " " + id, typ = "chat") # Wiadomosc do wyslania.
            
            self.ids_received[id] = 0 # Domyslnie wiadomosc nieodebrana.
        
            self.client.send(message) # Wysylamy wiadomosc.
        
            self.now = time.time() # Aktualny czas (zaczynamy odliczac do uplyniecia czasu na odpowiedz).
            
            time_ids[id] = time.time() # Zapisz identyfikator wiadomosci i czas kiedy go wyslano (dla sumowania).
            
            self.each_time_ids[id] = time.time() # Zapisz identyfikator wiadomosci i czas kiedy go wyslano (dla czasu rzeczywistego).
        
            while self.received != 1:
                self.client.Process() # Oczekuj na wiadomosc.
                    
                later = time.time() # Aktualny czas.
                    
                if (later - self.now) > data["timeout"]:
                    if self.try_no == data["retries"]:
                        date = time.strftime("%Y-%m-%d")
                        current_time = time.strftime("%X") # Aktualna godzina.
                        times = datetime.datetime.now()
                    
                        time_ids[id] = time.time() - self.sum_time
                    
                        time_ids[id] *= 1000
                        
                        log = str(date) + " " + str(current_time) + "," + str(times.microsecond)[:3] + " - zlight.kedavra - DEBUG - Failed " + self.jid_to_ping + " - " + "0, " + str(time_ids[id]) + ", " + id + ", " + str(self.try_no) # Sformatuj odpowiednio dane logowania (czas odpowiedzi jako 0 oznacza, ze odpowiedz nie przyszla).
                    
                        print log
            
                        self.log_file_lock.acquire() # Zablokuj.
            
                        self.file_handle.write(log + "\n") # Zapisz do pliku logowania.
            
                        self.log_file_lock.release() # Odblokuj.
                    
                    self.ids_received[id] = 0 # Wiadomosc o takim identyfikatorze nie zostala odebrana.
                        
                    self.lost_ids.append(id)
            
                    break
            
            if self.received == 1: # Jezeli odebrano wiadomosc to nie "dobijaj" sie juz dalej.
                break
            else:
                retry += 1
                
            time.sleep(data["retry_interval"])
        
        # Konczymy "dobijanie".
        
        self.client.disconnect()
        
    def message_handler(self, connection, event): # Funkcja wywolywana w wypadku przyjscia nowej wiadomosci.
        get_message_time = time.time() # Czas odebrania wiadomosci.
        kind = event.getType() # Typ wiadomosci.
        from_jid = event.getFrom().getStripped()
        date = time.strftime("%Y-%m-%d")
        current_time = time.strftime("%X") # Aktualna godzina.
        times = datetime.datetime.now()
        
        # Jezeli wiadomosc pochodzi od JID-a, ktorego aktualnie sprawdzamy, odpowiedz ma jeden z identyfikatorow, ktorego nadalismy wyslanym 
        # wiadomosciom, jezeli pierwszy czlon wiadomosci jest rowny "pong" i jezeli wiadomosc nie jest na liscie zagubionych JID-ow podczas
        # aktualnego zapytania.
    
        if kind in ["message", "chat", None] and from_jid == self.jid_to_ping and event.getBody().split()[1] in time_ids and event.getBody().split()[0] == "pong" and event.getBody().split()[1] not in self.lost_ids: 
            time_ids[event.getBody().split()[1]] = (get_message_time - self.sum_time) * 1000 # Sumowanie.
            
            self.each_time_ids[event.getBody().split()[1]] = get_message_time - self.each_time_ids[event.getBody().split()[1]]
            
            self.each_time_ids[event.getBody().split()[1]] *= 1000 # Zamien na milisekundy.
            
            log = str(date) + " " + str(current_time) + "," + str(times.microsecond)[:3] + " - zlight.kedavra - DEBUG - Ok " + from_jid + " - " + str(self.each_time_ids[event.getBody().split()[1]]) + ", " + str(time_ids[event.getBody().split()[1]]) + ", " + event.getBody().split()[1] + ", " + str(self.try_no) # Sformatuj odpowiednio dane logowania.
        
            print log
            
            self.log_file_lock.acquire() # Zablokuj.
            
            self.file_handle.write(log + "\n") # Zapisz do pliku logowania.
            
            self.log_file_lock.release() # Odblokuj.
            
            self.received = 1 # Odebrano wiadomosc.
            
            self.ids_received[event.getBody().split()[1]] = 1
            
        # Jezeli przyszla wiadomosc, na ktora nie czekalem.
        
        if kind in ["message", "chat", None] and event.getBody().split()[0] == "pong": # Jezeli pierwszy czlon wiadomosci to odpowiedz.
            if event.getBody().split()[1] not in time_ids or event.getBody().split()[1] in self.lost_ids: # Jezeli nie znajduje sie na liscie wyslanych identyfikatorow.
                # Wyciagamy z identyfikatora informacje, ktora pozwoli nam obliczyc ile pakiet wedrowal oraz ktory byl to numer zapytania.
                
                lost_values = ["", "", "", "", ""]
                iterator = 0
                
                for character in event.getBody().split()[1]:
                    if character != ",":
                        lost_values[iterator] += character
                    else:
                        iterator += 1
                        
                journey_time = (get_message_time - float(lost_values[4])) * 1000
                
                log = str(date) + " " + str(current_time) + "," + str(times.microsecond)[:3] + " - zlight.kedavra - DEBUG - Lost " + from_jid + " - 0, " + str(journey_time) + ", " + event.getBody().split()[1] + ", " + lost_values[3]
                
                print log
                
                self.log_file_lock.acquire() # Zablokuj.
            
                self.file_handle.write(log + "\n") # Zapisz do pliku logowania.
            
                self.log_file_lock.release() # Odblokuj.
        
try:
    data = json.loads(open('conf.json').read()) # Odczytujemy plik z dnaymi.
except IOError as excerpt:
    print "Blad wejscia wyjscia pliku z danymi konfiguracyjnymi: \"" + str(excerpt) + "\"." 
    
    sys.exit()
    
gateway_jids = [] # Tablica na JID-y gatewayow, ktore mamy pingowac.

for jid in data["gateway_jids"]: # Dla kazdego JID-u gatewaya.
    gateway_jids.append(jid) # Dodajemy JID-y do tablicy.
    
log_filename = data["log_filename"] # Okreslamy plik logowania.
    
try:
    file_handle = open(log_filename, "a") # Otworz plik do dopisywania (stworz jezeli nie istnieje).
except IOError as excerpt:
    print "Blad wejscia wyjscia pliku logowania: \"" + str(excerpt) + "\"."
    
    sys.exit()
    
pinger_jid = xmpp.protocol.JID(data["jid"]) # Do pingowania wykorzystaj danego JID-a.

run = 0

while run < data["runs"]: # Kolejne uruchomiania koncepcji diagnostyki..
    for jid in gateway_jids: # Dla kazdego JID-a.
        ping_thread(jid).start() # Uruchamiamy kolejny watek (wywola funkcje run w klasie).
        
    time.sleep(data["run_interval"])
        
    run += 1
    
file_handle.close() # Zamknij uchwyt pliku.
